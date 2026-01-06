"""
测试流程编排层功能
"""
import pytest
import json
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from ainovel.workflow import (
    WorkflowOrchestrator,
    PlanningGenerator,
    WorldBuildingGenerator,
    DetailOutlineGenerator,
)
from ainovel.llm import BaseLLMClient
from ainovel.db import init_database
from ainovel.db import novel_crud, volume_crud, chapter_crud
from ainovel.db.novel import WorkflowStatus
from ainovel.memory import CharacterDatabase, WorldDatabase, MBTIType, WorldDataType


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    db = init_database("sqlite:///:memory:")
    # 创建所有表
    from ainovel.db.base import Base
    from ainovel.db.novel import Novel
    from ainovel.db.volume import Volume
    from ainovel.db.chapter import Chapter
    from ainovel.memory.character import Character
    from ainovel.memory.world_data import WorldData

    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        yield session


@pytest.fixture
def mock_llm_client():
    """创建Mock LLM客户端"""
    client = Mock(spec=BaseLLMClient)
    return client


@pytest.fixture
def test_novel(db_session):
    """创建测试小说"""
    novel = novel_crud.create(
        db_session,
        title="测试小说",
        description="我想写一个修仙题材的小说，主角是天才少年",
        author="测试作者",
    )
    return novel


@pytest.fixture
def character_db(db_session):
    """创建角色数据库实例"""
    return CharacterDatabase(db_session)


@pytest.fixture
def world_db(db_session):
    """创建世界观数据库实例"""
    return WorldDatabase(db_session)


@pytest.fixture
def orchestrator(mock_llm_client, character_db, world_db):
    """创建流程编排器"""
    return WorkflowOrchestrator(mock_llm_client, character_db, world_db)


class TestPlanningGenerator:
    """测试创作思路生成器"""

    def test_generate_planning(self, mock_llm_client):
        """测试生成创作思路"""
        # Mock LLM响应
        mock_response = {
            "content": """```json
{
  "genre": "玄幻",
  "theme": "成长",
  "target_audience": "青年读者",
  "tone": "热血激昂",
  "core_conflict": "主角追求武学极致，对抗邪恶势力",
  "story_arc": "入门、修炼、历练、突破、巅峰",
  "estimated_length": {
    "volumes": 3,
    "chapters_per_volume": 10,
    "words_per_chapter": 3000
  },
  "key_features": ["天才主角", "修仙体系", "热血战斗"],
  "challenges": ["保持节奏: 合理分配战斗和日常情节"]
}
```""",
            "usage": {"input_tokens": 100, "output_tokens": 200},
            "cost": 0.01,
        }
        mock_llm_client.generate.return_value = mock_response

        generator = PlanningGenerator(mock_llm_client)
        result = generator.generate_planning("我想写一个修仙小说")

        assert "planning" in result
        assert result["planning"]["genre"] == "玄幻"
        assert result["planning"]["theme"] == "成长"
        mock_llm_client.generate.assert_called_once()


class TestWorldBuildingGenerator:
    """测试世界背景和角色生成器"""

    def test_generate_world_building(self, mock_llm_client, character_db, world_db):
        """测试生成世界观和角色"""
        # Mock LLM响应
        mock_response = {
            "content": """```json
{
  "world_data": [
    {
      "data_type": "location",
      "name": "青云宗",
      "description": "主角所在的修仙宗门",
      "properties": {"region": "东域"}
    }
  ],
  "characters": [
    {
      "name": "张三",
      "role": "protagonist",
      "mbti": "INTJ",
      "background": "天才剑客",
      "personality_traits": {"开放性": 8, "责任心": 7},
      "goals": "成为天下第一剑仙",
      "conflicts": "追求力量与道义的冲突"
    }
  ]
}
```""",
            "usage": {"input_tokens": 100, "output_tokens": 300},
            "cost": 0.02,
        }
        mock_llm_client.generate.return_value = mock_response

        generator = WorldBuildingGenerator(mock_llm_client, character_db, world_db)
        result = generator.generate_world_building('{"genre": "玄幻"}')

        assert "world_building" in result
        assert len(result["world_building"]["world_data"]) == 1
        assert len(result["world_building"]["characters"]) == 1


