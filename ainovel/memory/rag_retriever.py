"""
RAG 向量检索器

职责：
- 为 PlotArc 生成并缓存 embedding 向量
- 给定查询文本，检索语义最相关的伏笔
- 降级策略：embedding API 不可用时回退到关键词匹配

向量存储方案：
  embedding 直接存入 PlotArc.embedding（JSON 列），无需外部向量数据库。
  相似度计算使用纯 Python 余弦相似度，无需 numpy。

支持的 embedding 后端（按优先级）：
  1. OpenAI text-embedding-3-small（需要 openai 包 + API key）
  2. 降级：基于 jieba 分词的 TF-IDF 余弦相似度（无需额外依赖）
"""
import math
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.memory.plot_arc import PlotArc, PlotArcStatus, plot_arc_crud


# ------------------------------------------------------------------ #
# 工具函数：纯 Python 余弦相似度
# ------------------------------------------------------------------ #

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算两个向量的余弦相似度，纯 Python 实现，无需 numpy"""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ------------------------------------------------------------------ #
# Embedding 后端抽象
# ------------------------------------------------------------------ #

class BaseEmbeddingBackend(ABC):
    """Embedding 后端抽象基类"""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """将文本转换为 embedding 向量"""
        ...

    @property
    @abstractmethod
    def dim(self) -> int:
        """向量维度"""
        ...


class OpenAIEmbeddingBackend(BaseEmbeddingBackend):
    """
    OpenAI text-embedding-3-small 后端

    使用项目已有的 openai 包，无需新增依赖。
    """

    _MODEL = "text-embedding-3-small"
    _DIM = 1536

    def __init__(self, api_key: str, api_base: Optional[str] = None):
        from openai import OpenAI
        self._client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://api.openai.com/v1",
        )

    def embed(self, text: str) -> List[float]:
        resp = self._client.embeddings.create(
            model=self._MODEL,
            input=text,
            encoding_format="float",
        )
        return resp.data[0].embedding

    @property
    def dim(self) -> int:
        return self._DIM


class TFIDFEmbeddingBackend(BaseEmbeddingBackend):
    """
    基于 jieba 分词的 TF-IDF 降级后端

    不调用任何外部 API，完全离线运行。
    向量维度由词表大小决定（动态），相似度计算仍使用余弦相似度。

    注意：此后端为无状态实现，每次 embed 独立计算词频向量，
    适合小规模（<500 条）伏笔检索场景。
    """

    _DIM = 512  # 固定哈希维度，避免词表膨胀

    def embed(self, text: str) -> List[float]:
        """使用字符级 n-gram 哈希向量（无需 jieba 也可运行）"""
        try:
            import jieba
            tokens = list(jieba.cut(text))
        except ImportError:
            # jieba 不可用时降级为字符级 bigram
            tokens = [text[i:i+2] for i in range(len(text) - 1)] or list(text)

        vec = [0.0] * self._DIM
        for token in tokens:
            # 哈希映射到固定维度
            idx = hash(token) % self._DIM
            vec[idx] += 1.0

        # L2 归一化
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    @property
    def dim(self) -> int:
        return self._DIM


def _build_backend(api_key: Optional[str] = None, api_base: Optional[str] = None) -> BaseEmbeddingBackend:
    """
    按优先级构建 embedding 后端：
    1. 有 api_key → OpenAI
    2. 无 api_key → TF-IDF 降级
    """
    if api_key:
        try:
            backend = OpenAIEmbeddingBackend(api_key, api_base)
            logger.info("RAGRetriever 使用 OpenAI embedding 后端")
            return backend
        except Exception as e:
            logger.warning(f"OpenAI embedding 后端初始化失败，降级到 TF-IDF: {e}")
    logger.info("RAGRetriever 使用 TF-IDF 降级后端")
    return TFIDFEmbeddingBackend()


# ------------------------------------------------------------------ #
# RAG 检索器
# ------------------------------------------------------------------ #

class RAGRetriever:
    """
    RAG 向量检索器

    职责：
    1. 为 PlotArc 批量生成并缓存 embedding（懒加载）
    2. 给定查询文本，返回语义最相关的活跃伏笔
    3. embedding API 不可用时自动降级到 TF-IDF

    使用方式：
        retriever = RAGRetriever(session, api_key="sk-...")
        cards = retriever.retrieve(novel_id=1, query="主角发现了神秘古籍", top_k=5)
    """

    def __init__(
        self,
        session: Session,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.session = session
        self._backend = _build_backend(api_key, api_base)

    def embed_text(self, text: str) -> List[float]:
        """将文本转换为 embedding 向量（供外部调用）"""
        return self._backend.embed(text)

    def index_novel(self, novel_id: int, force: bool = False) -> int:
        """
        为小说所有尚未索引的伏笔生成 embedding 并写入数据库

        Args:
            novel_id: 小说 ID
            force: 为 True 时强制重新生成所有 embedding

        Returns:
            本次索引的伏笔数量
        """
        if force:
            arcs = plot_arc_crud.get_by_novel_id(self.session, novel_id)
        else:
            arcs = plot_arc_crud.get_without_embedding(self.session, novel_id)

        count = 0
        for arc in arcs:
            try:
                text = self._arc_to_text(arc)
                arc.embedding = self._backend.embed(text)
                count += 1
            except Exception as e:
                logger.warning(f"伏笔 {arc.id}（{arc.name}）embedding 生成失败: {e}")

        if count:
            self.session.flush()
            logger.info(f"小说 {novel_id} 完成 {count} 条伏笔索引")
        return count

    def retrieve(
        self,
        novel_id: int,
        query: str,
        top_k: int = 5,
        only_active: bool = True,
        min_similarity: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        检索与查询文本语义最相关的伏笔

        Args:
            novel_id: 小说 ID
            query: 查询文本（当前章节大纲、关键事件等）
            top_k: 返回最多 top_k 条结果
            only_active: 为 True 时只检索未回收的伏笔
            min_similarity: 最低相似度阈值，低于此值的结果被过滤

        Returns:
            伏笔卡片列表，按相似度降序排列，每条附加 similarity 字段
        """
        # 1. 获取候选伏笔
        if only_active:
            arcs = plot_arc_crud.get_active(self.session, novel_id, limit=200)
        else:
            arcs = plot_arc_crud.get_by_novel_id(self.session, novel_id)

        if not arcs:
            return []

        # 2. 生成查询向量
        try:
            query_vec = self._backend.embed(query)
        except Exception as e:
            logger.warning(f"查询 embedding 生成失败，降级到关键词匹配: {e}")
            return self._keyword_fallback(arcs, query, top_k)

        # 3. 确保所有候选伏笔都有 embedding（懒加载）
        self._ensure_embeddings(arcs)

        # 4. 计算相似度并排序
        scored: List[Tuple[float, PlotArc]] = []
        for arc in arcs:
            if not arc.embedding:
                continue
            sim = _cosine_similarity(query_vec, arc.embedding)
            if sim >= min_similarity:
                scored.append((sim, arc))

        scored.sort(key=lambda x: x[0], reverse=True)

        # 5. 构建返回卡片
        results = []
        for sim, arc in scored[:top_k]:
            card = arc.to_card()
            card["similarity"] = round(sim, 4)
            results.append(card)

        logger.debug(
            f"RAG 检索完成：novel={novel_id}, query_len={len(query)}, "
            f"candidates={len(arcs)}, returned={len(results)}"
        )
        return results

    # ------------------------------------------------------------------ #
    # 内部方法
    # ------------------------------------------------------------------ #

    def _arc_to_text(self, arc: PlotArc) -> str:
        """将伏笔转换为用于 embedding 的文本"""
        parts = [arc.name, arc.description]
        if arc.related_characters:
            parts.append("相关角色：" + "、".join(arc.related_characters))
        if arc.related_keywords:
            parts.append("关键词：" + "、".join(arc.related_keywords))
        return " ".join(parts)

    def _ensure_embeddings(self, arcs: List[PlotArc]) -> None:
        """对缺少 embedding 的伏笔进行懒加载索引"""
        missing = [arc for arc in arcs if not arc.embedding]
        if not missing:
            return
        for arc in missing:
            try:
                arc.embedding = self._backend.embed(self._arc_to_text(arc))
            except Exception as e:
                logger.warning(f"伏笔 {arc.id} 懒加载 embedding 失败: {e}")
        self.session.flush()

    def _keyword_fallback(
        self, arcs: List[PlotArc], query: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """
        embedding 不可用时的关键词降级检索

        统计伏笔名称、描述、关键词在查询文本中的命中次数，按命中数排序。
        """
        normalized = query.lower()
        scored: List[Tuple[int, PlotArc]] = []
        for arc in arcs:
            keywords = list(arc.related_keywords or []) + [arc.name]
            hits = sum(1 for kw in keywords if kw.strip().lower() in normalized)
            if hits > 0:
                scored.append((hits, arc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for hits, arc in scored[:top_k]:
            card = arc.to_card()
            card["similarity"] = hits / max(len(arc.related_keywords or [arc.name]), 1)
            results.append(card)
        return results
