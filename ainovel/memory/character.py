"""
Character（角色）模型

管理小说中的角色信息、MBTI 人格、记忆和关系网络
"""
from enum import Enum
from typing import Dict, List, Any
from sqlalchemy import String, Text, Integer, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ainovel.db.base import Base, TimestampMixin


class MBTIType(str, Enum):
    """MBTI 人格类型枚举（16 种）"""

    # 分析家（NT）
    INTJ = "INTJ"  # 建筑师：独立、战略性思考
    INTP = "INTP"  # 逻辑学家：创新、逻辑性强
    ENTJ = "ENTJ"  # 指挥官：果断、领导力强
    ENTP = "ENTP"  # 辩论家：聪明、好奇

    # 外交家（NF）
    INFJ = "INFJ"  # 提倡者：理想主义、有洞察力
    INFP = "INFP"  # 调停者：忠诚、富有想象力
    ENFJ = "ENFJ"  # 主人公：魅力、激励他人
    ENFP = "ENFP"  # 竞选者：热情、创造力强

    # 守护者（SJ）
    ISTJ = "ISTJ"  # 物流师：可靠、实际
    ISFJ = "ISFJ"  # 守卫者：温暖、负责
    ESTJ = "ESTJ"  # 总经理：组织能力强、传统
    ESFJ = "ESFJ"  # 执政官：关心他人、社交能力强

    # 探险家（SP）
    ISTP = "ISTP"  # 鉴赏家：大胆、实践性强
    ISFP = "ISFP"  # 探险家：灵活、有艺术天赋
    ESTP = "ESTP"  # 企业家：精力充沛、直接
    ESFP = "ESFP"  # 表演者：自发、热情


class Character(Base, TimestampMixin):
    """角色模型"""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    novel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属小说ID",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="角色姓名"
    )
    mbti: Mapped[MBTIType] = mapped_column(
        SQLEnum(MBTIType), nullable=False, index=True, comment="MBTI 人格类型"
    )
    background: Mapped[str] = mapped_column(Text, nullable=False, comment="背景故事")

    # JSON 字段：灵活存储复杂数据
    personality_traits: Mapped[Dict[str, int]] = mapped_column(
        JSON, default=dict, nullable=False, comment="性格特征（属性名: 值1-10）"
    )
    memories: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False, comment="角色记忆列表"
    )
    relationships: Mapped[Dict[str, Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=False, comment="关系网络（角色名: 关系信息）"
    )

    # 关系：多对一，多个角色属于一部小说
    novel: Mapped["Novel"] = relationship("Novel")

    def __repr__(self) -> str:
        return f"Character(id={self.id}, name={self.name!r}, mbti={self.mbti.value}, novel_id={self.novel_id})"

    def add_memory(
        self,
        event: str,
        content: str,
        chapter_id: int | None = None,
        volume_id: int | None = None,
        importance: str = "medium",
    ) -> None:
        """
        添加角色记忆

        Args:
            event: 事件名称
            content: 记忆内容
            chapter_id: 发生在哪一章（可选）
            volume_id: 发生在哪一卷（可选）
            importance: 重要性（high/medium/low）
        """
        from datetime import datetime

        memory = {
            "event": event,
            "content": content,
            "chapter_id": chapter_id,
            "volume_id": volume_id,
            "importance": importance,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if self.memories is None:
            self.memories = []
        self.memories.append(memory)

    def add_relationship(
        self,
        character_name: str,
        relation_type: str,
        intimacy: int = 5,
        first_met_chapter: int | None = None,
        notes: str = "",
    ) -> None:
        """
        添加角色关系

        Args:
            character_name: 关联角色名称
            relation_type: 关系类型（如：师徒、朋友、敌人）
            intimacy: 亲密度（1-10）
            first_met_chapter: 初次相遇的章节
            notes: 备注
        """
        if self.relationships is None:
            self.relationships = {}

        self.relationships[character_name] = {
            "relation_type": relation_type,
            "intimacy": min(max(intimacy, 1), 10),  # 限制在 1-10
            "first_met_chapter": first_met_chapter,
            "notes": notes,
        }

    def update_personality_trait(self, trait_name: str, value: int) -> None:
        """
        更新性格特征

        Args:
            trait_name: 特征名称（如：勇敢、智慧）
            value: 特征值（1-10）
        """
        if self.personality_traits is None:
            self.personality_traits = {}

        self.personality_traits[trait_name] = min(max(value, 1), 10)

    def get_mbti_description(self) -> str:
        """获取 MBTI 人格描述"""
        descriptions = {
            MBTIType.INTJ: "建筑师：独立、战略性思考、目标明确",
            MBTIType.INTP: "逻辑学家：创新、逻辑性强、好奇心重",
            MBTIType.ENTJ: "指挥官：果断、领导力强、组织能力强",
            MBTIType.ENTP: "辩论家：聪明、好奇、喜欢挑战",
            MBTIType.INFJ: "提倡者：理想主义、有洞察力、同理心强",
            MBTIType.INFP: "调停者：忠诚、富有想象力、价值观强",
            MBTIType.ENFJ: "主人公：魅力、激励他人、善于沟通",
            MBTIType.ENFP: "竞选者：热情、创造力强、社交能力强",
            MBTIType.ISTJ: "物流师：可靠、实际、注重细节",
            MBTIType.ISFJ: "守卫者：温暖、负责、保护他人",
            MBTIType.ESTJ: "总经理：组织能力强、传统、执行力强",
            MBTIType.ESFJ: "执政官：关心他人、社交能力强、责任感强",
            MBTIType.ISTP: "鉴赏家：大胆、实践性强、灵活应变",
            MBTIType.ISFP: "探险家：灵活、有艺术天赋、温和",
            MBTIType.ESTP: "企业家：精力充沛、直接、冒险精神",
            MBTIType.ESFP: "表演者：自发、热情、享受当下",
        }
        return descriptions.get(self.mbti, "未知人格类型")
