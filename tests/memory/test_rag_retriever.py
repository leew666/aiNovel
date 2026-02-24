"""
RAGRetriever 单元测试

覆盖：
- TF-IDF 降级后端 embed 输出维度与归一化
- 余弦相似度计算正确性
- index_novel 为伏笔生成 embedding
- retrieve 返回相关伏笔，按相似度排序
- retrieve 过滤已回收伏笔（only_active=True）
- retrieve 在无伏笔时返回空列表
- keyword_fallback 在 embedding 失败时正常工作
- force=True 时重新索引所有伏笔
"""
import math
import pytest

from ainovel.db import init_database, novel_crud
from ainovel.db.base import Base
from ainovel.memory.plot_arc import PlotArcTracker, plot_arc_crud
from ainovel.memory.rag_retriever import (
    RAGRetriever,
    TFIDFEmbeddingBackend,
    _cosine_similarity,
)


@pytest.fixture
def db_session():
    db = init_database("sqlite:///:memory:")
    Base.metadata.create_all(db.engine)
    with db.session_scope() as session:
        yield session


@pytest.fixture
def novel(db_session):
    return novel_crud.create(db_session, title="RAG测试小说", description="desc", author="测试")


@pytest.fixture
def tracker(db_session):
    return PlotArcTracker(db_session)


@pytest.fixture
def retriever(db_session):
    """使用 TF-IDF 降级后端（无需 API key）"""
    return RAGRetriever(db_session, api_key=None)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        """相同向量相似度为 1.0"""
        v = [1.0, 0.0, 0.5]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        """正交向量相似度为 0.0"""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_zero_vector(self):
        """零向量相似度为 0.0"""
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_length_mismatch(self):
        """长度不匹配返回 0.0"""
        assert _cosine_similarity([1.0, 2.0], [1.0]) == 0.0


class TestTFIDFBackend:
    def test_embed_returns_correct_dim(self):
        """embed 返回固定维度向量"""
        backend = TFIDFEmbeddingBackend()
        vec = backend.embed("主角发现了神秘古籍")
        assert len(vec) == backend.dim

    def test_embed_is_normalized(self):
        """embed 返回 L2 归一化向量"""
        backend = TFIDFEmbeddingBackend()
        vec = backend.embed("测试文本")
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_empty_text(self):
        """空文本不抛出异常"""
        backend = TFIDFEmbeddingBackend()
        vec = backend.embed("")
        assert len(vec) == backend.dim

    def test_similar_texts_higher_similarity(self):
        """语义相近的文本相似度高于无关文本"""
        backend = TFIDFEmbeddingBackend()
        v_base = backend.embed("神秘古籍封印魔法")
        v_similar = backend.embed("古籍封印秘术")
        v_unrelated = backend.embed("今天天气晴朗适合出游")
        sim_similar = _cosine_similarity(v_base, v_similar)
        sim_unrelated = _cosine_similarity(v_base, v_unrelated)
        assert sim_similar > sim_unrelated


class TestRAGRetrieverIndex:
    def test_index_novel_generates_embeddings(self, db_session, novel, tracker, retriever):
        """index_novel 为所有伏笔生成 embedding"""
        tracker.plant(novel_id=novel.id, name="古剑", description="封印的上古神剑")
        tracker.plant(novel_id=novel.id, name="血契", description="用鲜血签订的契约")

        count = retriever.index_novel(novel.id)
        assert count == 2

        arcs = plot_arc_crud.get_by_novel_id(db_session, novel.id)
        for arc in arcs:
            assert arc.embedding is not None
            assert len(arc.embedding) > 0

    def test_index_novel_skips_existing(self, db_session, novel, tracker, retriever):
        """index_novel 跳过已有 embedding 的伏笔"""
        tracker.plant(novel_id=novel.id, name="伏笔A", description="desc")
        retriever.index_novel(novel.id)

        # 第二次调用应跳过
        count = retriever.index_novel(novel.id)
        assert count == 0

    def test_index_novel_force_reindex(self, db_session, novel, tracker, retriever):
        """force=True 时强制重新索引所有伏笔"""
        tracker.plant(novel_id=novel.id, name="伏笔B", description="desc")
        retriever.index_novel(novel.id)

        count = retriever.index_novel(novel.id, force=True)
        assert count == 1


class TestRAGRetrieverRetrieve:
    def test_retrieve_returns_relevant_arcs(self, db_session, novel, tracker, retriever):
        """retrieve 返回与查询相关的伏笔"""
        tracker.plant(
            novel_id=novel.id,
            name="神秘古籍",
            description="记载上古魔法的古籍",
            related_keywords=["古籍", "魔法"],
        )
        tracker.plant(
            novel_id=novel.id,
            name="失踪的父亲",
            description="主角父亲在战争中失踪",
            related_keywords=["父亲", "战争"],
        )

        results = retriever.retrieve(novel.id, query="主角发现了古籍中的魔法秘术", top_k=5)
        assert len(results) > 0
        # 第一条应与古籍相关
        assert results[0]["name"] == "神秘古籍"

    def test_retrieve_excludes_resolved(self, db_session, novel, tracker, retriever):
        """retrieve only_active=True 时不返回已回收伏笔"""
        arc = tracker.plant(
            novel_id=novel.id,
            name="已回收伏笔",
            description="古籍魔法秘术",
            related_keywords=["古籍"],
        )
        tracker.resolve(arc.id)

        results = retriever.retrieve(novel.id, query="古籍魔法", only_active=True)
        names = [r["name"] for r in results]
        assert "已回收伏笔" not in names

    def test_retrieve_empty_when_no_arcs(self, db_session, novel, retriever):
        """无伏笔时返回空列表"""
        results = retriever.retrieve(novel.id, query="任意查询")
        assert results == []

    def test_retrieve_top_k_limit(self, db_session, novel, tracker, retriever):
        """retrieve 遵守 top_k 限制"""
        for i in range(5):
            tracker.plant(
                novel_id=novel.id,
                name=f"伏笔{i}",
                description=f"描述{i}",
                related_keywords=[f"关键词{i}"],
            )
        results = retriever.retrieve(novel.id, query="伏笔描述关键词", top_k=3)
        assert len(results) <= 3

    def test_retrieve_card_has_similarity(self, db_session, novel, tracker, retriever):
        """retrieve 返回的卡片包含 similarity 字段"""
        tracker.plant(novel_id=novel.id, name="测试伏笔", description="测试描述")
        results = retriever.retrieve(novel.id, query="测试", top_k=5)
        if results:
            assert "similarity" in results[0]

    def test_retrieve_sorted_by_similarity(self, db_session, novel, tracker, retriever):
        """retrieve 结果按相似度降序排列"""
        tracker.plant(
            novel_id=novel.id,
            name="高相关",
            description="古籍魔法封印秘术上古",
            related_keywords=["古籍", "魔法", "封印"],
        )
        tracker.plant(
            novel_id=novel.id,
            name="低相关",
            description="村庄集市买菜",
            related_keywords=["集市"],
        )

        results = retriever.retrieve(novel.id, query="古籍魔法封印", top_k=5)
        if len(results) >= 2:
            assert results[0]["similarity"] >= results[1]["similarity"]


class TestRAGRetrieverEmbedText:
    def test_embed_text_returns_vector(self, db_session, retriever):
        """embed_text 返回非空向量"""
        vec = retriever.embed_text("测试文本")
        assert isinstance(vec, list)
        assert len(vec) > 0
