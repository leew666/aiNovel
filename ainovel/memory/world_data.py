"""
WorldData（世界观数据）模型

管理小说的世界观设定，包括地点、组织、物品、规则等
"""
from enum import Enum
from typing import Dict, Any
from sqlalchemy import String, Text, Integer, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ainovel.db.base import Base, TimestampMixin


class WorldDataType(str, Enum):
    """世界观数据类型枚举"""

    LOCATION = "location"  # 地点：城市、山脉、秘境等
    ORGANIZATION = "organization"  # 组织：门派、势力、阵营等
    ITEM = "item"  # 物品：法宝、装备、关键道具等
    RULE = "rule"  # 规则：物理规则、魔法系统、社会结构等


class WorldData(Base, TimestampMixin):
    """世界观数据模型"""

    __tablename__ = "world_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    novel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属小说ID",
    )
    data_type: Mapped[WorldDataType] = mapped_column(
        SQLEnum(WorldDataType), nullable=False, index=True, comment="数据类型"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="名称"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="描述")

    # JSON 字段：根据 data_type 存储不同的属性
    properties: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False, comment="属性（灵活存储）"
    )

    # 关系：多对一，多条世界观数据属于一部小说
    novel: Mapped["Novel"] = relationship("Novel")

    def __repr__(self) -> str:
        return f"WorldData(id={self.id}, name={self.name!r}, type={self.data_type.value}, novel_id={self.novel_id})"

    def set_location_properties(
        self,
        coordinates: str | None = None,
        climate: str | None = None,
        population: int | None = None,
        notable_features: str | None = None,
        **kwargs,
    ) -> None:
        """
        设置地点属性

        Args:
            coordinates: 坐标（如：东经120°，北纬30°）
            climate: 气候
            population: 人口
            notable_features: 显著特征
            **kwargs: 其他自定义属性
        """
        if self.data_type != WorldDataType.LOCATION:
            raise ValueError(f"数据类型必须是 LOCATION，当前是 {self.data_type.value}")

        if self.properties is None:
            self.properties = {}

        if coordinates:
            self.properties["coordinates"] = coordinates
        if climate:
            self.properties["climate"] = climate
        if population is not None:
            self.properties["population"] = population
        if notable_features:
            self.properties["notable_features"] = notable_features

        # 添加其他自定义属性
        self.properties.update(kwargs)

    def set_organization_properties(
        self,
        leader: str | None = None,
        members_count: int | None = None,
        power_level: str | None = None,
        territory: str | None = None,
        **kwargs,
    ) -> None:
        """
        设置组织属性

        Args:
            leader: 领导者
            members_count: 成员数量
            power_level: 实力等级（如：一流、二流、三流）
            territory: 势力范围
            **kwargs: 其他自定义属性
        """
        if self.data_type != WorldDataType.ORGANIZATION:
            raise ValueError(f"数据类型必须是 ORGANIZATION，当前是 {self.data_type.value}")

        if self.properties is None:
            self.properties = {}

        if leader:
            self.properties["leader"] = leader
        if members_count is not None:
            self.properties["members_count"] = members_count
        if power_level:
            self.properties["power_level"] = power_level
        if territory:
            self.properties["territory"] = territory

        self.properties.update(kwargs)

    def set_item_properties(
        self,
        rarity: str | None = None,
        power_level: int | None = None,
        owner: str | None = None,
        abilities: str | None = None,
        **kwargs,
    ) -> None:
        """
        设置物品属性

        Args:
            rarity: 稀有度（如：普通、稀有、传说）
            power_level: 威力等级（1-10）
            owner: 当前所有者
            abilities: 能力描述
            **kwargs: 其他自定义属性
        """
        if self.data_type != WorldDataType.ITEM:
            raise ValueError(f"数据类型必须是 ITEM，当前是 {self.data_type.value}")

        if self.properties is None:
            self.properties = {}

        if rarity:
            self.properties["rarity"] = rarity
        if power_level is not None:
            self.properties["power_level"] = min(max(power_level, 1), 10)
        if owner:
            self.properties["owner"] = owner
        if abilities:
            self.properties["abilities"] = abilities

        self.properties.update(kwargs)

    def set_rule_properties(
        self,
        category: str | None = None,
        limitations: str | None = None,
        **kwargs,
    ) -> None:
        """
        设置规则属性

        Args:
            category: 分类（如：物理规则、魔法系统、社会制度）
            limitations: 限制条件
            **kwargs: 其他自定义属性
        """
        if self.data_type != WorldDataType.RULE:
            raise ValueError(f"数据类型必须是 RULE，当前是 {self.data_type.value}")

        if self.properties is None:
            self.properties = {}

        if category:
            self.properties["category"] = category
        if limitations:
            self.properties["limitations"] = limitations

        self.properties.update(kwargs)
