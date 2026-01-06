"""
LLM异常类定义

所有LLM相关异常都继承自LLMError基类,便于统一捕获和处理
"""


class LLMError(Exception):
    """LLM基础异常类"""

    pass


class APIKeyError(LLMError):
    """API密钥错误(未配置或无效)"""

    pass


class TokenLimitError(LLMError):
    """Token超限错误"""

    pass


class RateLimitError(LLMError):
    """API限流错误(429)"""

    pass


class BudgetExceededError(LLMError):
    """预算超限错误"""

    pass
