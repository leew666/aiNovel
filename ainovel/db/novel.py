"""
Novel（小说）模型

表示一部小说的基本信息
"""
from enum import Enum
from typing import List
from sqlalchemy import String, Text, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ainovel.db.base import Base, TimestampMixin


class NovelStatus(str, Enum):
    """小说状态枚举"""

    DRAFT = "draft"  # 草稿
    ONGOING = "ongoing"  # 连载中
    COMPLETED = "completed"  # 已完结


class WorkflowStatus(str, Enum):
    """创作流程状态枚举"""

    CREATED = "created"  # 已创建
    PLANNING = "planning"  # 规划中（步骤1：制定创作思路）
    WORLD_BUILDING = "world_building"  # 世界构建中（步骤2：生成世界背景和角色）
    OUTLINE = "outline"  # 大纲生成中（步骤3：生成作品大纲）
    DETAIL_OUTLINE = "detail_outline"  # 细纲生成中（步骤4：生成作品细纲）
    WRITING = "writing"  # 写作中（步骤5：创作章节内容）
    QUALITY_CHECK = "quality_check"  # 质量检查中（步骤6：检查章节质量）
    COMPLETED = "completed"  # 已完成


class Novel(Base, TimestampMixin):
    """小说模型"""

    __tablename__ = "novels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    title: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True, comment="小说标题"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="小说简介")
    author: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="作者")
    genre: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="小说类型（如玄幻、都市、科幻）"
    )
    # 情节标签：逗号分隔的 plot_id 列表，如 "rebirth,revenge,face_slap"
    plots: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="情节流派标签（逗号分隔的 plot_id）"
    )
    status: Mapped[NovelStatus] = mapped_column(
        SQLEnum(NovelStatus),
        default=NovelStatus.DRAFT,
        nullable=False,
        index=True,
        comment="小说状态",
    )

    # 防剧透机制：全局设定（不传入LLM）
    global_config: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="全局设定（包含完整世界观、最终boss、核心秘密，不传入LLM）"
    )

    # 流程管理字段
    workflow_status: Mapped[WorkflowStatus] = mapped_column(
        SQLEnum(WorkflowStatus),
        default=WorkflowStatus.CREATED,
        nullable=False,
        index=True,
        comment="创作流程状态",
    )
    current_step: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="当前步骤（0-5）"
    )
    planning_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="步骤1：创作思路内容"
    )

    # 关系：一对多，一部小说包含多个分卷
    volumes: Mapped[List["Volume"]] = relationship(
        "Volume", back_populates="novel", cascade="all, delete-orphan", lazy="selectin"
    )

    # 关系：一对多，一部小说可有多个文风档案
    style_profiles: Mapped[List["StyleProfile"]] = relationship(
        "StyleProfile", back_populates="novel", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Novel(id={self.id}, title={self.title!r}, status={self.status.value})"
