"""
Web 应用配置管理

使用 Pydantic Settings 管理环境变量配置
"""
import json
from typing import Optional, List, Dict, Any
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
    LLM_PROVIDER: str = Field(default="openai", description="当前激活的 LLM 提供商")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API密钥")
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1", description="OpenAI API 地址")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI 模型")

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Claude API密钥")
    ANTHROPIC_MODEL: str = Field(default="claude-3-haiku-20240307", description="Claude 模型")

    # 通义千问
    DASHSCOPE_API_KEY: Optional[str] = Field(default=None, description="通义千问API密钥")
    DASHSCOPE_API_BASE: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1", description="通义千问 API 地址")
    QIANWEN_MODEL: str = Field(default="qwen-max", description="通义千问模型")

    # 自定义 provider 列表，JSON 格式存储
    # 每项格式: {"name": "x666", "api_key": "sk-...", "api_base": "https://...", "model": "gpt-5-nano"}
    CUSTOM_PROVIDERS: str = Field(default="[]", description="自定义提供商列表（JSON）")

    # 成本控制
    DAILY_BUDGET: float = Field(default=10.0, description="每日预算（美元或人民币）")

    # Web 服务器配置
    HOST: str = Field(default="0.0.0.0", description="监听地址")
    PORT: int = Field(default=8000, description="监听端口")
    RELOAD: bool = Field(default=True, description="热重载（开发模式）")

    # 静态文件和模板路径
    TEMPLATES_DIR: str = Field(default="ainovel/web/templates", description="模板目录")
    STATIC_DIR: str = Field(default="ainovel/web/static", description="静态文件目录")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_custom_providers(self) -> List[Dict[str, Any]]:
        """解析并返回自定义 provider 列表。"""
        try:
            return json.loads(self.CUSTOM_PROVIDERS) or []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_custom_provider(self, name: str) -> Optional[Dict[str, Any]]:
        """按名称查找自定义 provider。"""
        name = name.lower()
        for p in self.get_custom_providers():
            if p.get("name", "").lower() == name:
                return p
        return None

    @property
    def LLM_MODEL(self) -> str:
        """根据当前激活 provider 返回对应模型名。"""
        p = self.LLM_PROVIDER.lower()
        if p == "claude":
            return self.ANTHROPIC_MODEL
        if p == "qwen":
            return self.QIANWEN_MODEL
        if p == "openai":
            return self.OPENAI_MODEL
        custom = self.get_custom_provider(p)
        if custom:
            return custom.get("model") or self.OPENAI_MODEL
        return self.OPENAI_MODEL

    @property
    def active_api_key(self) -> Optional[str]:
        """根据当前激活 provider 返回对应 API Key。"""
        p = self.LLM_PROVIDER.lower()
        if p == "claude":
            return self.ANTHROPIC_API_KEY
        if p == "qwen":
            return self.DASHSCOPE_API_KEY
        if p == "openai":
            return self.OPENAI_API_KEY
        custom = self.get_custom_provider(p)
        if custom:
            return custom.get("api_key") or self.OPENAI_API_KEY
        return self.OPENAI_API_KEY

    @property
    def active_api_base(self) -> str:
        """根据当前激活 provider 返回对应 API Base URL。"""
        p = self.LLM_PROVIDER.lower()
        if p == "qwen":
            return self.DASHSCOPE_API_BASE
        if p in ("openai", "claude"):
            return self.OPENAI_API_BASE
        custom = self.get_custom_provider(p)
        if custom:
            return custom.get("api_base") or self.OPENAI_API_BASE
        return self.OPENAI_API_BASE


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例（用于依赖注入）"""
    return settings
