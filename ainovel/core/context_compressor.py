"""
上下文压缩器

长篇创作时对历史章节进行分层压缩，提高 token 利用率。

压缩策略（基于章节与当前章节的距离）：
- 近章（距离 1-3）：详细摘要，保留关键情节和对话（约 200 字）
- 中章（距离 4-10）：简要摘要，保留核心事件（约 100 字）
- 远章（距离 > 10）：关键事件列表（约 50 字）

缓存机制：压缩结果写入 chapter.summary，避免重复 LLM 调用。
"""
from enum import Enum
from typing import List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.llm import BaseLLMClient
from ainovel.db import chapter_crud


class CompressionLevel(Enum):
    """压缩级别，对应不同的摘要详细程度"""
    DETAILED = "detailed"    # 近章：详细摘要
    BRIEF = "brief"          # 中章：简要摘要
    MINIMAL = "minimal"      # 远章：关键事件列表


# 各压缩级别对应的目标字数和 max_tokens
_LEVEL_CONFIG = {
    CompressionLevel.DETAILED: {"target_words": 200, "max_tokens": 300},
    CompressionLevel.BRIEF:    {"target_words": 100, "max_tokens": 150},
    CompressionLevel.MINIMAL:  {"target_words": 50,  "max_tokens": 80},
}

# 距离阈值
_NEAR_THRESHOLD = 3
_MID_THRESHOLD = 10


def _get_compression_level(distance: int) -> CompressionLevel:
    """根据章节距离返回压缩级别"""
    if distance <= _NEAR_THRESHOLD:
        return CompressionLevel.DETAILED
    if distance <= _MID_THRESHOLD:
        return CompressionLevel.BRIEF
    return CompressionLevel.MINIMAL


class ContextCompressor:
    """
    上下文压缩器

    职责：
    1. 根据章节距离选择压缩级别
    2. 优先使用缓存（chapter.summary），避免重复 LLM 调用
    3. 支持 token 预算控制，动态裁剪上下文长度
    """

    def __init__(self, llm_client: BaseLLMClient, session: Session):
        self.llm_client = llm_client
        self.session = session

    def build_previous_context(
        self,
        volume_id: int,
        current_order: int,
        window_size: int = 10,
        token_budget: int = 800,
    ) -> str:
        """
        构建前情回顾文本

        Args:
            volume_id: 当前分卷 ID
            current_order: 当前章节序号
            window_size: 最多回溯的章节数
            token_budget: 前情回顾允许使用的最大 token 数（粗估：1 token ≈ 1.5 中文字）

        Returns:
            格式化的前情回顾文本
        """
        if current_order <= 1:
            return "本章为开篇，无前情"

        start_order = max(1, current_order - window_size)
        chapters = []
        for order in range(start_order, current_order):
            chapter = chapter_crud.get_by_order(self.session, volume_id, order)
            if chapter and chapter.content:
                chapters.append(chapter)

        if not chapters:
            return "本章为开篇，无前情"

        # 按距离从近到远排序（近章优先占用 token 预算）
        chapters_with_distance = [
            (ch, current_order - ch.order) for ch in chapters
        ]

        parts = self._compress_chapters(chapters_with_distance, token_budget)
        return "\n\n".join(parts)

    def compress_and_cache(self, chapter_id: int) -> str:
        """
        压缩单章内容并缓存到 chapter.summary

        用于批量预压缩场景，提前生成摘要避免生成时实时调用 LLM。

        Args:
            chapter_id: 章节 ID

        Returns:
            压缩后的摘要文本
        """
        chapter = chapter_crud.get_by_id(self.session, chapter_id)
        if chapter is None:
            raise ValueError(f"章节 ID {chapter_id} 不存在")

        if chapter.summary:
            logger.debug(f"章节 {chapter_id} 已有缓存摘要，跳过压缩")
            return chapter.summary

        summary = self._compress_single(chapter.content, CompressionLevel.DETAILED)
        chapter_crud.update(self.session, chapter_id, summary=summary)
        logger.info(f"章节 {chapter_id} 摘要已缓存，长度: {len(summary)} 字")
        return summary

    # ------------------------------------------------------------------ #
    # 内部方法
    # ------------------------------------------------------------------ #

    def _compress_chapters(
        self,
        chapters_with_distance: List[tuple],
        token_budget: int,
    ) -> List[str]:
        """
        按 token 预算压缩章节列表，近章优先分配预算

        Args:
            chapters_with_distance: [(chapter, distance), ...] 按距离升序
            token_budget: 总 token 预算

        Returns:
            各章节压缩文本列表（按原始顺序）
        """
        # 粗估：1 token ≈ 1.5 中文字
        char_budget = int(token_budget * 1.5)
        remaining = char_budget

        result_map = {}  # order -> text

        for chapter, distance in chapters_with_distance:
            if remaining <= 0:
                break

            level = _get_compression_level(distance)
            target = _LEVEL_CONFIG[level]["target_words"]

            # 预算不足时降级压缩
            if remaining < target:
                if remaining >= _LEVEL_CONFIG[CompressionLevel.MINIMAL]["target_words"]:
                    level = CompressionLevel.MINIMAL
                    target = _LEVEL_CONFIG[CompressionLevel.MINIMAL]["target_words"]
                else:
                    break

            text = self._get_or_compress(chapter, level)
            # 截断到实际可用预算
            if len(text) > remaining:
                text = text[:remaining] + "…"

            result_map[chapter.order] = f"第{chapter.order}章 {chapter.title}：{text}"
            remaining -= len(text)

        # 按章节序号升序输出
        return [result_map[order] for order in sorted(result_map)]

    def _get_or_compress(self, chapter, level: CompressionLevel) -> str:
        """
        优先使用缓存摘要，否则实时压缩

        近章（DETAILED）使用缓存或实时生成；
        中章/远章若有缓存直接截取，否则实时生成。
        """
        if chapter.summary:
            cached = chapter.summary
            target = _LEVEL_CONFIG[level]["target_words"]
            # 缓存摘要比目标长时截取
            if len(cached) <= target * 1.5:
                return cached
            return cached[:target] + "…"

        return self._compress_single(chapter.content, level)

    def _compress_single(self, content: str, level: CompressionLevel) -> str:
        """
        调用 LLM 压缩单章内容

        Args:
            content: 章节正文
            level: 压缩级别

        Returns:
            压缩后的摘要
        """
        config = _LEVEL_CONFIG[level]
        target_words = config["target_words"]
        max_tokens = config["max_tokens"]

        # 内容过短时直接截取，不调用 LLM
        if len(content) <= target_words:
            return content

        from ainovel.core.prompt_manager import PromptManager
        prompt = PromptManager.generate_compression_prompt(content, level.value, target_words)

        try:
            response = self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return response["content"].strip()
        except Exception as e:
            logger.warning(f"LLM 压缩失败，降级截取: {e}")
            return content[:target_words] + "…"
