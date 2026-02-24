"""
测试章节改写器
"""
from unittest.mock import Mock

import pytest

from ainovel.core.chapter_rewriter import ChapterRewriter
from ainovel.db import init_database, novel_crud, volume_crud, chapter_crud
from ainovel.db.base import Base
from ainovel.llm import BaseLLMClient


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
        "content": "改写后的文本片段。",
        "usage": {"input_tokens": 60, "output_tokens": 40, "total_tokens": 100},
        "cost": 0.005,
        "model": "mock-model",
    }
    return client


def _create_chapter(session):
    novel = novel_crud.create(session, title="改写测试小说", description="desc", author="a")
    volume = volume_crud.create(session, novel_id=novel.id, title="卷一", order=1)
    chapter = chapter_crud.create(
        session,
        volume_id=volume.id,
        title="第一章",
        order=1,
        content="第一段原文。\n\n第二段原文。\n\n第三段原文。",
    )
    return chapter


def test_rewrite_paragraph_range(db_session, mock_llm):
    chapter = _create_chapter(db_session)
    rewriter = ChapterRewriter(mock_llm, db_session)

    result = rewriter.rewrite(
        chapter_id=chapter.id,
        instruction="加强冲突",
        target_scope="paragraph",
        range_start=2,
        range_end=2,
        save=False,
    )

    assert result["target_scope"] == "paragraph"
    assert result["range_start"] == 2
    assert "改写后的文本片段。" in result["new_content"]
    assert result["saved"] is False
    assert result["usage"]["total_tokens"] == 100


def test_rewrite_chapter_and_save(db_session, mock_llm):
    chapter = _create_chapter(db_session)
    rewriter = ChapterRewriter(mock_llm, db_session)

    result = rewriter.rewrite(
        chapter_id=chapter.id,
        instruction="整体润色",
        target_scope="chapter",
        rewrite_mode="polish",
        save=True,
    )

    assert result["target_scope"] == "chapter"
    assert result["saved"] is True

    updated = chapter_crud.get_by_id(db_session, chapter.id)
    assert updated.content == result["new_content"]
    assert result["history_id"]


def test_rollback_to_latest_history(db_session, mock_llm):
    chapter = _create_chapter(db_session)
    rewriter = ChapterRewriter(mock_llm, db_session)

    rewrite_result = rewriter.rewrite(
        chapter_id=chapter.id,
        instruction="整体润色",
        target_scope="chapter",
        save=True,
    )
    updated = chapter_crud.get_by_id(db_session, chapter.id)
    assert updated.content == rewrite_result["new_content"]

    rollback_result = rewriter.rollback(chapter_id=chapter.id, save=True)
    reverted = chapter_crud.get_by_id(db_session, chapter.id)
    assert rollback_result["history_id"] == rewrite_result["history_id"]
    assert reverted.content == rewrite_result["original_content"]
