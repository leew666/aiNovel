"""
数据库连接和 Session 管理模块

提供数据库引擎初始化、Session 工厂和上下文管理器
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, Engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from loguru import logger


class Database:
    """数据库连接管理器"""

    def __init__(self, database_url: str = "sqlite:///ainovel.db", echo: bool = False):
        """
        初始化数据库连接

        Args:
            database_url: 数据库连接字符串
                - SQLite: "sqlite:///ainovel.db"
                - PostgreSQL: "postgresql://user:pass@localhost/dbname"
            echo: 是否打印 SQL 语句（调试用）
        """
        self.database_url = database_url
        self.echo = echo

        # 创建引擎
        if database_url.startswith("sqlite"):
            # SQLite 特殊配置：使用 StaticPool 避免多线程问题
            self._engine = create_engine(
                database_url,
                echo=echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            # PostgreSQL 等其他数据库
            self._engine = create_engine(database_url, echo=echo, pool_pre_ping=True)

        # 创建 Session 工厂
        self._session_factory = sessionmaker(
            bind=self._engine, autocommit=False, autoflush=False, expire_on_commit=False
        )

        logger.info(f"数据库连接已初始化: {database_url}")

    @property
    def engine(self) -> Engine:
        """获取数据库引擎"""
        return self._engine

    def create_all_tables(self) -> None:
        """创建所有表（开发环境使用，生产环境建议使用 Alembic 迁移）"""
        from ainovel.db.base import Base

        Base.metadata.create_all(bind=self._engine)
        self._apply_sqlite_legacy_migrations()
        logger.info("所有数据表已创建")

    def drop_all_tables(self) -> None:
        """删除所有表（测试环境使用，生产环境禁用）"""
        from ainovel.db.base import Base

        Base.metadata.drop_all(bind=self._engine)
        logger.warning("所有数据表已删除")

    def get_session(self) -> Session:
        """
        获取新的 Session 实例

        注意：调用方负责关闭 Session，建议使用 session_scope 上下文管理器
        """
        return self._session_factory()

    def _apply_sqlite_legacy_migrations(self) -> None:
        """
        对历史 SQLite 数据库做轻量补列，避免旧库与新模型不兼容。

        说明：
        - 只在 SQLite 下执行。
        - 仅在列缺失时执行 ALTER TABLE ADD COLUMN。
        - 不做删除/重命名等破坏性变更。
        """
        if not self.database_url.startswith("sqlite"):
            return

        migration_plan: dict[str, list[tuple[str, str]]] = {
            "novels": [
                ("author", "VARCHAR(100)"),
                ("genre", "VARCHAR(50)"),
                ("status", "VARCHAR(20) DEFAULT 'draft'"),
                ("global_config", "TEXT"),
                ("workflow_status", "VARCHAR(50) DEFAULT 'created'"),
                ("current_step", "INTEGER DEFAULT 0"),
                ("planning_content", "TEXT"),
            ],
            "volumes": [
                ("description", "TEXT"),
                ("volume_config", "TEXT"),
            ],
            "chapters": [
                ("summary", "TEXT"),
                ("key_events", "TEXT"),
                ("characters_involved", "TEXT"),
                ("detail_outline", "TEXT"),
                ("quality_report", "TEXT"),
            ],
        }

        inspector = inspect(self._engine)
        existing_tables = set(inspector.get_table_names())

        with self._engine.begin() as conn:
            for table_name, columns in migration_plan.items():
                if table_name not in existing_tables:
                    continue

                existing_columns = {
                    col["name"] for col in inspect(conn).get_columns(table_name)
                }
                for column_name, column_def in columns:
                    if column_name in existing_columns:
                        continue
                    conn.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {column_name} {column_def}"
                        )
                    )
                    logger.warning(
                        f"检测到旧版数据库，已补充列: {table_name}.{column_name}"
                    )

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        提供事务上下文管理器，自动提交/回滚

        用法:
            with db.session_scope() as session:
                novel = Novel(title="测试小说")
                session.add(novel)
                # 自动提交，或发生异常时自动回滚
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
            logger.debug("事务已提交")
        except Exception as e:
            session.rollback()
            logger.error(f"事务回滚: {e}")
            raise
        finally:
            session.close()


# 全局数据库实例（延迟初始化）
_db_instance: Database | None = None


def init_database(database_url: str = "sqlite:///ainovel.db", echo: bool = False) -> Database:
    """
    初始化全局数据库实例

    Args:
        database_url: 数据库连接字符串
        echo: 是否打印 SQL 语句

    Returns:
        Database 实例
    """
    global _db_instance
    _db_instance = Database(database_url=database_url, echo=echo)
    return _db_instance


def get_database() -> Database:
    """
    获取全局数据库实例

    Raises:
        RuntimeError: 如果数据库未初始化
    """
    if _db_instance is None:
        raise RuntimeError("数据库未初始化，请先调用 init_database()")
    return _db_instance
