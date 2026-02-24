"""
伏笔追踪（PlotArc）模型与服务

职责：
- 记录小说中的伏笔/情节弧的埋设、发展、回收状态
- 支持按状态、章节、角色查询未回收伏笔
- 为 RAG 检索提供结构化的伏笔卡片

伏笔生命周期：
  planted（埋设）→ developing（发展中）→ resolved（已回收）
  任意阶段可标记为 abandoned（放弃）
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Text, Integer, Enum as SQLEnum, JSON, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, Session

from ainovel.db.base import Base, TimestampMixin
from ainovel.db.crud import CRUDBase


class PlotArcStatus(str, Enum):
    """伏笔状态枚举"""
    PLANTED = "planted"        # 已埋设，尚未展开
    DEVELOPING = "developing"  # 发展中，已有后续铺垫
    RESOLVED = "resolved"      # 已回收，情节完结
    ABANDONED = "abandoned"    # 已放弃，不再追踪


class PlotArc(Base, TimestampMixin):
    """
    伏笔/情节弧模型

    存储小说中每条伏笔的完整生命周期信息，
    embedding 字段用于 RAG 向量检索。
    """
    __tablename__ = "plot_arcs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    novel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属小说 ID"
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="伏笔名称")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="伏笔内容描述")
    status: Mapped[PlotArcStatus] = mapped_column(
        SQLEnum(PlotArcStatus),
        default=PlotArcStatus.PLANTED,
        nullable=False,
        index=True,
        comment="伏笔状态",
    )

    # 关联信息（JSON 存储，避免多表关联复杂度）
    planted_chapter: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="埋设章节序号"
    )
    resolved_chapter: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="回收章节序号"
    )
    related_characters: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="相关角色名列表"
    )
    related_keywords: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="触发关键词列表（用于 Lorebook 兼容扫描）"
    )

    # 向量存储（RAG 检索用）
    embedding: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="文本 embedding 向量（float 列表）"
    )

    # 扩展元数据
    importance: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False,
        comment="重要程度：high / medium / low"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="创作备注")

    def to_card(self) -> Dict[str, Any]:
        """返回注入 prompt 用的伏笔卡片格式"""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "importance": self.importance,
            "planted_chapter": self.planted_chapter,
            "related_characters": self.related_characters or [],
            "related_keywords": self.related_keywords or [],
        }


class PlotArcCRUD(CRUDBase[PlotArc]):
    """PlotArc 模型的 CRUD 管理器"""

    def get_by_novel_id(
        self, session: Session, novel_id: int, skip: int = 0, limit: int = 200
    ) -> List[PlotArc]:
        """查询小说所有伏笔"""
        stmt = (
            select(PlotArc)
            .where(PlotArc.novel_id == novel_id)
            .order_by(PlotArc.planted_chapter, PlotArc.id)
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_active(
        self, session: Session, novel_id: int, limit: int = 50
    ) -> List[PlotArc]:
        """查询未回收的伏笔（planted + developing）"""
        stmt = (
            select(PlotArc)
            .where(
                PlotArc.novel_id == novel_id,
                PlotArc.status.in_([PlotArcStatus.PLANTED, PlotArcStatus.DEVELOPING]),
            )
            .order_by(PlotArc.importance, PlotArc.planted_chapter)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_by_status(
        self, session: Session, novel_id: int, status: PlotArcStatus, limit: int = 100
    ) -> List[PlotArc]:
        """按状态查询伏笔"""
        stmt = (
            select(PlotArc)
            .where(PlotArc.novel_id == novel_id, PlotArc.status == status)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_without_embedding(
        self, session: Session, novel_id: int
    ) -> List[PlotArc]:
        """查询尚未生成 embedding 的伏笔"""
        stmt = select(PlotArc).where(
            PlotArc.novel_id == novel_id,
            PlotArc.embedding.is_(None),
        )
        return list(session.scalars(stmt).all())


# 全局 CRUD 实例
plot_arc_crud = PlotArcCRUD(PlotArc)


class PlotArcTracker:
    """
    伏笔追踪服务

    职责：
    - 创建/更新伏笔
    - 推进伏笔状态（planted → developing → resolved）
    - 查询当前活跃伏笔，供上下文注入
    """

    def __init__(self, session: Session):
        self.session = session

    def plant(
        self,
        novel_id: int,
        name: str,
        description: str,
        planted_chapter: Optional[int] = None,
        related_characters: Optional[List[str]] = None,
        related_keywords: Optional[List[str]] = None,
        importance: str = "medium",
        notes: Optional[str] = None,
    ) -> PlotArc:
        """埋设新伏笔"""
        arc = plot_arc_crud.create(
            self.session,
            novel_id=novel_id,
            name=name,
            description=description,
            status=PlotArcStatus.PLANTED,
            planted_chapter=planted_chapter,
            related_characters=related_characters or [],
            related_keywords=related_keywords or [],
            importance=importance,
            notes=notes,
        )
        return arc

    def develop(self, arc_id: int, notes: Optional[str] = None) -> Optional[PlotArc]:
        """将伏笔推进到发展中状态"""
        kwargs: Dict[str, Any] = {"status": PlotArcStatus.DEVELOPING}
        if notes is not None:
            kwargs["notes"] = notes
        return plot_arc_crud.update(self.session, arc_id, **kwargs)

    def resolve(self, arc_id: int, resolved_chapter: Optional[int] = None) -> Optional[PlotArc]:
        """回收伏笔"""
        kwargs: Dict[str, Any] = {"status": PlotArcStatus.RESOLVED}
        if resolved_chapter is not None:
            kwargs["resolved_chapter"] = resolved_chapter
        return plot_arc_crud.update(self.session, arc_id, **kwargs)

    def abandon(self, arc_id: int) -> Optional[PlotArc]:
        """放弃伏笔"""
        return plot_arc_crud.update(self.session, arc_id, status=PlotArcStatus.ABANDONED)

    def get_active_cards(self, novel_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取当前活跃伏笔的卡片列表，按重要程度排序

        Returns:
            [{"name": ..., "description": ..., "status": ..., ...}, ...]
        """
        # 重要程度排序：high > medium > low
        importance_order = {"high": 0, "medium": 1, "low": 2}
        arcs = plot_arc_crud.get_active(self.session, novel_id, limit=limit * 2)
        arcs.sort(key=lambda a: importance_order.get(a.importance, 1))
        return [arc.to_card() for arc in arcs[:limit]]
