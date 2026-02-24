"""
测试一致性检查生成器
"""
import json
from unittest.mock import Mock

import pytest

from ainovel.db import init_database, novel_crud, volume_crud, chapter_crud
from ainovel.db.base import Base
from ainovel.llm import BaseLLMClient
from ainovel.memory import CharacterDatabase, WorldDatabase, MBTIType
from ainovel.workflow.generators.consistency_generator import ConsistencyGenerator


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
        "content": """```json
{
  "overall_risk": "low",
  "summary": "未发现严重冲突。",
  "issues": []
}
```""",
        "usage": {"input_tokens": 120, "output_tokens": 80, "total_tokens": 200},
        "cost": 0.01,
    }
    return client


def test_check_chapter_success(db_session, mock_llm):
    novel = novel_crud.create(db_session, title="测试小说B", description="desc", author="a")
    volume = volume_crud.create(db_session, novel_id=novel.id, title="卷一", order=1)
    chapter = chapter_crud.create(
        db_session,
        volume_id=volume.id,
        title="第三章",
        order=3,
        content="张三来到青云宗，准备参加内门考核。",
    )
    chapter.summary = "主角参加考核"
    chapter.key_events = json.dumps(["参加考核", "遭遇阻拦"], ensure_ascii=False)
    chapter.characters_involved = json.dumps(["张三"], ensure_ascii=False)
    db_session.flush()

    char_db = CharacterDatabase(db_session)
    world_db = WorldDatabase(db_session)
    zhangsan = char_db.create_character(
        novel_id=novel.id,
        name="张三",
        mbti=MBTIType.INTJ,
        background="天赋异禀",
    )
    char_db.add_memory(zhangsan.id, event="拜师", content="在青云宗外门拜师", importance="high")
    world_db.create_location(
        novel_id=novel.id,
        name="青云宗",
        description="仙门圣地",
    )

    generator = ConsistencyGenerator(mock_llm)
    result = generator.check_chapter(db_session, chapter.id, strict=True)

    assert result["chapter_id"] == chapter.id
    assert result["overall_risk"] == "low"
    assert isinstance(result["issues"], list)
    mock_llm.generate.assert_called_once()


def test_check_chapter_returns_structured_issues(db_session):
    llm = Mock(spec=BaseLLMClient)
    llm.generate.return_value = {
        "content": """```json
{
  "overall_risk": "medium",
  "summary": "存在中等风险冲突。",
  "issues": [
    {
      "severity": "major",
      "type": "character",
      "location": "第2段",
      "description": "角色突然改口不符设定",
      "suggestion": "补充心理动机过渡"
    }
  ]
}
```""",
        "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200},
        "cost": 0.01,
    }

    novel = novel_crud.create(db_session, title="测试小说C", description="desc", author="a")
    volume = volume_crud.create(db_session, novel_id=novel.id, title="卷一", order=1)
    chapter = chapter_crud.create(
        db_session,
        volume_id=volume.id,
        title="第一章",
        order=1,
        content="测试正文",
    )

    generator = ConsistencyGenerator(llm)
    result = generator.check_chapter(db_session, chapter.id)

    issue = result["issues"][0]
    assert issue["severity"] == "major"
    assert issue["type"] == "character"
    assert "location" in issue
    assert "suggestion" in issue
