"""
测试流水线运行器
"""
import pytest
from unittest.mock import MagicMock, patch

from ainovel.db import init_database
from ainovel.db import novel_crud, volume_crud, chapter_crud
from ainovel.db.novel import WorkflowStatus
from ainovel.workflow.pipeline_runner import PipelineRunner, parse_chapter_range


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    """内存数据库会话"""
    db = init_database("sqlite:///:memory:")
    from ainovel.db.base import Base
    from ainovel.db.novel import Novel
    from ainovel.db.volume import Volume
    from ainovel.db.chapter import Chapter
    from ainovel.memory.character import Character
    from ainovel.memory.world_data import WorldData
    from ainovel.db.style_profile import StyleProfile

    Base.metadata.create_all(db.engine)
    with db.session_scope() as session:
        yield session


@pytest.fixture
def novel_with_chapters(db_session):
    """创建含2卷各3章的测试小说"""
    novel = novel_crud.create(
        db_session,
        title="流水线测试小说",
        description="测试用",
        author="测试",
    )
    novel.workflow_status = WorkflowStatus.WORLD_BUILDING
    novel.current_step = 2

    for vol_order in range(1, 3):
        volume = volume_crud.create(
            db_session,
            novel_id=novel.id,
            title=f"第{vol_order}卷",
            order=vol_order,
        )
        for ch_order in range(1, 4):
            chapter_crud.create(
                db_session,
                volume_id=volume.id,
                title=f"第{vol_order}卷第{ch_order}章",
                order=ch_order,
                content="",
            )

    db_session.commit()
    db_session.refresh(novel)
    return novel


def _make_orchestrator(step4_fail_ids=None, step5_fail_ids=None):
    """构造带可控失败的 Mock orchestrator"""
    orch = MagicMock()

    def fake_step3(session, novel_id):
        return {"stats": {}, "novel_id": novel_id, "workflow_status": "outline"}

    def fake_step4(session, chapter_id):
        if step4_fail_ids and chapter_id in step4_fail_ids:
            raise RuntimeError(f"step4 mock failure for chapter {chapter_id}")
        return {"stats": {"scenes_count": 3}, "chapter_id": chapter_id}

    def fake_step5(session, chapter_id):
        if step5_fail_ids and chapter_id in step5_fail_ids:
            raise RuntimeError(f"step5 mock failure for chapter {chapter_id}")
        return {"word_count": 2000, "stats": {}, "chapter_id": chapter_id}

    orch.step_3_outline.side_effect = fake_step3
    orch.step_4_detail_outline.side_effect = fake_step4
    orch.step_5_writing.side_effect = fake_step5
    return orch


# ---------------------------------------------------------------------------
# parse_chapter_range 单元测试
# ---------------------------------------------------------------------------


class TestParseChapterRange:
    def test_none_returns_all(self):
        assert parse_chapter_range(None, 5) == [1, 2, 3, 4, 5]

    def test_empty_string_returns_all(self):
        assert parse_chapter_range("", 5) == [1, 2, 3, 4, 5]

    def test_single_index(self):
        assert parse_chapter_range("3", 5) == [3]

    def test_range(self):
        assert parse_chapter_range("2-4", 5) == [2, 3, 4]

    def test_comma_list(self):
        assert parse_chapter_range("1,3,5", 5) == [1, 3, 5]

    def test_mixed(self):
        assert parse_chapter_range("1-2,5", 6) == [1, 2, 5]

    def test_out_of_bounds_filtered(self):
        # 超出总数的索引被过滤
        assert parse_chapter_range("1-10", 3) == [1, 2, 3]

    def test_dedup(self):
        assert parse_chapter_range("1,1,2", 5) == [1, 2]

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            parse_chapter_range("abc", 5)

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError):
            parse_chapter_range("5-2", 10)


# ---------------------------------------------------------------------------
# PipelineRunner 集成测试
# ---------------------------------------------------------------------------