class TestDetailOutlineGenerator:
    """测试详细细纲生成器"""

    def test_generate_detail_outline(
        self, db_session, mock_llm_client, test_novel
    ):
        """测试生成详细细纲"""
        # 创建测试分卷和章节
        volume = volume_crud.create(
            db_session,
            novel_id=test_novel.id,
            title="第一卷",
            description="入门篇",
            order=1,
        )
        chapter = chapter_crud.create(
            db_session,
            volume_id=volume.id,
            title="第一章",
            order=1,
            content="",
        )
        chapter.summary = "主角觉醒天赋"
        chapter.key_events = json.dumps(["灵根测试", "拜师"])
        chapter.characters_involved = json.dumps(["张三"])
        db_session.commit()

        # Mock LLM响应
        mock_response = {
            "content": """```json
{
  "scenes": [
    {
      "scene_number": 1,
      "location": "青云宗测试场",
      "characters": ["张三"],
      "time": "清晨",
      "description": "主角参加灵根测试",
      "key_dialogues": ["你的天赋不凡"],
      "plot_points": ["测试通过"],
      "foreshadowing": "未来的强大",
      "estimated_words": 1000
    }
  ],
  "chapter_goal": "展示主角天赋",
  "emotional_tone": "紧张期待",
  "cliffhanger": "测试结果震惊众人"
}
```""",
            "usage": {"input_tokens": 200, "output_tokens": 300},
            "cost": 0.03,
        }
        mock_llm_client.generate.return_value = mock_response

        generator = DetailOutlineGenerator(mock_llm_client)
        result = generator.generate_detail_outline(db_session, chapter.id)

        assert "detail_outline" in result
        assert len(result["detail_outline"]["scenes"]) == 1


class TestWorkflowOrchestrator:
    """测试流程编排器"""

    def test_get_workflow_status(self, db_session, test_novel, orchestrator):
        """测试获取工作流状态"""
        status = orchestrator.get_workflow_status(db_session, test_novel.id)

        assert status["novel_id"] == test_novel.id
        assert status["workflow_status"] == "created"
        assert status["current_step"] == 0

    def test_step_1_planning(self, db_session, test_novel, orchestrator, mock_llm_client):
        """测试步骤1：生成创作思路"""
        # Mock LLM响应
        mock_response = {
            "content": """```json
{
  "genre": "玄幻",
  "theme": "成长",
  "target_audience": "青年读者",
  "tone": "热血激昂",
  "core_conflict": "主角追求武学极致",
  "story_arc": "入门、修炼、历练、突破、巅峰",
  "estimated_length": {"volumes": 3, "chapters_per_volume": 10, "words_per_chapter": 3000},
  "key_features": ["天才主角"],
  "challenges": ["保持节奏"]
}
```""",
            "usage": {"input_tokens": 100, "output_tokens": 200},
            "cost": 0.01,
        }
        mock_llm_client.generate.return_value = mock_response

        result = orchestrator.step_1_planning(db_session, test_novel.id)

        assert result["novel_id"] == test_novel.id
        assert result["workflow_status"] == "planning"
        assert "planning" in result

        # 验证数据库已更新
        db_session.refresh(test_novel)
        assert test_novel.workflow_status == WorkflowStatus.PLANNING
        assert test_novel.current_step == 1
        assert test_novel.planning_content is not None

    def test_step_1_update(self, db_session, test_novel, orchestrator):
        """测试步骤1：更新创作思路"""
        planning_json = json.dumps({"genre": "玄幻", "theme": "复仇"}, ensure_ascii=False)

        result = orchestrator.step_1_update(db_session, test_novel.id, planning_json)

        assert result["novel_id"] == test_novel.id
        assert result["planning"]["genre"] == "玄幻"

        # 验证数据库已更新
        db_session.refresh(test_novel)
        assert test_novel.planning_content == planning_json


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
