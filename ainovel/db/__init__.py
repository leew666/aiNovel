"""
数据库模块

提供数据库连接、模型定义和 CRUD 操作
"""
from ainovel.db.database import Database, init_database, get_database
from ainovel.db.base import Base, TimestampMixin
from ainovel.db.novel import Novel, NovelStatus
from ainovel.db.volume import Volume
from ainovel.db.chapter import Chapter
from ainovel.db.style_profile import StyleProfile
from ainovel.db.crud import (
    CRUDBase,
    NovelCRUD,
    VolumeCRUD,
    ChapterCRUD,
    StyleProfileCRUD,
    novel_crud,
    volume_crud,
    chapter_crud,
    style_profile_crud,
)

__all__ = [
    # 数据库连接
    "Database",
    "init_database",
    "get_database",
    # 基础类
    "Base",
    "TimestampMixin",
    # 模型
    "Novel",
    "NovelStatus",
    "Volume",
    "Chapter",
    "StyleProfile",
    # CRUD
    "CRUDBase",
    "NovelCRUD",
    "VolumeCRUD",
    "ChapterCRUD",
    "StyleProfileCRUD",
    "novel_crud",
    "volume_crud",
    "chapter_crud",
    "style_profile_crud",
]
