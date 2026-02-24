"""
章节改写器

提供段落级与整章级改写能力。
"""
import json
import re
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from ainovel.llm import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.db import chapter_crud


class ChapterRewriter:
    """章节改写服务"""

    def __init__(self, llm_client: BaseLLMClient, session: Session):
        self.llm_client = llm_client
        self.session = session

    def rewrite(
        self,
        chapter_id: int,
        instruction: str,
        target_scope: str = "paragraph",
        range_start: Optional[int] = None,
        range_end: Optional[int] = None,
        preserve_plot: bool = True,
        rewrite_mode: str = "rewrite",
        save: bool = False,
        temperature: float = 0.5,
        max_tokens: int = 3000,
    ) -> Dict[str, Any]:
        """
        改写章节内容。

        Args:
            chapter_id: 章节ID
            instruction: 改写指令
            target_scope: paragraph | chapter
            range_start: 段落起始（1-based）
            range_end: 段落结束（1-based）
            preserve_plot: 是否保持主线剧情
            rewrite_mode: rewrite | polish | expand
            save: 是否落库
        """
        chapter = chapter_crud.get_by_id(self.session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")
        if not chapter.content:
            raise ValueError(f"章节内容为空，无法改写: {chapter_id}")
        if not instruction or not instruction.strip():
            raise ValueError("instruction 不能为空")

        original_content = chapter.content
        scope = (target_scope or "paragraph").lower().strip()
        if scope not in {"paragraph", "chapter"}:
            raise ValueError("target_scope 仅支持 paragraph 或 chapter")

        if scope == "chapter":
            source_content = original_content
            rewritten_scope_meta = {"scope": "chapter"}
            rewritten_text, llm_meta = self._rewrite_text(
                source_content=source_content,
                instruction=instruction,
                rewrite_mode=rewrite_mode,
                preserve_plot=preserve_plot,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            new_content = rewritten_text
        else:
            paragraphs = self._split_paragraphs(original_content)
            if not paragraphs:
                raise ValueError("章节无可改写段落")

            start = range_start or 1
            end = range_end or start
            if start < 1 or end < start or end > len(paragraphs):
                raise ValueError(
                    f"段落范围无效: start={start}, end={end}, total={len(paragraphs)}"
                )

            selected = "\n\n".join(paragraphs[start - 1 : end])
            rewritten_text, llm_meta = self._rewrite_text(
                source_content=selected,
                instruction=instruction,
                rewrite_mode=rewrite_mode,
                preserve_plot=preserve_plot,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            rewritten_paragraphs = self._split_paragraphs(rewritten_text)
            paragraphs[start - 1 : end] = rewritten_paragraphs
            new_content = "\n\n".join(paragraphs)
            rewritten_scope_meta = {
                "scope": "paragraph",
                "range_start": start,
                "range_end": end,
                "paragraphs_total": len(paragraphs),
            }

        diff_summary = self._build_diff_summary(original_content, new_content)
        history_id = self._append_rewrite_history(
            chapter_id=chapter_id,
            chapter_title=chapter.title,
            instruction=instruction,
            rewrite_mode=rewrite_mode,
            scope_meta=rewritten_scope_meta,
            original_content=original_content,
            new_content=new_content,
        )

        if save:
            chapter_crud.update(self.session, chapter_id, content=new_content)
            updated = chapter_crud.get_by_id(self.session, chapter_id)
            if updated:
                updated.update_word_count()
            self.session.flush()
            logger.info(f"章节改写已保存: chapter_id={chapter_id}, history_id={history_id}")

        return {
            "chapter_id": chapter_id,
            "chapter_title": chapter.title,
            "rewrite_mode": rewrite_mode,
            "target_scope": rewritten_scope_meta["scope"],
            "range_start": rewritten_scope_meta.get("range_start"),
            "range_end": rewritten_scope_meta.get("range_end"),
            "instruction": instruction,
            "preserve_plot": preserve_plot,
            "original_content": original_content,
            "new_content": new_content,
            "diff_summary": diff_summary,
            "saved": save,
            "history_id": history_id,
            "usage": llm_meta.get("usage", {}),
            "cost": llm_meta.get("cost", 0),
            "model": llm_meta.get("model"),
        }

    def rollback(
        self,
        chapter_id: int,
        history_id: Optional[str] = None,
        save: bool = True,
    ) -> Dict[str, Any]:
        """
        回滚章节到历史版本。

        Args:
            chapter_id: 章节ID
            history_id: 指定历史ID；为空时回滚到最近一次
            save: 是否落库（默认 True）
        """
        chapter = chapter_crud.get_by_id(self.session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        history_records = self._read_rewrite_history(chapter_id)
        if not history_records:
            raise ValueError("未找到可回滚的改写历史")

        target = None
        if history_id:
            for record in history_records:
                if record.get("history_id") == history_id:
                    target = record
                    break
            if target is None:
                raise ValueError(f"未找到指定 history_id: {history_id}")
        else:
            target = history_records[-1]

        rollback_content = target.get("original_content") or ""
        if not rollback_content:
            raise ValueError("历史记录缺少 original_content，无法回滚")

        if save:
            chapter_crud.update(self.session, chapter_id, content=rollback_content)
            updated = chapter_crud.get_by_id(self.session, chapter_id)
            if updated:
                updated.update_word_count()
            self.session.flush()

        return {
            "chapter_id": chapter_id,
            "chapter_title": chapter.title,
            "history_id": target.get("history_id"),
            "rolled_back_content": rollback_content,
            "saved": save,
        }

    def _rewrite_text(
        self,
        source_content: str,
        instruction: str,
        rewrite_mode: str,
        preserve_plot: bool,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, Dict[str, Any]]:
        prompt = PromptManager.generate_rewrite_prompt(
            source_content=source_content,
            instruction=instruction,
            rewrite_mode=rewrite_mode,
            preserve_plot=preserve_plot,
        )
        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = (response.get("content") or "").strip()
        if not text:
            raise ValueError("改写结果为空")
        return text, response

    @staticmethod
    def _split_paragraphs(text: str) -> List[str]:
        return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    @staticmethod
    def _build_diff_summary(original: str, rewritten: str) -> str:
        ratio = SequenceMatcher(None, original, rewritten).ratio()
        original_len = len(original)
        rewritten_len = len(rewritten)
        delta = rewritten_len - original_len
        return (
            f"相似度: {ratio:.2%}; 原长度: {original_len}; 新长度: {rewritten_len}; "
            f"变化: {delta:+d} 字符"
        )

    @staticmethod
    def _append_rewrite_history(
        chapter_id: int,
        chapter_title: str,
        instruction: str,
        rewrite_mode: str,
        scope_meta: Dict[str, Any],
        original_content: str,
        new_content: str,
    ) -> str:
        """
        记录改写历史到本地 jsonl，便于回滚。
        """
        history_dir = Path("data/projects")
        history_dir.mkdir(parents=True, exist_ok=True)
        history_path = history_dir / f"chapter_{chapter_id}_rewrite_history.jsonl"

        history_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        record = {
            "history_id": history_id,
            "timestamp": datetime.utcnow().isoformat(),
            "chapter_id": chapter_id,
            "chapter_title": chapter_title,
            "instruction": instruction,
            "rewrite_mode": rewrite_mode,
            "scope": scope_meta,
            "original_content": original_content,
            "new_content": new_content,
        }
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return history_id

    @staticmethod
    def _read_rewrite_history(chapter_id: int) -> List[Dict[str, Any]]:
        history_path = Path("data/projects") / f"chapter_{chapter_id}_rewrite_history.jsonl"
        if not history_path.exists():
            return []
        records: List[Dict[str, Any]] = []
        for line in history_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records
