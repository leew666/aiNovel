"""
LLM客户端抽象基类

定义了所有LLM客户端必须实现的接口,确保不同平台的一致性调用方式
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from loguru import logger


class BaseLLMClient(ABC):
    """
    LLM客户端抽象基类

    所有具体的LLM客户端(OpenAI/Claude/Qwen)都必须继承此类并实现抽象方法
    """

    def __init__(self, api_key: str, model: str, **kwargs):
        """
        初始化LLM客户端

        Args:
            api_key: API密钥
            model: 模型名称(如gpt-4o-mini, claude-3-haiku-20240307)
            **kwargs: 其他配置参数(如api_base, timeout等)
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        logger.info(f"初始化 {self.__class__.__name__}, 模型: {model}")

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        生成文本(核心接口)

        Args:
            messages: 对话历史,格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数(0-1),控制随机性
            max_tokens: 最大生成token数

        Returns:
            {
                "content": str,  # 生成的文本内容
                "usage": {  # Token使用统计
                    "input_tokens": int,
                    "output_tokens": int,
                    "total_tokens": int,
                },
                "cost": float,  # 本次调用成本(美元或人民币)
                "model": str,  # 实际使用的模型名
            }

        Raises:
            APIKeyError: API密钥错误
            TokenLimitError: Token超限
            RateLimitError: 限流错误
            LLMError: 其他错误
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数量

        Args:
            text: 待计算的文本

        Returns:
            Token数量
        """
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        预估成本

        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            预估成本(美元或人民币)
        """
        pass

    def _format_messages(self, messages: List[Dict[str, str]]) -> Any:
        """
        格式化消息(子类可选重写)

        不同平台的消息格式可能略有差异,子类可以重写此方法进行适配

        Args:
            messages: 标准消息格式

        Returns:
            平台特定的消息格式
        """
        return messages

    def _handle_error(self, error: Exception) -> None:
        """
        统一错误处理(子类可选重写)

        Args:
            error: 捕获的异常
        """
        logger.error(f"{self.__class__.__name__} 错误: {error}")
        raise error
