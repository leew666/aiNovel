"""
小说导入与改写

将原始小说文本解析为章节，并落库后逐章改写。
"""
from __future__ import annotations

import re
from typing import List, Tuple, Dict, Any

from sqlalchemy.orm import Session

from ainovel.llm.base import BaseLLMClient
from ainovel.db.crud import novel_crud, volume_crud, chapter_crud
from ainovel.db.novel import WorkflowStatus
from ainovel.core.chapter_rewriter import ChapterRewriter


CHAPTER_TITLE_PATTERN = re.compile(
    r"^\s*("
    r"第\s*[0-9一二三四五六七八九十百千]+\s*[章节回卷].*"
    r"|Chapter\s+\d+.*"
    r"|CHAPTER\s+\d+.*"
    r"|CHAPTER\s+[IVXLC]+.*"
    r")\s*$"
)


def split_chapters(raw_text: str) -> List[Tuple[str, str]]:
    """
    将原始文本拆分为章节列表。

    Returns:
        [(title, content), ...]
    """
    text = (raw_text or "").strip()
    if not text:
        return []

    lines = text.splitlines()
    chapters: List[Tuple[str, str]] = []
    current_title: str | None = None
    current_lines: List[str] = []

    def _flush():
        nonlocal current_title, current_lines
        if current_title is None:
            return
        content = "\n".join(current_lines).strip()
        if content:
            chapters.append((current_title, content))
        current_title = None
        current_lines = []

    for line in lines:
        if CHAPTER_TITLE_PATTERN.match(line.strip()):
            _flush()
            current_title = line.strip()
            current_lines = []
            continue
        if current_title is None:
            current_title = "第1章"
        current_lines.append(line)

    _flush()

    if not chapters:
        return [("第1章", text)]
    return chapters


def import_and_rewrite_novel(
    session: Session,
    llm_client: BaseLLMClient,
    *,
    title: str,
    author: str | None,
    genre: str | None,
    description: str | None,
    raw_text: str,
    instruction: str,
    rewrite_mode: str = "rewrite",
    preserve_plot: bool = True,
    volume_title: str = "导入卷",
) -> Dict[str, Any]:
    """
    导入原始小说并逐章改写。

    Returns:
        统计结果
    """
    existing = novel_crud.get_by_title(session, title)
    if existing:
        raise ValueError(f"小说标题已存在: {title}")

    chapters = split_chapters(raw_text)
    if not chapters:
        raise ValueError("导入文本为空，无法解析章节")

    novel = novel_crud.create(
        session,
        title=title,
        author=author,
        genre=genre,
        description=description or "",
    )

    volume = volume_crud.create(
        session,
        novel_id=novel.id,
        title=volume_title,
        order=1,
        description="导入的原始章节",
    )

    created_chapters = []
    for idx, (chapter_title, content) in enumerate(chapters, start=1):
        chapter = chapter_crud.create(
            session,
            volume_id=volume.id,
            title=chapter_title or f"第{idx}章",
            order=idx,
            content=content,
        )
        chapter.update_word_count()
        created_chapters.append(chapter)

    session.commit()

    rewriter = ChapterRewriter(llm_client, session)
    stats = {
        "total": len(created_chapters),
        "succeeded": 0,
        "failed": 0,
        "errors": [],
        "chapter_results": [],
    }

    for chapter in created_chapters:
        try:
            result = rewriter.rewrite(
                chapter_id=chapter.id,
                instruction=instruction,
                target_scope="chapter",
                preserve_plot=preserve_plot,
                rewrite_mode=rewrite_mode,
                save=True,
            )
            stats["succeeded"] += 1
            stats["chapter_results"].append(
                {
                    "chapter_id": chapter.id,
                    "chapter_title": chapter.title,
                    "token_usage": result.get("usage", {}).get("total_tokens"),
                    "cost": result.get("cost"),
                    "saved": result.get("saved"),
                }
            )
        except Exception as exc:
            stats["failed"] += 1
            stats["errors"].append(
                {
                    "chapter_id": chapter.id,
                    "chapter_title": chapter.title,
                    "error": str(exc),
                }
            )

    novel.workflow_status = WorkflowStatus.WRITING
    novel.current_step = max(novel.current_step, 5)
    session.commit()

    stats.update({"novel_id": novel.id, "volume_id": volume.id})
    return stats
