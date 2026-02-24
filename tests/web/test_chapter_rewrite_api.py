"""
测试章节改写 API 路由
"""
import asyncio

import pytest
from fastapi import HTTPException

from ainovel.web.routers.workflow import rewrite_chapter, rollback_rewrite
from ainovel.web.schemas.workflow import ChapterRewriteRequest, ChapterRollbackRequest


class _DummyOrchestrator:
    def rewrite_chapter(self, **kwargs):
        return {
            "novel_id": 1,
            "chapter_id": kwargs["chapter_id"],
            "chapter_title": "第一章",
            "rewrite_mode": kwargs["rewrite_mode"],
            "target_scope": kwargs["target_scope"],
            "range_start": kwargs.get("range_start"),
            "range_end": kwargs.get("range_end"),
            "instruction": kwargs["instruction"],
            "preserve_plot": kwargs["preserve_plot"],
            "original_content": "原文",
            "new_content": "新文",
            "diff_summary": "相似度: 80%",
            "saved": kwargs["save"],
            "history_id": "20260101010101000000",
            "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
            "cost": 0.001,
            "model": "mock-model",
        }


class _FailOrchestrator:
    def rewrite_chapter(self, **kwargs):
        raise ValueError("章节不存在")

    def rollback_chapter_rewrite(self, **kwargs):
        raise ValueError("无历史版本")


class _RollbackOrchestrator:
    def rollback_chapter_rewrite(self, **kwargs):
        return {
            "novel_id": 1,
            "chapter_id": kwargs["chapter_id"],
            "chapter_title": "第一章",
            "history_id": kwargs.get("history_id") or "latest-id",
            "rolled_back_content": "旧版本正文",
            "saved": kwargs.get("save", True),
        }


def test_rewrite_api_success():
    req = ChapterRewriteRequest(
        instruction="加强冲突",
        target_scope="paragraph",
        range_start=1,
        range_end=2,
        preserve_plot=True,
        rewrite_mode="rewrite",
        save=False,
    )

    result = asyncio.run(
        rewrite_chapter(
            chapter_id=1,
            request_data=req,
            session=object(),
            orch=_DummyOrchestrator(),
        )
    )

    assert result.chapter_id == 1
    assert result.new_content == "新文"
    assert result.target_scope == "paragraph"


def test_rewrite_api_error_to_http_exception():
    req = ChapterRewriteRequest(instruction="测试")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            rewrite_chapter(
                chapter_id=999,
                request_data=req,
                session=object(),
                orch=_FailOrchestrator(),
            )
        )

    assert exc_info.value.status_code == 400


def test_rollback_api_success():
    req = ChapterRollbackRequest(history_id="abc", save=True)
    result = asyncio.run(
        rollback_rewrite(
            chapter_id=1,
            request_data=req,
            session=object(),
            orch=_RollbackOrchestrator(),
        )
    )
    assert result.chapter_id == 1
    assert result.rolled_back_content == "旧版本正文"


def test_rollback_api_error_to_http_exception():
    req = ChapterRollbackRequest()
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            rollback_rewrite(
                chapter_id=1,
                request_data=req,
                session=object(),
                orch=_FailOrchestrator(),
            )
        )
    assert exc_info.value.status_code == 400
