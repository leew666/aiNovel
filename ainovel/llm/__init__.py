"""
LLM接入层 - 提供统一的多平台LLM API调用接口

支持的平台:
- OpenAI (gpt-4o, gpt-4o-mini)
- Anthropic Claude (claude-3-5-sonnet, claude-3-haiku)
- 阿里通义千问 (qwen-max, qwen-turbo)

核心功能:
- 统一的生成接口
- Token计数和成本监控
- 自动重试和错误处理
- 日志记录
"""

from ainovel.llm.base import BaseLLMClient
from ainovel.llm.openai_client import OpenAIClient
from ainovel.llm.claude_client import ClaudeClient
from ainovel.llm.qwen_client import QwenClient
from ainovel.llm.factory import LLMFactory, LLMConfig
from ainovel.llm.exceptions import (
    LLMError,
    APIKeyError,
    TokenLimitError,
    RateLimitError,
    BudgetExceededError,
)
from ainovel.llm.cost_tracker import CostTracker, get_cost_tracker, reset_cost_tracker

__all__ = [
    "BaseLLMClient",
    "OpenAIClient",
    "ClaudeClient",
    "QwenClient",
    "LLMFactory",
    "LLMConfig",
    "LLMError",
    "APIKeyError",
    "TokenLimitError",
    "RateLimitError",
    "BudgetExceededError",
    "CostTracker",
    "get_cost_tracker",
    "reset_cost_tracker",
]
