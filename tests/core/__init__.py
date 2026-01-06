"""
测试生成核心层功能
"""
import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from ainovel.core import PromptManager, OutlineGenerator, ChapterGenerator
from ainovel.llm import BaseLLMClient
from ainovel.db import init_database, get_database
from ainovel.db import novel_crud, volume_crud, chapter_crud
from ainovel.memory import CharacterDatabase, WorldDatabase, MBTIType, WorldDataType


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    db = init_database("sqlite:///:memory:")
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
        description="这是一个测试小说",
        author="测试作者",
    )
    return novel


@pytest.fixture
def test_characters(db_session, test_novel):
    """创建测试角色"""
    char_db = CharacterDatabase(db_session)

    char1 = char_db.create_character(
        novel_id=test_novel.id,
        name="张三",
        mbti=MBTIType.INTJ,
        background="天才剑客，追求武学极致",
        personality_traits={"勇气": 9, "智慧": 8},
    )

    char2 = char_db.create_character(
        novel_id=test_novel.id,
        name="李四",
        mbti=MBTIType.ENFP,
        background="乐观商人，善于交际",
        personality_traits={"魅力": 9, "财富": 7},
    )

    return [char1, char2]


@pytest.fixture
def test_world_data(db_session, test_novel):
    """创建测试世界观"""
    world_db = WorldDatabase(db_session)

    world1 = world_db.create_world_data(
        novel_id=test_novel.id,
        data_type=WorldDataType.SETTING,
        title="修仙世界",
        content="一个修仙者遍布的世界，境界分为：炼气、筑基、金丹、元婴",
    )

    world2 = world_db.create_world_data(
        novel_id=test_novel.id,
        data_type=WorldDataType.LOCATION,
        title="青云宗",
        content="主角所在的修仙宗门，位于青云山上",
    )

    return [world1, world2]


class TestPromptManager:
    """测试提示词管理器"""

    def test_format_world_info(self):
        """测试格式化世界观信息"""
        world_data_list = [
            {
                "data_type": "设定",
                "title": "修仙世界",
                "content": "这是一个修仙世界",
            },
            {
                "data_type": "地点",
                "title": "青云宗",
                "content": "主角的宗门",
            },
        ]

        result = PromptManager.format_world_info(world_data_list)

        assert "修仙世界" in result
        assert "青云宗" in result
        assert "设定" in result
        assert "地点" in result

    def test_format_character_info(self):
        """测试格式化角色信息"""
        character_list = [
            {
                "name": "张三",
                "mbti": "INTJ",
                "background": "天才剑客",
                "personality_traits": {"勇气": 9, "智慧": 8},
            }
        ]

        result = PromptManager.format_character_info(character_list)

        assert "张三" in result
        assert "INTJ" in result
        assert "天才剑客" in result
        assert "勇气: 9/10" in result

    def test_generate_outline_prompt(self):
        """测试生成大纲提示词"""
        prompt = PromptManager.generate_outline_prompt(
            title="测试小说",
            description="测试简介",
            author="测试作者",
            world_data_list=[],
            character_list=[],
        )

        assert "测试小说" in prompt
        assert "测试简介" in prompt
        assert "测试作者" in prompt
        assert "JSON" in prompt

    def test_generate_chapter_prompt(self):
        """测试生成章节提示词"""
        prompt = PromptManager.generate_chapter_prompt(
            title="测试小说",
            volume_title="第一卷",
            chapter_order=1,
            chapter_title="序章",
            chapter_summary="故事开始",
            key_events=["主角出场", "遇到导师"],
            character_list=[],
            world_data_list=[],
            previous_context="",
        )

        assert "测试小说" in prompt
        assert "第一卷" in prompt
        assert "序章" in prompt
        assert "故事开始" in prompt
        assert "主角出场" in prompt