class TestPipelineRunner:
    def test_validate_plan_invalid_from_step(self):
        runner = PipelineRunner(MagicMock())
        with pytest.raises(ValueError, match="from_step"):
            runner.run(MagicMock(), 1, {"from_step": 2, "to_step": 5})

    def test_validate_plan_from_greater_than_to(self):
        runner = PipelineRunner(MagicMock())
        with pytest.raises(ValueError, match="from_step"):
            runner.run(MagicMock(), 1, {"from_step": 5, "to_step": 3})

    def test_novel_not_found_raises(self, db_session):
        runner = PipelineRunner(MagicMock())
        from ainovel.exceptions import NovelNotFoundError
        with pytest.raises(NovelNotFoundError):
            runner.run(db_session, 9999, {"from_step": 4, "to_step": 5})

    def test_step4_and_step5_all_success(self, db_session, novel_with_chapters):
        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        result = runner.run(
            db_session,
            novel_with_chapters.id,
            {"from_step": 4, "to_step": 5},
        )

        assert result["failed"] == 0
        assert result["succeeded"] == 12  # 6章 × 2步
        assert result["total"] == 6

    def test_step4_failure_skips_step5(self, db_session, novel_with_chapters):
        """步骤4失败的章节，步骤5应被跳过"""
        all_chapters = []
        for vol in sorted(novel_with_chapters.volumes, key=lambda v: v.order):
            all_chapters.extend(sorted(vol.chapters, key=lambda c: c.order))

        fail_id = all_chapters[0].id
        orch = _make_orchestrator(step4_fail_ids={fail_id})
        runner = PipelineRunner(orch)

        result = runner.run(
            db_session,
            novel_with_chapters.id,
            {"from_step": 4, "to_step": 5},
        )

        assert result["failed"] == 1
        assert result["skipped"] == 1
        assert fail_id in result["failed_chapter_ids"]

    def test_chapter_range_limits_scope(self, db_session, novel_with_chapters):
        """章节范围限制只处理指定章节"""
        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        result = runner.run(
            db_session,
            novel_with_chapters.id,
            {"from_step": 5, "to_step": 5, "chapter_range": "1-2"},
        )

        assert result["total"] == 2
        assert result["succeeded"] == 2

    def test_idempotent_skip_when_already_done(self, db_session, novel_with_chapters):
        """已有细纲/正文时，不传 regenerate 应跳过"""
        # 给第一章预填内容
        all_chapters = []
        for vol in sorted(novel_with_chapters.volumes, key=lambda v: v.order):
            all_chapters.extend(sorted(vol.chapters, key=lambda c: c.order))

        first = all_chapters[0]
        first.detail_outline = '{"scenes": []}'
        first.content = "已有正文内容"
        db_session.commit()

        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        result = runner.run(
            db_session,
            novel_with_chapters.id,
            {"from_step": 4, "to_step": 5, "chapter_range": "1"},
        )

        # 两步都跳过，不调用 orchestrator
        orch.step_4_detail_outline.assert_not_called()
        orch.step_5_writing.assert_not_called()
        assert result["succeeded"] == 2  # 跳过也算成功

    def test_regenerate_forces_rerun(self, db_session, novel_with_chapters):
        """regenerate=True 时即使已有内容也重新生成"""
        all_chapters = []
        for vol in sorted(novel_with_chapters.volumes, key=lambda v: v.order):
            all_chapters.extend(sorted(vol.chapters, key=lambda c: c.order))

        first = all_chapters[0]
        first.detail_outline = '{"scenes": []}'
        first.content = "已有正文内容"
        db_session.commit()

        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        runner.run(
            db_session,
            novel_with_chapters.id,
            {"from_step": 4, "to_step": 5, "chapter_range": "1", "regenerate": True},
        )

        orch.step_4_detail_outline.assert_called_once()
        orch.step_5_writing.assert_called_once()

    def test_step5_only(self, db_session, novel_with_chapters):
        """仅执行步骤5，不触发步骤4"""
        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        result = runner.run(
            db_session,
            novel_with_chapters.id,
            {"from_step": 5, "to_step": 5},
        )

        orch.step_4_detail_outline.assert_not_called()
        assert result["total"] == 6


# ---------------------------------------------------------------------------
# 并行执行测试
# ---------------------------------------------------------------------------


