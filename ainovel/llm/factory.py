"""
LLM配置和工厂类

提供统一的配置管理和客户端创建接口
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from loguru import logger

from ainovel.llm.base import BaseLLMClient
from ainovel.llm.openai_client import OpenAIClient
from ainovel.llm.claude_client import ClaudeClient
from ainovel.llm.qwen_client import QwenClient
from ainovel.llm.exceptions import APIKeyError, LLMError


class LLMConfig(BaseModel):
    """LLM配置模型"""

    # 通用配置
    provider: str = Field(
        default="openai",
        description="LLM提供商: openai/claude/qwen",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="模型名称",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="温度参数(0-1)",
    )
    max_tokens: int = Field(
        default=2000,
        gt=0,
        description="最大生成token数",
    )
    daily_budget: float = Field(
        default=5.0,
        gt=0,
        description="日预算上限(美元或人民币)",
    )
    enable_cache: bool = Field(
        default=True,
        description="是否启用缓存",
    )

    # API密钥配置
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API密钥",
    )
    openai_api_base: Optional[str] = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API地址",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API密钥",
    )
    dashscope_api_key: Optional[str] = Field(
        default=None,
        description="DashScope API密钥",
    )

    # 超时配置
    timeout: int = Field(
        default=60,
        gt=0,
        description="API调用超时(秒)",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """验证provider"""
        allowed = ["openai", "claude", "qwen"]
        if v not in allowed:
            raise ValueError(f"provider必须是{allowed}之一")
        return v

    @classmethod
    def from_env(cls, **kwargs) -> "LLMConfig":
        """
        从环境变量加载配置

        优先级: kwargs > 环境变量 > 默认值

        Returns:
            配置对象
        """
        config_dict = {
            "provider": os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
            "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "2000")),
            "daily_budget": float(os.getenv("DAILY_BUDGET", "5.0")),
            "enable_cache": os.getenv("ENABLE_CACHE", "true").lower() == "true",
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "openai_api_base": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
            "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY"),
        }

        # 模型配置
        provider = config_dict["provider"]
        if provider == "openai":
            config_dict["model"] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        elif provider == "claude":
            config_dict["model"] = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        elif provider == "qwen":
            config_dict["model"] = os.getenv("QIANWEN_MODEL", "qwen-max")

        # 覆盖kwargs
        config_dict.update(kwargs)

        return cls(**config_dict)


class LLMFactory:
    """
    LLM客户端工厂

    根据配置创建对应的LLM客户端
    """

    _clients: Dict[str, BaseLLMClient] = {}  # 客户端缓存

    @classmethod
    def create_client(
        cls,
        config: Optional[LLMConfig] = None,
        provider: Optional[str] = None,
        **kwargs,
    ) -> BaseLLMClient:
        """
        创建LLM客户端

        Args:
            config: 配置对象(优先使用)
            provider: 提供商名称(当config为None时使用)
            **kwargs: 其他参数

        Returns:
            对应的LLM客户端

        Raises:
            APIKeyError: API密钥未配置
            LLMError: 不支持的提供商
        """
        # 加载配置
        if config is None:
            config = LLMConfig.from_env(provider=provider, **kwargs)

        # 检查缓存
        cache_key = f"{config.provider}:{config.model}"
        if cache_key in cls._clients:
            logger.debug(f"使用缓存的LLM客户端: {cache_key}")
            return cls._clients[cache_key]

        # 创建客户端
        logger.info(f"创建LLM客户端: {config.provider}, 模型: {config.model}")

        if config.provider == "openai":
            if not config.openai_api_key:
                raise APIKeyError("OpenAI API密钥未配置")
            client = OpenAIClient(
                api_key=config.openai_api_key,
                model=config.model,
                api_base=config.openai_api_base,
                timeout=config.timeout,
            )

        elif config.provider == "claude":
            if not config.anthropic_api_key:
                raise APIKeyError("Anthropic API密钥未配置")
            client = ClaudeClient(
                api_key=config.anthropic_api_key,
                model=config.model,
                timeout=config.timeout,
            )

        elif config.provider == "qwen":
            if not config.dashscope_api_key:
                raise APIKeyError("DashScope API密钥未配置")
            client = QwenClient(
                api_key=config.dashscope_api_key,
                model=config.model,
            )

        else:
            raise LLMError(f"不支持的LLM提供商: {config.provider}")

        # 缓存客户端
        cls._clients[cache_key] = client

        return client

    @classmethod
    def clear_cache(cls) -> None:
        """清空客户端缓存"""
        cls._clients.clear()
        logger.info("已清空LLM客户端缓存")
