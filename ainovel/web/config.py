"""
Web 应用配置管理

使用 Pydantic Settings 管理环境变量配置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "AI小说创作系统"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, description="调试模式")

    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///data/ainovel.db",
        description="数据库连接URL",
    )

    # LLM 配置
    LLM_PROVIDER: str = Field(default="openai", description="LLM提供商: openai/claude/qwen")
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="默认模型")
    OPENAI_API_BASE: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI 兼容 API 地址（支持自定义端点）",
    )

    # API 密钥（从环境变量读取）
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API密钥")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Claude API密钥")
    DASHSCOPE_API_KEY: Optional[str] = Field(default=None, description="通义千问API密钥")

    # 成本控制
    DAILY_BUDGET: float = Field(default=10.0, description="每日预算（美元或人民币）")

    # Web 服务器配置
    HOST: str = Field(default="0.0.0.0", description="监听地址")
    PORT: int = Field(default=8000, description="监听端口")
    RELOAD: bool = Field(default=True, description="热重载（开发模式）")

    # 静态文件和模板路径
    TEMPLATES_DIR: str = Field(
        default="ainovel/web/templates",
        description="模板目录",
    )
    STATIC_DIR: str = Field(
        default="ainovel/web/static",
        description="静态文件目录",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例（用于依赖注入）"""
    return settings
