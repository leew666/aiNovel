"""
记忆管理层 CRUD 操作

提供 Character 和 WorldData 的数据库操作接口
"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from ainovel.db.crud import CRUDBase
from ainovel.memory.character import Character, MBTIType
from ainovel.memory.world_data import WorldData, WorldDataType


class CharacterCRUD(CRUDBase[Character]):
    """Character 模型的 CRUD 管理器"""

    def get_by_name(self, session: Session, novel_id: int, name: str) -> Optional[Character]:
        """根据小说 ID 和角色名查询角色"""
        stmt = select(Character).where(Character.novel_id == novel_id, Character.name == name)
        return session.scalar(stmt)

    def get_by_novel_id(
        self, session: Session, novel_id: int, skip: int = 0, limit: int = 100
    ) -> List[Character]:
        """根据小说 ID 查询所有角色"""
        stmt = (
            select(Character)
            .where(Character.novel_id == novel_id)
            .order_by(Character.name)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_by_mbti(
        self, session: Session, novel_id: int, mbti: MBTIType, skip: int = 0, limit: int = 100
    ) -> List[Character]:
        """根据小说 ID 和 MBTI 类型查询角色"""
        stmt = (
            select(Character)
            .where(Character.novel_id == novel_id, Character.mbti == mbti)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def search_by_name(
        self, session: Session, novel_id: int, keyword: str, skip: int = 0, limit: int = 100
    ) -> List[Character]:
        """根据名称关键词搜索角色"""
        stmt = (
            select(Character)
            .where(Character.novel_id == novel_id, Character.name.contains(keyword))
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())


class WorldDataCRUD(CRUDBase[WorldData]):
    """WorldData 模型的 CRUD 管理器"""

    def get_by_novel_id(
        self, session: Session, novel_id: int, skip: int = 0, limit: int = 100
    ) -> List[WorldData]:
        """根据小说 ID 查询所有世界观数据"""
        stmt = (
            select(WorldData)
            .where(WorldData.novel_id == novel_id)
            .order_by(WorldData.data_type, WorldData.name)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_by_type(
        self,
        session: Session,
        novel_id: int,
        data_type: WorldDataType,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorldData]:
        """根据小说 ID 和数据类型查询世界观数据"""
        stmt = (
            select(WorldData)
            .where(WorldData.novel_id == novel_id, WorldData.data_type == data_type)
            .order_by(WorldData.name)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_by_name(
        self, session: Session, novel_id: int, name: str
    ) -> Optional[WorldData]:
        """根据小说 ID 和名称查询世界观数据"""
        stmt = select(WorldData).where(WorldData.novel_id == novel_id, WorldData.name == name)
        return session.scalar(stmt)

    def search_by_name(
        self, session: Session, novel_id: int, keyword: str, skip: int = 0, limit: int = 100
    ) -> List[WorldData]:
        """根据名称关键词搜索世界观数据"""
        stmt = (
            select(WorldData)
            .where(WorldData.novel_id == novel_id, WorldData.name.contains(keyword))
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())


# 全局 CRUD 实例
character_crud = CharacterCRUD(Character)
world_data_crud = WorldDataCRUD(WorldData)
