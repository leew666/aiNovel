"""
LLM配置和工厂类

提供统一的配置管理和客户端创建接口
"""

import os
from typing import Optional, Dict, Type, Any
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
        """验证provider，内置三种，其余视为 OpenAI 兼容自定义提供商"""
        return v.lower().strip()

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
    _provider_registry: Dict[str, Dict[str, Any]] = {}  # provider -> meta

    @classmethod
    def _ensure_registry(cls) -> None:
        """初始化内置提供商注册表。"""
        if cls._provider_registry:
            return
        cls._provider_registry = {
            "openai": {
                "client_cls": OpenAIClient,
                "api_key_field": "openai_api_key",
                "uses_openai_base": True,
            },
            "claude": {
                "client_cls": ClaudeClient,
                "api_key_field": "anthropic_api_key",
                "uses_openai_base": False,
            },
            "qwen": {
                "client_cls": QwenClient,
                "api_key_field": "dashscope_api_key",
                "uses_openai_base": False,
            },
        }

    @classmethod
    def register_provider(
        cls,
        name: str,
        client_cls: Type[BaseLLMClient],
        api_key_field: str = "openai_api_key",
        uses_openai_base: bool = True,
    ) -> None:
        """
        注册自定义提供商。

        Args:
            name: 提供商名称
            client_cls: 客户端类
            api_key_field: LLMConfig 中对应的密钥字段名
            uses_openai_base: 是否向客户端传递 openai_api_base
        """
        cls._ensure_registry()
        provider = name.lower().strip()
        cls._provider_registry[provider] = {
            "client_cls": client_cls,
            "api_key_field": api_key_field,
            "uses_openai_base": uses_openai_base,
        }
        logger.info(f"已注册提供商: {provider} -> {client_cls.__name__}")

    @classmethod
    def get_registered_providers(cls) -> list[str]:
        """获取已注册提供商列表。"""
        cls._ensure_registry()
        return sorted(cls._provider_registry.keys())

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
        cls._ensure_registry()

        # 兼容旧参数命名：api_key
        if provider and "api_key" in kwargs:
            provider_name = provider.lower().strip()
            meta = cls._provider_registry.get(provider_name)
            key_field = meta["api_key_field"] if meta else "openai_api_key"
            if key_field not in kwargs:
                kwargs[key_field] = kwargs.pop("api_key")

        # 加载配置
        if config is None:
            config = LLMConfig.from_env(provider=provider, **kwargs)

        # 优先校验密钥，避免在缺失密钥时误用缓存客户端
        cls._validate_api_key(config)

        # 检查缓存
        cache_key = f"{config.provider}:{config.model}"
        if cache_key in cls._clients:
            logger.debug(f"使用缓存的LLM客户端: {cache_key}")
            return cls._clients[cache_key]

        # 创建客户端
        logger.info(f"创建LLM客户端: {config.provider}, 模型: {config.model}")
        meta = cls._provider_registry.get(config.provider)

        if meta:
            client_cls: Type[BaseLLMClient] = meta["client_cls"]
            api_key_field: str = meta["api_key_field"]
            api_key = getattr(config, api_key_field, None)

            client_kwargs: Dict[str, Any] = {"timeout": config.timeout}
            if meta.get("uses_openai_base"):
                client_kwargs["api_base"] = config.openai_api_base

            client = client_cls(
                api_key=api_key,
                model=config.model,
                **client_kwargs,
            )
        else:
            # 自定义 provider：直接走 OpenAI 兼容接口
            client = OpenAIClient(
                api_key=config.openai_api_key,
                model=config.model,
                api_base=config.openai_api_base,
                timeout=config.timeout,
            )

        # 缓存客户端
        cls._clients[cache_key] = client

        return client

    @classmethod
    def clear_cache(cls) -> None:
        """清空客户端缓存"""
        cls._clients.clear()
        logger.info("已清空LLM客户端缓存")

    @classmethod
    def create_from_env(cls, **kwargs) -> BaseLLMClient:
        """
        从环境变量创建客户端（向后兼容）。
        """
        return cls.create_client(config=LLMConfig.from_env(**kwargs))

    @classmethod
    def create_openai_client(
        cls,
        api_key: str,
        model: str = "gpt-4o-mini",
        **kwargs,
    ) -> BaseLLMClient:
        """创建 OpenAI 客户端（向后兼容）。"""
        return cls.create_client(
            provider="openai",
            model=model,
            openai_api_key=api_key,
            **kwargs,
        )

    @classmethod
    def create_claude_client(
        cls,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
        **kwargs,
    ) -> BaseLLMClient:
        """创建 Claude 客户端（向后兼容）。"""
        return cls.create_client(
            provider="claude",
            model=model,
            anthropic_api_key=api_key,
            **kwargs,
        )

    @classmethod
    def create_qwen_client(
        cls,
        api_key: str,
        model: str = "qwen-max",
        **kwargs,
    ) -> BaseLLMClient:
        """创建 Qwen 客户端（向后兼容）。"""
        return cls.create_client(
            provider="qwen",
            model=model,
            dashscope_api_key=api_key,
            **kwargs,
        )

    @staticmethod
    def _validate_api_key(config: LLMConfig) -> None:
        """根据提供商校验 API Key。自定义提供商使用 openai_api_key。"""
        LLMFactory._ensure_registry()
        meta = LLMFactory._provider_registry.get(config.provider)
        if meta:
            key_field = meta["api_key_field"]
            if not getattr(config, key_field, None):
                raise APIKeyError(f"{config.provider} API密钥未配置")
            return
        # 未注册 provider 按 OpenAI 兼容处理
        if not config.openai_api_key:
            raise APIKeyError(f"{config.provider} API密钥未配置")