class TestPipelineRunnerParallel:
    """验证 max_workers > 1 时并行路径的正确性"""

    @pytest.fixture
    def parallel_db(self):
        """为并行测试提供独立的内存数据库（需注册为全局实例）"""
        from ainovel.db import init_database
        from ainovel.db.base import Base
        from ainovel.db.novel import Novel
        from ainovel.db.volume import Volume
        from ainovel.db.chapter import Chapter
        from ainovel.memory.character import Character
        from ainovel.memory.world_data import WorldData
        from ainovel.db.style_profile import StyleProfile

        db = init_database("sqlite:///:memory:")
        Base.metadata.create_all(db.engine)
        return db

    @pytest.fixture
    def parallel_novel(self, parallel_db):
        """在并行数据库中创建测试小说"""
        with parallel_db.session_scope() as session:
            novel = novel_crud.create(
                session,
                title="并行测试小说",
                description="测试用",
                author="测试",
            )
            novel.workflow_status = WorkflowStatus.WORLD_BUILDING
            novel.current_step = 2

            for vol_order in range(1, 3):
                volume = volume_crud.create(
                    session,
                    novel_id=novel.id,
                    title=f"第{vol_order}卷",
                    order=vol_order,
                )
                for ch_order in range(1, 4):
                    chapter_crud.create(
                        session,
                        volume_id=volume.id,
                        title=f"第{vol_order}卷第{ch_order}章",
                        order=ch_order,
                        content="",
                    )
            session.commit()
            novel_id = novel.id

        return novel_id, parallel_db

    def test_parallel_step4_and_step5_all_success(self, parallel_novel):
        """并行模式下步骤4+5全部成功"""
        novel_id, db = parallel_novel
        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        with db.session_scope() as session:
            with patch("ainovel.workflow.pipeline_runner.get_database", return_value=db):
                result = runner.run(
                    session,
                    novel_id,
                    {"from_step": 4, "to_step": 5, "max_workers": 3},
                )

        assert result["failed"] == 0
        assert result["succeeded"] == 12  # 6章 × 2步
        assert result["total"] == 6

    def test_parallel_step4_failure_skips_step5(self, parallel_novel):
        """并行模式下步骤4失败的章节，步骤5应被跳过"""
        novel_id, db = parallel_novel

        with db.session_scope() as session:
            novel = novel_crud.get_by_id(session, novel_id)
            all_chapters = []
            for vol in sorted(novel.volumes, key=lambda v: v.order):
                all_chapters.extend(sorted(vol.chapters, key=lambda c: c.order))
            fail_id = all_chapters[0].id

        orch = _make_orchestrator(step4_fail_ids={fail_id})
        runner = PipelineRunner(orch)

        with db.session_scope() as session:
            with patch("ainovel.workflow.pipeline_runner.get_database", return_value=db):
                result = runner.run(
                    session,
                    novel_id,
                    {"from_step": 4, "to_step": 5, "max_workers": 3},
                )

        assert result["failed"] == 1
        assert result["skipped"] == 1
        assert fail_id in result["failed_chapter_ids"]

    def test_parallel_step5_only(self, parallel_novel):
        """并行模式下仅执行步骤5"""
        novel_id, db = parallel_novel
        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        with db.session_scope() as session:
            with patch("ainovel.workflow.pipeline_runner.get_database", return_value=db):
                result = runner.run(
                    session,
                    novel_id,
                    {"from_step": 5, "to_step": 5, "max_workers": 2},
                )

        orch.step_4_detail_outline.assert_not_called()
        assert result["total"] == 6
        assert result["failed"] == 0

    def test_max_workers_1_uses_serial_path(self, db_session, novel_with_chapters):
        """max_workers=1 时走串行路径，行为与默认一致"""
        orch = _make_orchestrator()
        runner = PipelineRunner(orch)

        result = runner.run(
            db_session,
            novel_with_chapters.id,
            {"from_step": 4, "to_step": 5, "max_workers": 1},
        )

        assert result["failed"] == 0
        assert result["succeeded"] == 12
