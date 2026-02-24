"""
FastAPI 依赖注入

提供全局共享的依赖实例（Database Session, LLM Client 等）
"""
from typing import Annotated, Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from ainovel.db.database import Database
from ainovel.llm.base import BaseLLMClient
from ainovel.llm.factory import LLMFactory
from ainovel.llm.exceptions import APIKeyError, LLMError
from ainovel.memory.character_db import CharacterDatabase
from ainovel.memory.world_db import WorldDatabase
from ainovel.workflow.orchestrator import WorkflowOrchestrator
from ainovel.web.config import settings


# ============ 全局单例（应用启动时初始化） ============

_db_instance: Database | None = None
_llm_client: BaseLLMClient | None = None


def get_database() -> Database:
    """
    获取全局 Database 实例

    Returns:
        Database 实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(settings.DATABASE_URL)
    return _db_instance


def get_llm_client() -> BaseLLMClient:
    """
    获取全局 LLM Client 实例

    Returns:
        BaseLLMClient 实例

    Raises:
        ValueError: 如果未配置 API 密钥
    """
    global _llm_client
    if _llm_client is None:
        try:
            _llm_client = LLMFactory.create_client(
                provider=settings.LLM_PROVIDER.lower(),
                model=settings.LLM_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                dashscope_api_key=settings.DASHSCOPE_API_KEY,
            )
        except (APIKeyError, LLMError) as e:
            raise ValueError(str(e)) from e

    return _llm_client


# ============ FastAPI 依赖函数 ============


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入：提供数据库 Session

    使用 yield 确保请求结束后自动关闭 Session

    Yields:
        Session: SQLAlchemy Session
    """
    db = get_database()
    with db.session_scope() as session:
        yield session


# ============ 类型别名（简化路由签名） ============

SessionDep = Annotated[Session, Depends(get_db)]
LLMClientDep = Annotated[BaseLLMClient, Depends(get_llm_client)]


def get_character_db(session: SessionDep) -> CharacterDatabase:
    """按请求创建角色数据库实例。"""
    return CharacterDatabase(session)


def get_world_db(session: SessionDep) -> WorldDatabase:
    """按请求创建世界观数据库实例。"""
    return WorldDatabase(session)


CharacterDBDep = Annotated[CharacterDatabase, Depends(get_character_db)]
WorldDBDep = Annotated[WorldDatabase, Depends(get_world_db)]


def get_orchestrator(
    llm_client: LLMClientDep,
    character_db: CharacterDBDep,
    world_db: WorldDBDep,
) -> WorkflowOrchestrator:
    """
    按请求创建工作流编排器实例。
    """
    return WorkflowOrchestrator(llm_client, character_db, world_db)


OrchestratorDep = Annotated[WorkflowOrchestrator, Depends(get_orchestrator)]
