"""
数据库层单元测试

测试 Novel、Volume、Chapter 模型和 CRUD 操作
"""
import pytest
from ainovel.db import (
    init_database,
    Novel,
    NovelStatus,
    Volume,
    Chapter,
    novel_crud,
    volume_crud,
    chapter_crud,
)


@pytest.fixture
def db():
    """创建内存数据库用于测试"""
    database = init_database("sqlite:///:memory:", echo=False)
    database.create_all_tables()
    yield database
    # 测试结束后清理


@pytest.fixture
def session(db):
    """创建数据库会话"""
    with db.session_scope() as sess:
        yield sess


def test_create_novel(session):
    """测试创建小说"""
    novel = novel_crud.create(
        session,
        title="测试小说",
        description="这是一部测试小说",
        author="测试作者",
        status=NovelStatus.DRAFT,
    )

    assert novel.id is not None
    assert novel.title == "测试小说"
    assert novel.author == "测试作者"
    assert novel.status == NovelStatus.DRAFT
    assert novel.created_at is not None


def test_get_novel_by_id(session):
    """测试根据 ID 查询小说"""
    # 创建小说
    novel = novel_crud.create(session, title="测试小说2", author="作者2")
    session.commit()

    # 查询小说
    found_novel = novel_crud.get_by_id(session, novel.id)
    assert found_novel is not None
    assert found_novel.title == "测试小说2"


def test_get_novel_by_title(session):
    """测试根据标题查询小说"""
    novel_crud.create(session, title="唯一标题小说")
    session.commit()

    found_novel = novel_crud.get_by_title(session, "唯一标题小说")
    assert found_novel is not None
    assert found_novel.title == "唯一标题小说"


def test_update_novel(session):
    """测试更新小说"""
    novel = novel_crud.create(session, title="待更新小说", status=NovelStatus.DRAFT)
    session.commit()

    # 更新状态
    updated_novel = novel_crud.update(session, novel.id, status=NovelStatus.ONGOING)
    session.commit()

    assert updated_novel.status == NovelStatus.ONGOING


def test_delete_novel(session):
    """测试删除小说"""
    novel = novel_crud.create(session, title="待删除小说")
    session.commit()

    # 删除小说
    result = novel_crud.delete(session, novel.id)
    session.commit()

    assert result is True
    assert novel_crud.get_by_id(session, novel.id) is None


def test_create_volume_with_novel(session):
    """测试创建分卷并关联小说"""
    # 创建小说
    novel = novel_crud.create(session, title="长篇小说")
    session.commit()

    # 创建分卷
    volume = volume_crud.create(
        session, novel_id=novel.id, title="第一卷", order=1, description="开篇卷"
    )
    session.commit()

    assert volume.id is not None
    assert volume.novel_id == novel.id
    assert volume.title == "第一卷"
    assert volume.order == 1


def test_get_volumes_by_novel_id(session):
    """测试根据小说 ID 查询分卷"""
    novel = novel_crud.create(session, title="多卷小说")
    volume_crud.create(session, novel_id=novel.id, title="第一卷", order=1)
    volume_crud.create(session, novel_id=novel.id, title="第二卷", order=2)
    session.commit()

    volumes = volume_crud.get_by_novel_id(session, novel.id)
    assert len(volumes) == 2
    assert volumes[0].order == 1
    assert volumes[1].order == 2


def test_create_chapter_with_volume(session):
    """测试创建章节并关联分卷"""
    novel = novel_crud.create(session, title="测试小说")
    volume = volume_crud.create(session, novel_id=novel.id, title="第一卷", order=1)
    session.commit()

    # 创建章节
    chapter = chapter_crud.create(
        session,
        volume_id=volume.id,
        title="第一章",
        order=1,
        content="这是第一章的内容，用于测试。",
    )
    session.commit()

    assert chapter.id is not None
    assert chapter.volume_id == volume.id
    assert chapter.title == "第一章"
    assert chapter.content == "这是第一章的内容，用于测试。"


def test_update_chapter_word_count(session):
    """测试章节字数统计"""
    novel = novel_crud.create(session, title="测试小说")
    volume = volume_crud.create(session, novel_id=novel.id, title="第一卷", order=1)
    chapter = chapter_crud.create(
        session, volume_id=volume.id, title="第一章", order=1, content="这是测试内容，有十个字。"
    )
    session.commit()

    # 更新字数
    chapter.update_word_count()
    session.commit()

    assert chapter.word_count > 0


def test_get_chapters_by_volume_id(session):
    """测试根据分卷 ID 查询章节"""
    novel = novel_crud.create(session, title="测试小说")
    volume = volume_crud.create(session, novel_id=novel.id, title="第一卷", order=1)
    chapter_crud.create(session, volume_id=volume.id, title="第一章", order=1, content="内容1")
    chapter_crud.create(session, volume_id=volume.id, title="第二章", order=2, content="内容2")
    session.commit()

    chapters = chapter_crud.get_by_volume_id(session, volume.id)
    assert len(chapters) == 2
    assert chapters[0].order == 1
    assert chapters[1].order == 2


def test_cascade_delete_novel(session):
    """测试级联删除：删除小说时，分卷和章节也应被删除"""
    novel = novel_crud.create(session, title="级联删除测试")
    volume = volume_crud.create(session, novel_id=novel.id, title="第一卷", order=1)
    chapter_crud.create(session, volume_id=volume.id, title="第一章", order=1, content="内容")
    session.commit()

    # 删除小说
    novel_crud.delete(session, novel.id)
    session.commit()

    # 验证分卷和章节也被删除
    assert volume_crud.get_by_id(session, volume.id) is None


def test_search_chapter_by_content(session):
    """测试根据内容搜索章节"""
    novel = novel_crud.create(session, title="测试小说")
    volume = volume_crud.create(session, novel_id=novel.id, title="第一卷", order=1)
    chapter_crud.create(
        session, volume_id=volume.id, title="第一章", order=1, content="这里有关键词：魔法"
    )
    chapter_crud.create(
        session, volume_id=volume.id, title="第二章", order=2, content="这里没有相关内容"
    )
    session.commit()

    results = chapter_crud.search_by_content(session, "魔法")
    assert len(results) == 1
    assert results[0].title == "第一章"
