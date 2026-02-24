"""
Lorebook 引擎单元测试

覆盖：
- 关键词命中世界观条目
- 关键词命中角色条目
- 无关键词时降级为名称匹配
- 未命中时返回空列表
- hit_count 排序正确
- scan_and_format 返回格式兼容
"""
import pytest

from ainovel.db import init_database, novel_crud
from ainovel.db.base import Base
from ainovel.memory import MBTIType, CharacterDatabase, WorldDatabase
from ainovel.memory.lorebook import LorebookEngine


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
def world_db(db_session):
    return WorldDatabase(db_session)


@pytest.fixture
def char_db(db_session):
    return CharacterDatabase(db_session)


class TestLorebookWorldScan:
    def test_explicit_keyword_hit(self, db_session, novel, world_db):
        """显式 lorebook_keywords 命中时返回该条目"""
        loc = world_db.create_location(
            novel_id=novel.id,
            name="青云宗",
            description="东域顶级宗门",
        )
        loc.lorebook_keywords = ["青云宗", "宗门"]
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(novel.id, "张三前往青云宗拜师")
        assert len(result["world"]) == 1
        assert result["world"][0].name == "青云宗"
        assert "青云宗" in result["world"][0].matched_keywords

    def test_no_keyword_fallback_to_name(self, db_session, novel, world_db):
        """无 lorebook_keywords 时，用名称作为隐式关键词"""
        world_db.create_location(
            novel_id=novel.id,
            name="天剑峰",
            description="险峻山峰",
        )
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(novel.id, "主角攀登天剑峰")
        assert len(result["world"]) == 1
        assert result["world"][0].name == "天剑峰"

    def test_no_match_returns_empty(self, db_session, novel, world_db):
        """文本中无任何关键词时返回空列表"""
        world_db.create_location(
            novel_id=novel.id,
            name="幽冥谷",
            description="阴暗山谷",
        )
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(novel.id, "主角在城镇中购买食材")
        assert result["world"] == []

    def test_hit_count_sorting(self, db_session, novel, world_db):
        """命中关键词多的条目排在前面"""
        loc_a = world_db.create_location(novel_id=novel.id, name="A地", description="地点A")
        loc_a.lorebook_keywords = ["剑", "法宝", "宗门"]
        loc_b = world_db.create_location(novel_id=novel.id, name="B地", description="地点B")
        loc_b.lorebook_keywords = ["剑"]
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(novel.id, "主角用剑击碎法宝，震惊宗门")
        assert result["world"][0].name == "A地"
        assert result["world"][0].hit_count == 3

    def test_max_entries_limit(self, db_session, novel, world_db):
        """超出 max_world_entries 时截断"""
        for i in range(5):
            loc = world_db.create_location(
                novel_id=novel.id, name=f"地点{i}", description="desc"
            )
            loc.lorebook_keywords = [f"地点{i}"]
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(
            novel.id,
            "地点0 地点1 地点2 地点3 地点4",
            max_world_entries=3,
        )
        assert len(result["world"]) == 3


class TestLorebookCharacterScan:
    def test_explicit_keyword_hit(self, db_session, novel, char_db):
        """角色显式关键词命中"""
        char = char_db.create_character(
            novel_id=novel.id, name="李逍遥", mbti=MBTIType.ENFP, background="江湖游侠"
        )
        char.lorebook_keywords = ["李逍遥", "逍遥"]
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(novel.id, "逍遥剑法令敌人胆寒")
        assert len(result["character"]) == 1
        assert result["character"][0].name == "李逍遥"

    def test_no_keyword_fallback_to_name(self, db_session, novel, char_db):
        """角色无关键词时用名称匹配"""
        char_db.create_character(
            novel_id=novel.id, name="王小明", mbti=MBTIType.ISTJ, background="普通村民"
        )
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(novel.id, "王小明走进了村庄")
        assert len(result["character"]) == 1
        assert result["character"][0].name == "王小明"

    def test_character_card_format(self, db_session, novel, char_db):
        """角色卡片包含必要字段"""
        char = char_db.create_character(
            novel_id=novel.id, name="赵云", mbti=MBTIType.ENTJ, background="常山赵子龙"
        )
        char_db.add_memory(char.id, event="长坂坡", content="七进七出救阿斗", importance="high")
        db_session.flush()

        engine = LorebookEngine(db_session)
        result = engine.scan(novel.id, "赵云出战")
        card = result["character"][0].content
        assert card["name"] == "赵云"
        assert "mbti" in card
        assert "important_memories" in card
        assert len(card["important_memories"]) == 1


class TestLorebookScanAndFormat:
    def test_returns_compatible_format(self, db_session, novel, world_db, char_db):
        """scan_and_format 返回与 get_world_cards / get_memory_cards 兼容的格式"""
        loc = world_db.create_location(novel_id=novel.id, name="蜀山", description="仙山")
        loc.lorebook_keywords = ["蜀山"]
        char = char_db.create_character(
            novel_id=novel.id, name="飞雪", mbti=MBTIType.INFJ, background="蜀山弟子"
        )
        char.lorebook_keywords = ["飞雪"]
        db_session.flush()

        engine = LorebookEngine(db_session)
        cards = engine.scan_and_format(novel.id, "飞雪登上蜀山")

        assert "world_cards" in cards
        assert "character_cards" in cards
        assert cards["world_cards"][0]["name"] == "蜀山"
        assert "data_type" in cards["world_cards"][0]
        assert cards["character_cards"][0]["name"] == "飞雪"

    def test_no_hits_returns_empty_lists(self, db_session, novel):
        """无命中时返回空列表"""
        engine = LorebookEngine(db_session)
        cards = engine.scan_and_format(novel.id, "无关文本")
        assert cards["world_cards"] == []
        assert cards["character_cards"] == []
