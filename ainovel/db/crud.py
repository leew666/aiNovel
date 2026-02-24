"""
CRUD 操作基类和管理器

提供通用的 CRUD（增删改查）操作接口
"""
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ainovel.db.base import Base

# 泛型类型变量，用于表示任意模型类
ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """
    CRUD 操作基类

    提供通用的增删改查方法，可被任何模型复用
    """

    def __init__(self, model: Type[ModelType]):
        """
        初始化 CRUD 管理器

        Args:
            model: SQLAlchemy 模型类
        """
        self.model = model

    def create(self, session: Session, **kwargs) -> ModelType:
        """
        创建新记录

        Args:
            session: 数据库会话
            **kwargs: 模型字段值

        Returns:
            创建的模型实例
        """
        obj = self.model(**kwargs)
        session.add(obj)
        session.flush()  # 立即获取自增 ID
        return obj

    def get_by_id(self, session: Session, obj_id: int) -> Optional[ModelType]:
        """
        根据 ID 查询记录

        Args:
            session: 数据库会话
            obj_id: 记录 ID

        Returns:
            模型实例，如果不存在则返回 None
        """
        return session.get(self.model, obj_id)

    def get_all(
        self, session: Session, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        查询所有记录（支持分页）

        Args:
            session: 数据库会话
            skip: 跳过的记录数（偏移量）
            limit: 返回的最大记录数

        Returns:
            模型实例列表
        """
        stmt = select(self.model).offset(skip).limit(limit)
        return list(session.scalars(stmt).all())

    def count(self, session: Session) -> int:
        """
        统计记录总数

        Args:
            session: 数据库会话

        Returns:
            记录总数
        """
        stmt = select(func.count()).select_from(self.model)
        return session.scalar(stmt) or 0

    def update(self, session: Session, obj_id: int, **kwargs) -> Optional[ModelType]:
        """
        更新记录

        Args:
            session: 数据库会话
            obj_id: 记录 ID
            **kwargs: 要更新的字段值

        Returns:
            更新后的模型实例，如果不存在则返回 None
        """
        obj = self.get_by_id(session, obj_id)
        if obj is None:
            return None

        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        session.flush()
        return obj

    def delete(self, session: Session, obj_id: int) -> bool:
        """
        删除记录

        Args:
            session: 数据库会话
            obj_id: 记录 ID

        Returns:
            删除成功返回 True，记录不存在返回 False
        """
        obj = self.get_by_id(session, obj_id)
        if obj is None:
            return False

        session.delete(obj)
        session.flush()
        return True


# ===== 特定模型的 CRUD 管理器 =====

from ainovel.db.novel import Novel, NovelStatus
from ainovel.db.volume import Volume
from ainovel.db.chapter import Chapter
from ainovel.db.style_profile import StyleProfile


class NovelCRUD(CRUDBase[Novel]):
    """Novel 模型的 CRUD 管理器"""

    def get_by_title(self, session: Session, title: str) -> Optional[Novel]:
        """根据标题查询小说"""
        stmt = select(Novel).where(Novel.title == title)
        return session.scalar(stmt)

    def get_by_status(
        self, session: Session, status: NovelStatus, skip: int = 0, limit: int = 100
    ) -> List[Novel]:
        """根据状态查询小说"""
        stmt = select(Novel).where(Novel.status == status).offset(skip).limit(limit)
        return list(session.scalars(stmt).all())


class VolumeCRUD(CRUDBase[Volume]):
    """Volume 模型的 CRUD 管理器"""

    def get_by_novel_id(
        self, session: Session, novel_id: int, skip: int = 0, limit: int = 100
    ) -> List[Volume]:
        """根据小说 ID 查询所有分卷"""
        stmt = (
            select(Volume)
            .where(Volume.novel_id == novel_id)
            .order_by(Volume.order)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_by_order(self, session: Session, novel_id: int, order: int) -> Optional[Volume]:
        """根据小说 ID 和序号查询分卷"""
        stmt = select(Volume).where(Volume.novel_id == novel_id, Volume.order == order)
        return session.scalar(stmt)


class ChapterCRUD(CRUDBase[Chapter]):
    """Chapter 模型的 CRUD 管理器"""

    def get_by_volume_id(
        self, session: Session, volume_id: int, skip: int = 0, limit: int = 100
    ) -> List[Chapter]:
        """根据分卷 ID 查询所有章节"""
        stmt = (
            select(Chapter)
            .where(Chapter.volume_id == volume_id)
            .order_by(Chapter.order)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_by_order(self, session: Session, volume_id: int, order: int) -> Optional[Chapter]:
        """根据分卷 ID 和序号查询章节"""
        stmt = select(Chapter).where(Chapter.volume_id == volume_id, Chapter.order == order)
        return session.scalar(stmt)

    def search_by_content(
        self, session: Session, keyword: str, skip: int = 0, limit: int = 100
    ) -> List[Chapter]:
        """根据内容关键词搜索章节"""
        stmt = (
            select(Chapter)
            .where(Chapter.content.contains(keyword))
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())


class StyleProfileCRUD(CRUDBase[StyleProfile]):
    """StyleProfile 模型的 CRUD 管理器"""

    def get_by_novel_id(
        self, session: Session, novel_id: int, skip: int = 0, limit: int = 100
    ) -> List[StyleProfile]:
        """查询小说的所有文风档案"""
        stmt = (
            select(StyleProfile)
            .where(StyleProfile.novel_id == novel_id)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_active(self, session: Session, novel_id: int) -> Optional[StyleProfile]:
        """获取小说当前激活的文风档案"""
        stmt = select(StyleProfile).where(
            StyleProfile.novel_id == novel_id,
            StyleProfile.is_active == True,
        )
        return session.scalar(stmt)

    def set_active(self, session: Session, novel_id: int, profile_id: int) -> Optional[StyleProfile]:
        """将指定档案设为激活，同时停用同小说其他档案"""
        # 停用所有同小说档案
        all_profiles = self.get_by_novel_id(session, novel_id)
        for p in all_profiles:
            p.is_active = False
        # 激活目标档案
        target = self.get_by_id(session, profile_id)
        if target and target.novel_id == novel_id:
            target.is_active = True
            session.flush()
            return target
        return None


# ===== 全局 CRUD 实例 =====

novel_crud = NovelCRUD(Novel)
volume_crud = VolumeCRUD(Volume)
chapter_crud = ChapterCRUD(Chapter)
style_profile_crud = StyleProfileCRUD(StyleProfile)
