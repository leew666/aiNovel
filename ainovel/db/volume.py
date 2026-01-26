"""
Volume（分卷）模型

表示小说中的一个分卷
"""
from typing import List
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ainovel.db.base import Base, TimestampMixin


class Volume(Base, TimestampMixin):
    """分卷模型"""

    __tablename__ = "volumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    novel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属小说ID"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="分卷标题")
    order: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="分卷序号（从1开始）"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="分卷简介")

    # 防剧透机制：当前卷设定（传入LLM）
    volume_config: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="当前卷设定（仅包含当前卷的世界观和登场角色，传入LLM）"
    )

    # 关系：多对一，多个分卷属于一部小说
    novel: Mapped["Novel"] = relationship("Novel", back_populates="volumes")

    # 关系：一对多，一个分卷包含多个章节
    chapters: Mapped[List["Chapter"]] = relationship(
        "Chapter", back_populates="volume", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Volume(id={self.id}, title={self.title!r}, order={self.order}, novel_id={self.novel_id})"
