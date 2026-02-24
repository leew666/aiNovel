"""
流水线运行器

封装"大纲 -> 章节细纲 -> 正文"批量执行、重试策略与失败章节收集。
支持从任意合法步骤恢复执行，某章节失败不阻塞整体。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger
from sqlalchemy.orm import Session

from ainovel.db.crud import novel_crud, chapter_crud
from ainovel.db.novel import WorkflowStatus
from ainovel.exceptions import NovelNotFoundError, InsufficientDataError


# 流水线支持的步骤范围（3=大纲, 4=细纲, 5=正文）
PIPELINE_STEPS = (3, 4, 5)


@dataclass
class TaskResult:
    """单章节任务执行结果"""

    chapter_id: int
    chapter_title: str
    step: int
    success: bool
    error: Optional[str] = None
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """整体流水线执行结果"""

    novel_id: int
    from_step: int
    to_step: int
    chapter_range: Optional[str]
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    task_results: list[TaskResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "novel_id": self.novel_id,
            "from_step": self.from_step,
            "to_step": self.to_step,
            "chapter_range": self.chapter_range,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "task_results": [
                {
                    "chapter_id": r.chapter_id,
                    "chapter_title": r.chapter_title,
                    "step": r.step,
                    "success": r.success,
                    "error": r.error,
                    "stats": r.stats,
                }
                for r in self.task_results
            ],
            "failed_chapter_ids": [
                r.chapter_id for r in self.task_results if not r.success
            ],
        }


def parse_chapter_range(chapter_range: Optional[str], total: int) -> list[int]:
    """
    解析章节范围字符串，返回 1-based 序号列表。

    支持格式：
    - None 或 "" → 全部章节
    - "5"        → 第5章
    - "1-10"     → 第1到10章
    - "1,3,5"    → 第1、3、5章
    """
    if not chapter_range:
        return list(range(1, total + 1))

    indices: list[int] = []
    for part in chapter_range.split(","):
        part = part.strip()
        if "-" in part:
            m = re.fullmatch(r"(\d+)-(\d+)", part)
            if not m:
                raise ValueError(f"无效章节范围格式: '{part}'，应为 'N-M'")
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                raise ValueError(f"章节范围起始 {start} 大于结束 {end}")
            indices.extend(range(start, end + 1))
        elif re.fullmatch(r"\d+", part):
            indices.append(int(part))
        else:
            raise ValueError(f"无效章节范围格式: '{part}'")

    # 去重并过滤越界
    seen: set[int] = set()
    result: list[int] = []
    for idx in indices:
        if idx not in seen and 1 <= idx <= total:
            seen.add(idx)
            result.append(idx)
    return sorted(result)


class PipelineRunner:
    """
    流水线运行器（SRP：只负责批量调度，不持有生成逻辑）

    调用方式：
        runner = PipelineRunner(orchestrator)
        result = runner.run(session, novel_id, plan)
    """

    def __init__(self, orchestrator: Any) -> None:
        """
        Args:
            orchestrator: WorkflowOrchestrator 实例，提供各步骤方法
        """
        self._orch = orchestrator

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def run(
        self,
        session: Session,
        novel_id: int,
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        """
        执行流水线计划。

        Args:
            session: 数据库会话
            novel_id: 小说ID
            plan: 执行计划，字段：
                from_step (int): 起始步骤，3/4/5
                to_step   (int): 结束步骤，3/4/5，须 >= from_step
                chapter_range (str|None): 章节范围，如 "1-10"
                regenerate (bool): 是否强制重新生成已有内容

        Returns:
            PipelineResult.to_dict()
        """
        from_step: int = plan.get("from_step", 3)
        to_step: int = plan.get("to_step", 5)
        chapter_range: Optional[str] = plan.get("chapter_range")
        regenerate: bool = plan.get("regenerate", False)

        self._validate_plan(from_step, to_step)

        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise NovelNotFoundError(novel_id)

        result = PipelineResult(
            novel_id=novel_id,
            from_step=from_step,
            to_step=to_step,
            chapter_range=chapter_range,
        )

        # 步骤3：生成大纲（novel 级别，不按章节循环）
        if from_step <= 3 <= to_step:
            self._run_step3(session, novel_id, novel, regenerate, result)
            # 刷新 novel 对象，确保后续步骤能看到新生成的 volumes/chapters
            session.refresh(novel)

        # 步骤4/5：按章节批量执行
        if to_step >= 4:
            all_chapters = self._collect_chapters(novel)
            if not all_chapters:
                raise InsufficientDataError(
                    "没有可处理的章节，请先完成步骤3（大纲生成）",
                    missing_data="chapters",
                )

            indices = parse_chapter_range(chapter_range, len(all_chapters))
            target_chapters = [all_chapters[i - 1] for i in indices]
            result.total = len(target_chapters)

            for chapter in target_chapters:
                if from_step <= 4 <= to_step:
                    task = self._run_step4(session, chapter, regenerate)
                    result.task_results.append(task)
                    if task.success:
                        result.succeeded += 1
                    else:
                        result.failed += 1
                        # 步骤4失败则跳过该章节的步骤5
                        if to_step >= 5:
                            result.task_results.append(
                                TaskResult(
                                    chapter_id=chapter.id,
                                    chapter_title=chapter.title,
                                    step=5,
                                    success=False,
                                    error="步骤4失败，跳过步骤5",
                                )
                            )
                            result.skipped += 1
                        continue

                if from_step <= 5 <= to_step:
                    task = self._run_step5(session, chapter, regenerate)
                    result.task_results.append(task)
                    if task.success:
                        result.succeeded += 1
                    else:
                        result.failed += 1

        logger.info(
            f"流水线完成 novel_id={novel_id} "
            f"步骤{from_step}-{to_step} "
            f"成功={result.succeeded} 失败={result.failed} 跳过={result.skipped}"
        )
        return result.to_dict()

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_plan(from_step: int, to_step: int) -> None:
        if from_step not in PIPELINE_STEPS:
            raise ValueError(f"from_step 必须为 {PIPELINE_STEPS} 之一，当前: {from_step}")
        if to_step not in PIPELINE_STEPS:
            raise ValueError(f"to_step 必须为 {PIPELINE_STEPS} 之一，当前: {to_step}")
        if from_step > to_step:
            raise ValueError(f"from_step({from_step}) 不能大于 to_step({to_step})")

    @staticmethod
    def _collect_chapters(novel: Any) -> list[Any]:
        """按卷序、章序收集所有章节"""
        chapters: list[Any] = []
        for volume in sorted(novel.volumes, key=lambda v: v.order):
            chapters.extend(sorted(volume.chapters, key=lambda c: c.order))
        return chapters

    def _run_step3(
        self,
        session: Session,
        novel_id: int,
        novel: Any,
        regenerate: bool,
        result: PipelineResult,
    ) -> None:
        """执行步骤3：大纲生成（幂等保护）"""
        already_done = novel.current_step >= 3 and len(novel.volumes) > 0
        if already_done and not regenerate:
            logger.info(f"novel_id={novel_id} 步骤3已完成，跳过（regenerate=False）")
            return

        try:
            self._orch.step_3_outline(session, novel_id)
            logger.info(f"novel_id={novel_id} 步骤3完成")
        except Exception as exc:
            logger.error(f"novel_id={novel_id} 步骤3失败: {exc}")
            raise

    def _run_step4(
        self, session: Session, chapter: Any, regenerate: bool
    ) -> TaskResult:
        """执行步骤4：单章节细纲生成（幂等保护）"""
        already_done = chapter.detail_outline is not None
        if already_done and not regenerate:
            logger.debug(f"chapter_id={chapter.id} 步骤4已完成，跳过")
            return TaskResult(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                step=4,
                success=True,
                stats={"skipped": True},
            )

        try:
            res = self._orch.step_4_detail_outline(session, chapter.id)
            return TaskResult(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                step=4,
                success=True,
                stats=res.get("stats", {}),
            )
        except Exception as exc:
            logger.warning(f"chapter_id={chapter.id} 步骤4失败: {exc}")
            return TaskResult(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                step=4,
                success=False,
                error=str(exc),
            )

    def _run_step5(
        self, session: Session, chapter: Any, regenerate: bool
    ) -> TaskResult:
        """执行步骤5：单章节正文生成（幂等保护）"""
        already_done = chapter.content is not None and len(chapter.content) > 0
        if already_done and not regenerate:
            logger.debug(f"chapter_id={chapter.id} 步骤5已完成，跳过")
            return TaskResult(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                step=5,
                success=True,
                stats={"skipped": True},
            )

        try:
            res = self._orch.step_5_writing(session, chapter.id)
            return TaskResult(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                step=5,
                success=True,
                stats={
                    "word_count": res.get("word_count", 0),
                    **res.get("stats", {}),
                },
            )
        except Exception as exc:
            logger.warning(f"chapter_id={chapter.id} 步骤5失败: {exc}")
            return TaskResult(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                step=5,
                success=False,
                error=str(exc),
            )
