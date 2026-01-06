"""
数据库基础模型类

提供所有模型的通用字段和方法
"""
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有模型的基类"""

    pass


class TimestampMixin:
    """时间戳混入类，提供创建时间和更新时间字段"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )

    def to_dict(self) -> dict[str, Any]:
        """
        将模型实例转换为字典

        Returns:
            字典表示，包含所有字段
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # 处理 datetime 类型
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def __repr__(self) -> str:
        """返回模型的字符串表示"""
        class_name = self.__class__.__name__
        attrs = ", ".join(
            f"{column.name}={getattr(self, column.name)!r}"
            for column in self.__table__.columns
        )
        return f"{class_name}({attrs})"
