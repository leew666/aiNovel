"""
记忆管理模块

提供角色数据库和世界观数据库的管理功能
"""
from ainovel.memory.character import Character, MBTIType
from ainovel.memory.world_data import WorldData, WorldDataType
from ainovel.memory.crud import CharacterCRUD, WorldDataCRUD, character_crud, world_data_crud
from ainovel.memory.character_db import CharacterDatabase
from ainovel.memory.world_db import WorldDatabase

__all__ = [
    # 模型
    "Character",
    "MBTIType",
    "WorldData",
    "WorldDataType",
    # CRUD
    "CharacterCRUD",
    "WorldDataCRUD",
    "character_crud",
    "world_data_crud",
    # 服务类
    "CharacterDatabase",
    "WorldDatabase",
]
