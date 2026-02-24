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
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.llm import BaseLLMClient
from ainovel.db import chapter_crud, volume_crud
from ainovel.memory import CharacterDatabase, WorldDatabase
from ainovel.memory.lorebook import LorebookEngine
from ainovel.memory.plot_arc import PlotArcTracker
from ainovel.memory.rag_retriever import RAGRetriever


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

    def build_context_bundle(
        self,
        volume_id: int,
        current_order: int,
        window_size: int = 10,
        token_budget: int = 1200,
        novel_id: Optional[int] = None,
        scan_text: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
        embedding_api_base: Optional[str] = None,
        plot_arc_top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        构建章节生成所需的上下文包

        包含四部分：
        1. 前情回顾（压缩后的历史章节）
        2. 角色记忆卡（Lorebook 关键词触发）
        3. 世界观卡片（Lorebook 关键词触发）
        4. 伏笔卡片（RAG 向量检索，按语义相关性排序）

        Args:
            volume_id: 分卷 ID
            current_order: 当前章节序号
            window_size: 回溯章节数
            token_budget: 前情回顾 token 预算
            novel_id: 小说 ID（可选，自动从 volume 推断）
            scan_text: 用于 Lorebook 扫描和 RAG 检索的文本；为 None 时降级为全量返回
            embedding_api_key: embedding API key（可选，不传则使用 TF-IDF 降级）
            embedding_api_base: embedding API base URL（可选）
            plot_arc_top_k: RAG 检索返回的最大伏笔数
        """
        previous_context = self.build_previous_context(
            volume_id=volume_id,
            current_order=current_order,
            window_size=window_size,
            token_budget=token_budget,
        )

        resolved_novel_id = novel_id
        if resolved_novel_id is None:
            volume = volume_crud.get_by_id(self.session, volume_id)
            if volume:
                resolved_novel_id = volume.novel_id

        if resolved_novel_id is None:
            return {
                "previous_context": previous_context,
                "character_memory_cards": [],
                "world_memory_cards": [],
                "plot_arc_cards": [],
            }

        # 有扫描文本时走 Lorebook 按需注入，否则降级到全量返回
        if scan_text:
            lorebook = LorebookEngine(self.session)
            cards = lorebook.scan_and_format(resolved_novel_id, scan_text)
            character_memory_cards = cards["character_cards"]
            world_memory_cards = cards["world_cards"]
        else:
            character_db = CharacterDatabase(self.session)
            world_db = WorldDatabase(self.session)
            character_memory_cards = character_db.get_memory_cards(
                novel_id=resolved_novel_id,
                character_names=[],
                limit_per_character=3,
            )
            world_memory_cards = world_db.get_world_cards(
                novel_id=resolved_novel_id,
                keywords=[],
                limit=8,
            )

        # RAG 伏笔检索：有 scan_text 时语义检索，否则返回活跃伏笔列表
        plot_arc_cards: List[Dict[str, Any]] = []
        try:
            if scan_text:
                rag = RAGRetriever(
                    self.session,
                    api_key=embedding_api_key,
                    api_base=embedding_api_base,
                )
                plot_arc_cards = rag.retrieve(
                    novel_id=resolved_novel_id,
                    query=scan_text,
                    top_k=plot_arc_top_k,
                    only_active=True,
                )
            else:
                tracker = PlotArcTracker(self.session)
                plot_arc_cards = tracker.get_active_cards(
                    resolved_novel_id, limit=plot_arc_top_k
                )
        except Exception as e:
            logger.warning(f"伏笔检索失败，跳过 plot_arc_cards: {e}")

        return {
            "previous_context": previous_context,
            "character_memory_cards": character_memory_cards,
            "world_memory_cards": world_memory_cards,
            "plot_arc_cards": plot_arc_cards,
        }

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
