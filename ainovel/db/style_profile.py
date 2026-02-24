"""
StyleProfile（文风档案）模型

存储从参考文本中学习到的写作风格特征，与小说关联
"""
from typing import List
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ainovel.db.base import Base, TimestampMixin


class StyleProfile(Base, TimestampMixin):
    """文风档案模型：存储从参考文本提取的风格特征"""

    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    novel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True, comment="关联小说ID"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="风格档案名称（如：金庸风格、张爱玲风格）")
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始参考文本（用于分析的样本）")
    # 结构化风格特征，JSON格式存储
    style_features: Mapped[str | None] = mapped_column(Text, nullable=True, comment="提取的风格特征（JSON格式）")
    # 格式化后可直接注入提示词的风格描述
    style_guide: Mapped[str | None] = mapped_column(Text, nullable=True, comment="格式化风格指南（直接注入提示词）")
    is_active: Mapped[bool] = mapped_column(
        default=True, nullable=False, comment="是否为当前激活的风格档案"
    )

    # 关系：多对一，多个风格档案属于一部小说
    novel: Mapped["Novel"] = relationship("Novel", back_populates="style_profiles")

    def __repr__(self) -> str:
        return f"StyleProfile(id={self.id}, novel_id={self.novel_id}, name={self.name!r})"
