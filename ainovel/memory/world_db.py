"""
WorldDatabase 服务类

提供世界观数据管理的业务逻辑封装
"""
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ainovel.memory.world_data import WorldData, WorldDataType
from ainovel.memory.crud import world_data_crud


class WorldDatabase:
    """世界观数据库服务类"""

    def __init__(self, session: Session):
        """
        初始化世界观数据库

        Args:
            session: 数据库会话
        """
        self.session = session

    def create_location(
        self,
        novel_id: int,
        name: str,
        description: str,
        coordinates: str | None = None,
        climate: str | None = None,
        population: int | None = None,
        notable_features: str | None = None,
        **kwargs,
    ) -> WorldData:
        """
        创建地点数据

        Args:
            novel_id: 小说 ID
            name: 地点名称
            description: 描述
            coordinates: 坐标
            climate: 气候
            population: 人口
            notable_features: 显著特征
            **kwargs: 其他自定义属性

        Returns:
            创建的世界观数据实例
        """
        location = world_data_crud.create(
            self.session,
            novel_id=novel_id,
            data_type=WorldDataType.LOCATION,
            name=name,
            description=description,
            properties={},
        )
        location.set_location_properties(
            coordinates=coordinates,
            climate=climate,
            population=population,
            notable_features=notable_features,
            **kwargs,
        )
        self.session.flush()
        return location

    def create_organization(
        self,
        novel_id: int,
        name: str,
        description: str,
        leader: str | None = None,
        members_count: int | None = None,
        power_level: str | None = None,
        territory: str | None = None,
        **kwargs,
    ) -> WorldData:
        """
        创建组织数据

        Args:
            novel_id: 小说 ID
            name: 组织名称
            description: 描述
            leader: 领导者
            members_count: 成员数量
            power_level: 实力等级
            territory: 势力范围
            **kwargs: 其他自定义属性

        Returns:
            创建的世界观数据实例
        """
        organization = world_data_crud.create(
            self.session,
            novel_id=novel_id,
            data_type=WorldDataType.ORGANIZATION,
            name=name,
            description=description,
            properties={},
        )
        organization.set_organization_properties(
            leader=leader,
            members_count=members_count,
            power_level=power_level,
            territory=territory,
            **kwargs,
        )
        self.session.flush()
        return organization

    def create_item(
        self,
        novel_id: int,
        name: str,
        description: str,
        rarity: str | None = None,
        power_level: int | None = None,
        owner: str | None = None,
        abilities: str | None = None,
        **kwargs,
    ) -> WorldData:
        """
        创建物品数据

        Args:
            novel_id: 小说 ID
            name: 物品名称
            description: 描述
            rarity: 稀有度
            power_level: 威力等级
            owner: 当前所有者
            abilities: 能力描述
            **kwargs: 其他自定义属性

        Returns:
            创建的世界观数据实例
        """
        item = world_data_crud.create(
            self.session,
            novel_id=novel_id,
            data_type=WorldDataType.ITEM,
            name=name,
            description=description,
            properties={},
        )
        item.set_item_properties(
            rarity=rarity,
            power_level=power_level,
            owner=owner,
            abilities=abilities,
            **kwargs,
        )
        self.session.flush()
        return item

    def create_rule(
        self,
        novel_id: int,
        name: str,
        description: str,
        category: str | None = None,
        limitations: str | None = None,
        **kwargs,
    ) -> WorldData:
        """
        创建规则数据

        Args:
            novel_id: 小说 ID
            name: 规则名称
            description: 描述
            category: 分类
            limitations: 限制条件
            **kwargs: 其他自定义属性

        Returns:
            创建的世界观数据实例
        """
        rule = world_data_crud.create(
            self.session,
            novel_id=novel_id,
            data_type=WorldDataType.RULE,
            name=name,
            description=description,
            properties={},
        )
        rule.set_rule_properties(category=category, limitations=limitations, **kwargs)
        self.session.flush()
        return rule

    def get_world_data(self, world_data_id: int) -> Optional[WorldData]:
        """
        根据 ID 获取世界观数据

        Args:
            world_data_id: 世界观数据 ID

        Returns:
            世界观数据实例，不存在则返回 None
        """
        return world_data_crud.get_by_id(self.session, world_data_id)

    def get_world_data_by_name(self, novel_id: int, name: str) -> Optional[WorldData]:
        """
        根据名称获取世界观数据

        Args:
            novel_id: 小说 ID
            name: 数据名称

        Returns:
            世界观数据实例，不存在则返回 None
        """
        return world_data_crud.get_by_name(self.session, novel_id, name)

    def list_all(self, novel_id: int, skip: int = 0, limit: int = 100) -> List[WorldData]:
        """
        列出小说的所有世界观数据

        Args:
            novel_id: 小说 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            世界观数据列表
        """
        return world_data_crud.get_by_novel_id(self.session, novel_id, skip, limit)

    def get_world_cards(
        self,
        novel_id: int,
        keywords: List[str],
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        获取世界观卡片（按关键词相关性粗排）

        Args:
            novel_id: 小说 ID
            keywords: 关键词列表，通常来自关键事件或章节主题
            limit: 返回最大条数

        Returns:
            世界观卡片列表
        """
        all_data = self.list_all(novel_id, limit=200)
        if not all_data:
            return []

        normalized_keywords = [
            kw.strip().lower() for kw in keywords if kw and kw.strip()
        ]

        if not normalized_keywords:
            selected = all_data[:limit]
        else:
            scored = []
            for item in all_data:
                text = " ".join(
                    [
                        item.name or "",
                        item.description or "",
                        json.dumps(item.properties or {}, ensure_ascii=False),
                    ]
                ).lower()
                score = sum(1 for kw in normalized_keywords if kw in text)
                if score > 0:
                    scored.append((score, item))

            scored.sort(key=lambda pair: pair[0], reverse=True)
            selected = [item for _, item in scored[:limit]]

            if not selected:
                selected = all_data[:limit]

        return [
            {
                "name": item.name,
                "data_type": item.data_type.value,
                "description": item.description,
                "properties": item.properties or {},
            }
            for item in selected
        ]

    def list_by_type(
        self, novel_id: int, data_type: WorldDataType, skip: int = 0, limit: int = 100
    ) -> List[WorldData]:
        """
        列出指定类型的世界观数据

        Args:
            novel_id: 小说 ID
            data_type: 数据类型
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            世界观数据列表
        """
        return world_data_crud.get_by_type(self.session, novel_id, data_type, skip, limit)

    def list_locations(self, novel_id: int, skip: int = 0, limit: int = 100) -> List[WorldData]:
        """列出所有地点"""
        return self.list_by_type(novel_id, WorldDataType.LOCATION, skip, limit)

    def list_organizations(
        self, novel_id: int, skip: int = 0, limit: int = 100
    ) -> List[WorldData]:
        """列出所有组织"""
        return self.list_by_type(novel_id, WorldDataType.ORGANIZATION, skip, limit)

    def list_items(self, novel_id: int, skip: int = 0, limit: int = 100) -> List[WorldData]:
        """列出所有物品"""
        return self.list_by_type(novel_id, WorldDataType.ITEM, skip, limit)

    def list_rules(self, novel_id: int, skip: int = 0, limit: int = 100) -> List[WorldData]:
        """列出所有规则"""
        return self.list_by_type(novel_id, WorldDataType.RULE, skip, limit)

    def search(
        self, novel_id: int, keyword: str, skip: int = 0, limit: int = 100
    ) -> List[WorldData]:
        """
        搜索世界观数据

        Args:
            novel_id: 小说 ID
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            世界观数据列表
        """
        return world_data_crud.search_by_name(self.session, novel_id, keyword, skip, limit)

    def update_properties(self, world_data_id: int, **kwargs) -> WorldData:
        """
        更新世界观数据的属性

        Args:
            world_data_id: 世界观数据 ID
            **kwargs: 要更新的属性

        Returns:
            更新后的世界观数据实例

        Raises:
            ValueError: 如果世界观数据不存在
        """
        world_data = self.get_world_data(world_data_id)
        if world_data is None:
            raise ValueError(f"世界观数据 ID {world_data_id} 不存在")

        if world_data.properties is None:
            world_data.properties = {}

        world_data.properties.update(kwargs)
        self.session.flush()
        return world_data

    def delete_world_data(self, world_data_id: int) -> bool:
        """
        删除世界观数据

        Args:
            world_data_id: 世界观数据 ID

        Returns:
            删除成功返回 True，数据不存在返回 False
        """
        return world_data_crud.delete(self.session, world_data_id)
