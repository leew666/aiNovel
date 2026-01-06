"""
记忆管理层单元测试

测试 Character、WorldData 模型和服务类
"""
import pytest
from ainovel.db import init_database, Novel, NovelStatus, novel_crud
from ainovel.memory import (
    Character,
    MBTIType,
    WorldData,
    WorldDataType,
    CharacterDatabase,
    WorldDatabase,
)


@pytest.fixture
def db():
    """创建内存数据库用于测试"""
    database = init_database("sqlite:///:memory:", echo=False)
    database.create_all_tables()
    yield database


@pytest.fixture
def session(db):
    """创建数据库会话"""
    with db.session_scope() as sess:
        yield sess


@pytest.fixture
def novel(session):
    """创建测试小说"""
    novel = novel_crud.create(session, title="测试小说", author="测试作者")
    session.commit()
    return novel


def test_create_character(session, novel):
    """测试创建角色"""
    char_db = CharacterDatabase(session)
    character = char_db.create_character(
        novel_id=novel.id,
        name="张三",
        mbti=MBTIType.INTJ,
        background="一个聪明的少年",
        personality_traits={"勇敢": 8, "智慧": 9},
    )

    assert character.id is not None
    assert character.name == "张三"
    assert character.mbti == MBTIType.INTJ
    assert character.personality_traits["勇敢"] == 8
    assert character.personality_traits["智慧"] == 9


def test_add_memory(session, novel):
    """测试添加角色记忆"""
    char_db = CharacterDatabase(session)
    character = char_db.create_character(
        novel_id=novel.id, name="李四", mbti=MBTIType.ENFP, background="活泼的少女"
    )

    char_db.add_memory(
        character_id=character.id,
        event="初遇师父",
        content="在青云山遇见了师父，开始修炼",
        chapter_id=1,
        importance="high",
    )

    memories = char_db.get_character_memories(character.id)
    assert len(memories) == 1
    assert memories[0]["event"] == "初遇师父"
    assert memories[0]["importance"] == "high"


def test_add_relationship(session, novel):
    """测试添加角色关系"""
    char_db = CharacterDatabase(session)
    character = char_db.create_character(
        novel_id=novel.id, name="王五", mbti=MBTIType.ISTJ, background="稳重的少年"
    )

    char_db.add_relationship(
        character_id=character.id,
        target_character_name="张三",
        relation_type="朋友",
        intimacy=7,
        notes="一起修炼的好朋友",
    )

    relationships = char_db.get_character_relationships(character.id)
    assert "张三" in relationships
    assert relationships["张三"]["relation_type"] == "朋友"
    assert relationships["张三"]["intimacy"] == 7


def test_list_characters_by_mbti(session, novel):
    """测试根据 MBTI 查询角色"""
    char_db = CharacterDatabase(session)
    char_db.create_character(novel_id=novel.id, name="角色1", mbti=MBTIType.INTJ, background="背景1")
    char_db.create_character(novel_id=novel.id, name="角色2", mbti=MBTIType.INTJ, background="背景2")
    char_db.create_character(novel_id=novel.id, name="角色3", mbti=MBTIType.ENFP, background="背景3")
    session.commit()

    intj_characters = char_db.list_characters_by_mbti(novel.id, MBTIType.INTJ)
    assert len(intj_characters) == 2


def test_get_mbti_description(session, novel):
    """测试获取 MBTI 描述"""
    char_db = CharacterDatabase(session)
    character = char_db.create_character(
        novel_id=novel.id, name="测试角色", mbti=MBTIType.INTJ, background="测试"
    )

    description = character.get_mbti_description()
    assert "建筑师" in description
    assert "独立" in description


def test_create_location(session, novel):
    """测试创建地点"""
    world_db = WorldDatabase(session)
    location = world_db.create_location(
        novel_id=novel.id,
        name="青云山",
        description="仙门所在的灵山",
        coordinates="东经120°，北纬30°",
        climate="四季如春",
        population=10000,
        notable_features="山顶有仙气缭绕",
    )

    assert location.id is not None
    assert location.name == "青云山"
    assert location.data_type == WorldDataType.LOCATION
    assert location.properties["climate"] == "四季如春"


def test_create_organization(session, novel):
    """测试创建组织"""
    world_db = WorldDatabase(session)
    organization = world_db.create_organization(
        novel_id=novel.id,
        name="青云宗",
        description="正道第一大宗门",
        leader="掌门张无忌",
        members_count=5000,
        power_level="一流",
    )

    assert organization.name == "青云宗"
    assert organization.data_type == WorldDataType.ORGANIZATION
    assert organization.properties["leader"] == "掌门张无忌"


def test_create_item(session, novel):
    """测试创建物品"""
    world_db = WorldDatabase(session)
    item = world_db.create_item(
        novel_id=novel.id,
        name="紫霄剑",
        description="上古神剑",
        rarity="传说",
        power_level=10,
        owner="主角",
        abilities="可斩断虚空",
    )

    assert item.name == "紫霄剑"
    assert item.data_type == WorldDataType.ITEM
    assert item.properties["power_level"] == 10


def test_create_rule(session, novel):
    """测试创建规则"""
    world_db = WorldDatabase(session)
    rule = world_db.create_rule(
        novel_id=novel.id,
        name="修炼等级",
        description="本世界的修炼体系",
        category="修炼系统",
        limitations="每提升一个大境界需要渡劫",
    )

    assert rule.name == "修炼等级"
    assert rule.data_type == WorldDataType.RULE
    assert rule.properties["category"] == "修炼系统"


def test_list_by_type(session, novel):
    """测试按类型查询世界观数据"""
    world_db = WorldDatabase(session)
    world_db.create_location(novel_id=novel.id, name="地点1", description="描述1")
    world_db.create_location(novel_id=novel.id, name="地点2", description="描述2")
    world_db.create_organization(novel_id=novel.id, name="组织1", description="描述3")
    session.commit()

    locations = world_db.list_locations(novel.id)
    assert len(locations) == 2

    organizations = world_db.list_organizations(novel.id)
    assert len(organizations) == 1


def test_search_world_data(session, novel):
    """测试搜索世界观数据"""
    world_db = WorldDatabase(session)
    world_db.create_location(novel_id=novel.id, name="青云山", description="仙山")
    world_db.create_location(novel_id=novel.id, name="红云峰", description="山峰")
    session.commit()

    results = world_db.search(novel.id, "云")
    assert len(results) == 2


def test_delete_character(session, novel):
    """测试删除角色"""
    char_db = CharacterDatabase(session)
    character = char_db.create_character(
        novel_id=novel.id, name="待删除角色", mbti=MBTIType.INTJ, background="测试"
    )
    session.commit()

    # 删除角色
    result = char_db.delete_character(character.id)
    session.commit()

    assert result is True
    assert char_db.get_character(character.id) is None


def test_delete_world_data(session, novel):
    """测试删除世界观数据"""
    world_db = WorldDatabase(session)
    location = world_db.create_location(novel_id=novel.id, name="待删除地点", description="测试")
    session.commit()

    # 删除世界观数据
    result = world_db.delete_world_data(location.id)
    session.commit()

    assert result is True
    assert world_db.get_world_data(location.id) is None
