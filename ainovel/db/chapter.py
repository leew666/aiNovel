"""
Chapter（章节）模型

表示分卷中的一个章节
"""
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ainovel.db.base import Base, TimestampMixin


class Chapter(Base, TimestampMixin):
    """章节模型"""

    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    volume_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("volumes.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属分卷ID"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="章节标题")
    order: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="章节序号（从1开始）"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="章节内容")
    word_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="字数统计"
    )

    # 流程管理字段
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="章节概要（用于大纲）"
    )
    key_events: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="关键事件列表（JSON格式）"
    )
    characters_involved: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="涉及角色列表（JSON格式）"
    )
    detail_outline: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="步骤4：详细细纲内容"
    )

    # 关系：多对一，多个章节属于一个分卷
    volume: Mapped["Volume"] = relationship("Volume", back_populates="chapters")

    def __repr__(self) -> str:
        return f"Chapter(id={self.id}, title={self.title!r}, order={self.order}, volume_id={self.volume_id}, word_count={self.word_count})"

    def update_word_count(self) -> None:
        """更新字数统计（中文字符计数）"""
        try:
            import jieba

            # 使用 jieba 分词，统计中文字数
            words = jieba.lcut(self.content)
            # 过滤掉标点符号和空格
            self.word_count = len([w for w in words if w.strip() and not w.isspace()])
        except ImportError:
            # 如果 jieba 不可用，使用简单的字符统计
            # 统计所有非空白字符
            self.word_count = len([c for c in self.content if not c.isspace()])