class TestOutlineGenerator:
    """测试大纲生成器"""

    def test_generate_outline(
        self, db_session, mock_llm_client, test_novel, test_characters, test_world_data
    ):
        """测试生成大纲"""
        # Mock LLM响应
        mock_llm_client.generate.return_value = {
            "content": """```json
{
  "volumes": [
    {
      "title": "第一卷：入门",
      "description": "主角踏入修仙之路",
      "order": 1,
      "chapters": [
        {
          "title": "序章",
          "order": 1,
          "summary": "主角张三被青云宗选中",
          "key_events": ["拜师", "领取法器"],
          "characters_involved": ["张三"]
        }
      ]
    }
  ]
}
```""",
            "usage": {"input_tokens": 100, "output_tokens": 200, "total_tokens": 300},
            "cost": 0.01,
        }

        generator = OutlineGenerator(mock_llm_client, db_session)
        result = generator.generate_outline(test_novel.id)

        assert "outline" in result
        assert "usage" in result
        assert "cost" in result
        assert len(result["outline"]["volumes"]) == 1
        assert result["outline"]["volumes"][0]["title"] == "第一卷：入门"

    def test_save_outline(self, db_session, mock_llm_client, test_novel):
        """测试保存大纲"""
        outline_data = {
            "volumes": [
                {
                    "title": "第一卷",
                    "order": 1,
                    "description": "开篇",
                    "chapters": [
                        {
                            "title": "第一章",
                            "order": 1,
                            "summary": "开始",
                            "key_events": ["事件1"],
                        }
                    ],
                }
            ]
        }

        generator = OutlineGenerator(mock_llm_client, db_session)
        stats = generator.save_outline(test_novel.id, outline_data)

        assert stats["volumes_created"] == 1
        assert stats["chapters_created"] == 1

        # 验证数据库
        volumes = volume_crud.get_by_novel_id(db_session, test_novel.id)
        assert len(volumes) == 1
        assert volumes[0].title == "第一卷"

    def test_parse_outline_with_code_block(
        self, db_session, mock_llm_client, test_novel
    ):
        """测试解析带代码块的大纲"""
        generator = OutlineGenerator(mock_llm_client, db_session)

        content = """```json
{
  "volumes": [
    {
      "title": "测试卷",
      "order": 1,
      "chapters": []
    }
  ]
}
```"""

        outline = generator._parse_outline(content)
        assert "volumes" in outline
        assert outline["volumes"][0]["title"] == "测试卷"


class TestChapterGenerator:
    """测试章节生成器"""

    def test_generate_chapter(
        self, db_session, mock_llm_client, test_novel, test_characters, test_world_data
    ):
        """测试生成章节"""
        # 创建分卷和章节
        volume = volume_crud.create(
            db_session, novel_id=test_novel.id, title="第一卷", order=1
        )

        chapter = chapter_crud.create(
            db_session,
            volume_id=volume.id,
            title="第一章",
            order=1,
            content="# 章节梗概\n主角出场\n\n# 关键事件\n- 拜师",
        )

        # Mock LLM响应
        mock_llm_client.generate.return_value = {
            "content": "这是生成的章节内容，主角张三踏入了青云宗...",
            "usage": {"input_tokens": 200, "output_tokens": 500, "total_tokens": 700},
            "cost": 0.02,
        }

        generator = ChapterGenerator(mock_llm_client, db_session)
        result = generator.generate_chapter(chapter.id)

        assert "content" in result
        assert "usage" in result
        assert "cost" in result
        assert "张三" in result["content"]

    def test_save_chapter_content(self, db_session, mock_llm_client, test_novel):
        """测试保存章节内容"""
        volume = volume_crud.create(
            db_session, novel_id=test_novel.id, title="第一卷", order=1
        )

        chapter = chapter_crud.create(
            db_session, volume_id=volume.id, title="第一章", order=1, content=""
        )

        generator = ChapterGenerator(mock_llm_client, db_session)
        content = "这是测试章节内容" * 100

        stats = generator.save_chapter_content(chapter.id, content)

        assert stats["chapter_id"] == chapter.id
        assert stats["word_count"] > 0

        # 验证数据库
        updated_chapter = chapter_crud.get_by_id(db_session, chapter.id)
        assert updated_chapter.content == content
        assert updated_chapter.word_count > 0

    def test_parse_chapter_outline(self, db_session, mock_llm_client, test_novel):
        """测试解析章节大纲"""
        generator = ChapterGenerator(mock_llm_client, db_session)

        content = """# 章节梗概
主角张三被青云宗选中，开始修仙之路。

# 关键事件
- 拜师仪式
- 领取法器
- 初识同门
"""

        summary, events = generator._parse_chapter_outline(content)

        assert "张三" in summary
        assert "修仙" in summary
        assert len(events) == 3
        assert "拜师仪式" in events

    def test_generate_context_summary(self, db_session, mock_llm_client, test_novel):
        """测试生成前情摘要"""
        # Mock LLM响应
        mock_llm_client.generate.return_value = {
            "content": "张三拜入青云宗，开始修炼。",
            "usage": {"input_tokens": 50, "output_tokens": 20, "total_tokens": 70},
            "cost": 0.001,
        }

        generator = ChapterGenerator(mock_llm_client, db_session)
        content = "这是一段很长的章节内容..." * 100

        summary = generator.generate_context_summary(content)

        assert len(summary) > 0
        assert "张三" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
