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
from ainovel.memory.character_db import CharacterDatabase
from ainovel.memory.world_db import WorldDatabase
from ainovel.workflow.orchestrator import WorkflowOrchestrator
from ainovel.web.config import settings


# ============ 全局单例（应用启动时初始化） ============

_db_instance: Database | None = None
_llm_client: BaseLLMClient | None = None
_character_db: CharacterDatabase | None = None
_world_db: WorldDatabase | None = None
_orchestrator: WorkflowOrchestrator | None = None


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
        # 根据配置创建对应的 LLM 客户端
        provider = settings.LLM_PROVIDER.lower()
        model = settings.LLM_MODEL

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("请在 .env 中配置 OPENAI_API_KEY")
            _llm_client = LLMFactory.create_openai_client(
                api_key=settings.OPENAI_API_KEY,
                model=model,
            )
        elif provider == "claude":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("请在 .env 中配置 ANTHROPIC_API_KEY")
            _llm_client = LLMFactory.create_claude_client(
                api_key=settings.ANTHROPIC_API_KEY,
                model=model,
            )
        elif provider == "qwen":
            if not settings.DASHSCOPE_API_KEY:
                raise ValueError("请在 .env 中配置 DASHSCOPE_API_KEY")
            _llm_client = LLMFactory.create_qwen_client(
                api_key=settings.DASHSCOPE_API_KEY,
                model=model,
            )
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")

    return _llm_client


def get_character_db() -> CharacterDatabase:
    """获取角色数据库实例"""
    global _character_db
    if _character_db is None:
        _character_db = CharacterDatabase()
    return _character_db


def get_world_db() -> WorldDatabase:
    """获取世界观数据库实例"""
    global _world_db
    if _world_db is None:
        _world_db = WorldDatabase()
    return _world_db


def get_orchestrator() -> WorkflowOrchestrator:
    """
    获取工作流编排器实例

    依赖于 LLM Client, Character DB, World DB
    """
    global _orchestrator
    if _orchestrator is None:
        llm_client = get_llm_client()
        character_db = get_character_db()
        world_db = get_world_db()
        _orchestrator = WorkflowOrchestrator(llm_client, character_db, world_db)
    return _orchestrator


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
OrchestratorDep = Annotated[WorkflowOrchestrator, Depends(get_orchestrator)]
CharacterDBDep = Annotated[CharacterDatabase, Depends(get_character_db)]
WorldDBDep = Annotated[WorldDatabase, Depends(get_world_db)]
