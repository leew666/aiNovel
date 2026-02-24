"""
测试上下文压缩器
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from ainovel.core.context_compressor import ContextCompressor, CompressionLevel, _get_compression_level
from ainovel.core.prompt_manager import PromptManager
from ainovel.llm import BaseLLMClient
from ainovel.db import init_database, novel_crud, volume_crud, chapter_crud
from ainovel.db.base import Base
from ainovel.memory import CharacterDatabase, WorldDatabase, MBTIType
from ainovel.db.novel import Novel
from ainovel.db.volume import Volume
from ainovel.db.chapter import Chapter


@pytest.fixture
def db_session():
    """内存数据库会话"""
    db = init_database("sqlite:///:memory:")
    Base.metadata.create_all(db.engine)
    with db.session_scope() as session:
        yield session


@pytest.fixture
def mock_llm():
    client = Mock(spec=BaseLLMClient)
    client.generate.return_value = {
        "content": "张三拜入青云宗，获得法器，初遇反派。",
        "usage": {"input_tokens": 50, "output_tokens": 20, "total_tokens": 70},
        "cost": 0.001,
    }
    return client


@pytest.fixture
def setup_chapters(db_session):
    """创建测试小说、分卷和多个章节"""
    novel = novel_crud.create(db_session, title="测试小说", description="测试", author="作者")
    volume = volume_crud.create(db_session, novel_id=novel.id, title="第一卷", order=1)

    chapters = []
    for i in range(1, 6):
        ch = chapter_crud.create(
            db_session,
            volume_id=volume.id,
            title=f"第{i}章",
            order=i,
            content=f"这是第{i}章的正文内容。" * 50,  # ~200字
        )
        chapters.append(ch)

    return volume, chapters


class TestCompressionLevel:
    """测试压缩级别选择逻辑"""

    def test_near_chapter_is_detailed(self):
        assert _get_compression_level(1) == CompressionLevel.DETAILED
        assert _get_compression_level(3) == CompressionLevel.DETAILED

    def test_mid_chapter_is_brief(self):
        assert _get_compression_level(4) == CompressionLevel.BRIEF
        assert _get_compression_level(10) == CompressionLevel.BRIEF

    def test_far_chapter_is_minimal(self):
        assert _get_compression_level(11) == CompressionLevel.MINIMAL
        assert _get_compression_level(50) == CompressionLevel.MINIMAL


class TestContextCompressor:
    """测试 ContextCompressor 核心功能"""

    def test_build_previous_context_first_chapter(self, mock_llm, db_session, setup_chapters):
        """第一章无前情"""
        volume, _ = setup_chapters
        compressor = ContextCompressor(mock_llm, db_session)
        result = compressor.build_previous_context(volume.id, current_order=1)
        assert result == "本章为开篇，无前情"
        mock_llm.generate.assert_not_called()

    def test_build_previous_context_uses_llm(self, mock_llm, db_session, setup_chapters):
        """有前章时调用 LLM 压缩"""
        volume, _ = setup_chapters
        compressor = ContextCompressor(mock_llm, db_session)
        result = compressor.build_previous_context(volume.id, current_order=3, window_size=5)

        assert "第1章" in result
        assert "第2章" in result
        assert mock_llm.generate.call_count >= 1

    def test_build_previous_context_respects_window_size(self, mock_llm, db_session, setup_chapters):
        """window_size 限制回溯章节数"""
        volume, _ = setup_chapters
        compressor = ContextCompressor(mock_llm, db_session)
        result = compressor.build_previous_context(volume.id, current_order=5, window_size=2)

        # 只应包含第3、4章，不含第1、2章
        assert "第3章" in result
        assert "第4章" in result
        assert "第1章" not in result
        assert "第2章" not in result

    def test_compress_and_cache_writes_summary(self, mock_llm, db_session, setup_chapters):
        """compress_and_cache 将摘要写入 chapter.summary"""
        _, chapters = setup_chapters
        chapter = chapters[0]
        assert chapter.summary is None

        compressor = ContextCompressor(mock_llm, db_session)
        summary = compressor.compress_and_cache(chapter.id)

        assert len(summary) > 0
        updated = chapter_crud.get_by_id(db_session, chapter.id)
        assert updated.summary == summary

    def test_compress_and_cache_uses_existing_summary(self, mock_llm, db_session, setup_chapters):
        """已有 summary 时不再调用 LLM"""
        _, chapters = setup_chapters
        chapter = chapters[0]
        chapter_crud.update(db_session, chapter.id, summary="已有摘要内容")

        compressor = ContextCompressor(mock_llm, db_session)
        result = compressor.compress_and_cache(chapter.id)

        assert result == "已有摘要内容"
        mock_llm.generate.assert_not_called()

    def test_compress_single_short_content_no_llm(self, mock_llm, db_session):
        """内容短于目标字数时不调用 LLM"""
        compressor = ContextCompressor(mock_llm, db_session)
        short_content = "短内容"
        result = compressor._compress_single(short_content, CompressionLevel.DETAILED)

        assert result == short_content
        mock_llm.generate.assert_not_called()

    def test_compress_single_llm_failure_fallback(self, db_session):
        """LLM 失败时降级截取"""
        failing_llm = Mock(spec=BaseLLMClient)
        failing_llm.generate.side_effect = Exception("API 超时")

        compressor = ContextCompressor(failing_llm, db_session)
        long_content = "这是很长的章节内容。" * 100

        result = compressor._compress_single(long_content, CompressionLevel.DETAILED)
        assert len(result) <= 210  # 200字 + "…"
        assert result.endswith("…")

    def test_token_budget_limits_context(self, mock_llm, db_session, setup_chapters):
        """token_budget 极小时只保留少量章节"""
        volume, _ = setup_chapters
        compressor = ContextCompressor(mock_llm, db_session)

        # 极小预算，只能容纳约 1 章
        result = compressor.build_previous_context(
            volume.id, current_order=5, window_size=10, token_budget=80
        )
        # 结果不为空但内容受限
        assert result != "本章为开篇，无前情"
        assert len(result) <= 200

    def test_build_context_bundle_includes_memory_cards(self, mock_llm, db_session, setup_chapters):
        """上下文包应包含前情、角色记忆卡和世界观卡片"""
        volume, _ = setup_chapters
        novel_id = volume.novel_id

        char_db = CharacterDatabase(db_session)
        world_db = WorldDatabase(db_session)

        char = char_db.create_character(
            novel_id=novel_id,
            name="张三",
            mbti=MBTIType.INTJ,
            background="少年天才",
        )
        char_db.add_memory(
            character_id=char.id,
            event="拜师",
            content="张三在青云宗拜师成功",
            importance="high",
        )
        world_db.create_location(
            novel_id=novel_id,
            name="青云宗",
            description="名门正派",
        )

        compressor = ContextCompressor(mock_llm, db_session)
        bundle = compressor.build_context_bundle(
            volume_id=volume.id,
            current_order=5,
            novel_id=novel_id,
            character_names=["张三"],
            world_keywords=["青云宗"],
        )

        assert "previous_context" in bundle
        assert "character_memory_cards" in bundle
        assert "world_memory_cards" in bundle
        assert bundle["character_memory_cards"][0]["name"] == "张三"
        assert bundle["world_memory_cards"][0]["name"] == "青云宗"


class TestPromptManagerCompression:
    """测试 PromptManager 分层压缩提示词"""

    def test_generate_compression_prompt_detailed(self):
        prompt = PromptManager.generate_compression_prompt("内容", "detailed", 200)
        assert "200" in prompt
        assert "详细摘要" in prompt

    def test_generate_compression_prompt_brief(self):
        prompt = PromptManager.generate_compression_prompt("内容", "brief", 100)
        assert "100" in prompt
        assert "简要摘要" in prompt

    def test_generate_compression_prompt_minimal(self):
        prompt = PromptManager.generate_compression_prompt("内容", "minimal", 50)
        assert "50" in prompt
        assert "关键事件" in prompt

    def test_generate_compression_prompt_unknown_level_fallback(self):
        """未知级别降级到 brief"""
        prompt = PromptManager.generate_compression_prompt("内容", "unknown", 100)
        assert len(prompt) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
