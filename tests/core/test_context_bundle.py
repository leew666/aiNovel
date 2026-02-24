"""
测试上下文包构建（前情 + 角色记忆卡 + 世界观卡片）
"""
from unittest.mock import Mock

import pytest

from ainovel.core.context_compressor import ContextCompressor
from ainovel.db import init_database, novel_crud, volume_crud, chapter_crud
from ainovel.db.base import Base
from ainovel.llm import BaseLLMClient
from ainovel.memory import CharacterDatabase, WorldDatabase, MBTIType


@pytest.fixture
def db_session():
    db = init_database("sqlite:///:memory:")
    Base.metadata.create_all(db.engine)
    with db.session_scope() as session:
        yield session


@pytest.fixture
def mock_llm():
    client = Mock(spec=BaseLLMClient)
    client.generate.return_value = {
        "content": "主角拜入宗门，获得初始功法，结识同门。",
        "usage": {"input_tokens": 30, "output_tokens": 20, "total_tokens": 50},
        "cost": 0.001,
    }
    return client


def test_build_context_bundle_contains_three_sections(db_session, mock_llm):
    novel = novel_crud.create(db_session, title="测试小说A", description="desc", author="a")
    volume = volume_crud.create(db_session, novel_id=novel.id, title="卷一", order=1)
    chapter_crud.create(
        db_session,
        volume_id=volume.id,
        title="第一章",
        order=1,
        content="第一章正文" * 80,
    )
    chapter_crud.create(
        db_session,
        volume_id=volume.id,
        title="第二章",
        order=2,
        content="第二章正文" * 80,
    )

    char_db = CharacterDatabase(db_session)
    world_db = WorldDatabase(db_session)

    zhangsan = char_db.create_character(
        novel_id=novel.id,
        name="张三",
        mbti=MBTIType.INTJ,
        background="出身寒门",
    )
    char_db.add_memory(zhangsan.id, event="拜师", content="在青云宗外门拜师", importance="high")
    world_db.create_location(
        novel_id=novel.id,
        name="青云宗",
        description="东域顶级宗门",
    )

    compressor = ContextCompressor(mock_llm, db_session)
    bundle = compressor.build_context_bundle(
        volume_id=volume.id,
        current_order=3,
        novel_id=novel.id,
        scan_text="张三在青云宗拜师，踏上修炼之路",
    )

    assert "previous_context" in bundle
    assert "character_memory_cards" in bundle
    assert "world_memory_cards" in bundle
    assert "第1章" in bundle["previous_context"]
    assert bundle["character_memory_cards"][0]["name"] == "张三"
    assert bundle["world_memory_cards"][0]["name"] == "青云宗"
