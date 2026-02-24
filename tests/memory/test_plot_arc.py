"""
PlotArc 伏笔追踪单元测试

覆盖：
- 埋设伏笔（plant）
- 状态推进：planted → developing → resolved
- 放弃伏笔（abandon）
- 查询活跃伏笔（get_active）
- 按状态查询（get_by_status）
- get_active_cards 返回格式与排序
- to_card 字段完整性
"""
import pytest

from ainovel.db import init_database, novel_crud
from ainovel.db.base import Base
from ainovel.memory.plot_arc import PlotArc, PlotArcStatus, PlotArcTracker, plot_arc_crud


@pytest.fixture
def db_session():
    db = init_database("sqlite:///:memory:")
    Base.metadata.create_all(db.engine)
    with db.session_scope() as session:
        yield session


@pytest.fixture
def novel(db_session):
    return novel_crud.create(db_session, title="测试小说", description="desc", author="测试")


@pytest.fixture
def tracker(db_session):
    return PlotArcTracker(db_session)


class TestPlotArcPlant:
    def test_plant_creates_arc(self, db_session, novel, tracker):
        """plant 创建状态为 PLANTED 的伏笔"""
        arc = tracker.plant(
            novel_id=novel.id,
            name="神秘玉佩",
            description="主角在废墟中捡到的玉佩，散发奇异光芒",
            planted_chapter=1,
            related_characters=["李明"],
            related_keywords=["玉佩", "废墟"],
            importance="high",
        )
        assert arc.id is not None
        assert arc.novel_id == novel.id
        assert arc.name == "神秘玉佩"
        assert arc.status == PlotArcStatus.PLANTED
        assert arc.planted_chapter == 1
        assert "李明" in arc.related_characters
        assert arc.importance == "high"

    def test_plant_defaults(self, db_session, novel, tracker):
        """plant 默认值正确"""
        arc = tracker.plant(novel_id=novel.id, name="伏笔A", description="描述A")
        assert arc.status == PlotArcStatus.PLANTED
        assert arc.importance == "medium"
        assert arc.related_characters == []
        assert arc.related_keywords == []

    def test_to_card_fields(self, db_session, novel, tracker):
        """to_card 包含所有必要字段"""
        arc = tracker.plant(
            novel_id=novel.id,
            name="血色月亮",
            description="每逢血月，古老诅咒复苏",
            planted_chapter=3,
            related_characters=["王芳"],
            importance="high",
        )
        card = arc.to_card()
        assert card["name"] == "血色月亮"
        assert card["description"] == "每逢血月，古老诅咒复苏"
        assert card["status"] == "planted"
        assert card["importance"] == "high"
        assert card["planted_chapter"] == 3
        assert "related_characters" in card
        assert "related_keywords" in card


class TestPlotArcStatusTransition:
    def test_develop(self, db_session, novel, tracker):
        """develop 将状态推进到 DEVELOPING"""
        arc = tracker.plant(novel_id=novel.id, name="古剑", description="封印的古剑")
        updated = tracker.develop(arc.id, notes="第5章出现线索")
        assert updated.status == PlotArcStatus.DEVELOPING
        assert updated.notes == "第5章出现线索"

    def test_resolve(self, db_session, novel, tracker):
        """resolve 将状态推进到 RESOLVED 并记录回收章节"""
        arc = tracker.plant(novel_id=novel.id, name="失踪的父亲", description="主角父亲失踪之谜")
        tracker.develop(arc.id)
        resolved = tracker.resolve(arc.id, resolved_chapter=20)
        assert resolved.status == PlotArcStatus.RESOLVED
        assert resolved.resolved_chapter == 20

    def test_abandon(self, db_session, novel, tracker):
        """abandon 将状态设为 ABANDONED"""
        arc = tracker.plant(novel_id=novel.id, name="废弃伏笔", description="不再使用")
        abandoned = tracker.abandon(arc.id)
        assert abandoned.status == PlotArcStatus.ABANDONED

    def test_resolve_nonexistent_returns_none(self, db_session, novel, tracker):
        """对不存在的 ID 操作返回 None"""
        result = tracker.resolve(99999, resolved_chapter=10)
        assert result is None


class TestPlotArcQuery:
    def test_get_active_excludes_resolved(self, db_session, novel, tracker):
        """get_active 不返回已回收或放弃的伏笔"""
        arc1 = tracker.plant(novel_id=novel.id, name="活跃伏笔", description="desc")
        arc2 = tracker.plant(novel_id=novel.id, name="已回收", description="desc")
        tracker.resolve(arc2.id)
        arc3 = tracker.plant(novel_id=novel.id, name="已放弃", description="desc")
        tracker.abandon(arc3.id)

        active = plot_arc_crud.get_active(db_session, novel.id)
        names = [a.name for a in active]
        assert "活跃伏笔" in names
        assert "已回收" not in names
        assert "已放弃" not in names

    def test_get_active_includes_developing(self, db_session, novel, tracker):
        """get_active 包含 DEVELOPING 状态"""
        arc = tracker.plant(novel_id=novel.id, name="发展中", description="desc")
        tracker.develop(arc.id)
        active = plot_arc_crud.get_active(db_session, novel.id)
        assert any(a.name == "发展中" for a in active)

    def test_get_by_status(self, db_session, novel, tracker):
        """get_by_status 按状态精确过滤"""
        tracker.plant(novel_id=novel.id, name="P1", description="d")
        arc2 = tracker.plant(novel_id=novel.id, name="P2", description="d")
        tracker.resolve(arc2.id)

        planted = plot_arc_crud.get_by_status(db_session, novel.id, PlotArcStatus.PLANTED)
        resolved = plot_arc_crud.get_by_status(db_session, novel.id, PlotArcStatus.RESOLVED)
        assert len(planted) == 1
        assert planted[0].name == "P1"
        assert len(resolved) == 1
        assert resolved[0].name == "P2"


class TestGetActiveCards:
    def test_returns_card_format(self, db_session, novel, tracker):
        """get_active_cards 返回卡片列表，包含必要字段"""
        tracker.plant(novel_id=novel.id, name="神器", description="传说中的神器", importance="high")
        cards = tracker.get_active_cards(novel.id)
        assert len(cards) == 1
        card = cards[0]
        assert "name" in card
        assert "description" in card
        assert "status" in card
        assert "importance" in card

    def test_importance_ordering(self, db_session, novel, tracker):
        """get_active_cards 按重要程度排序：high > medium > low"""
        tracker.plant(novel_id=novel.id, name="低优先", description="d", importance="low")
        tracker.plant(novel_id=novel.id, name="高优先", description="d", importance="high")
        tracker.plant(novel_id=novel.id, name="中优先", description="d", importance="medium")

        cards = tracker.get_active_cards(novel.id)
        assert cards[0]["name"] == "高优先"
        assert cards[1]["name"] == "中优先"
        assert cards[2]["name"] == "低优先"

    def test_limit_respected(self, db_session, novel, tracker):
        """get_active_cards 遵守 limit 参数"""
        for i in range(5):
            tracker.plant(novel_id=novel.id, name=f"伏笔{i}", description="d")
        cards = tracker.get_active_cards(novel.id, limit=3)
        assert len(cards) == 3

    def test_empty_when_no_arcs(self, db_session, novel, tracker):
        """无伏笔时返回空列表"""
        cards = tracker.get_active_cards(novel.id)
        assert cards == []
