"""
Anthropic Claude客户端实现

支持的模型:
- claude-3-5-sonnet-20241022
- claude-3-5-haiku-20241022
- claude-3-opus-20240229
- claude-3-haiku-20240307
"""

from typing import List, Dict, Any
from anthropic import Anthropic
from anthropic.types import Message
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from loguru import logger

from ainovel.llm.base import BaseLLMClient
from ainovel.llm.exceptions import (
    APIKeyError,
    TokenLimitError,
    RateLimitError,
    LLMError,
)


# Claude模型计费表(美元/1k tokens, 2024年1月数据)
CLAUDE_PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API客户端"""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", **kwargs):
        """
        初始化Claude客户端

        Args:
            api_key: Anthropic API密钥
            model: 模型名称,默认claude-3-haiku-20240307
            **kwargs: 其他配置(timeout等)
        """
        super().__init__(api_key, model, **kwargs)

        # 验证API密钥
        if not api_key or api_key == "your_anthropic_api_key_here":
            raise APIKeyError("Anthropic API密钥未配置或无效")

        # 初始化Anthropic客户端
        self.client = Anthropic(
            api_key=api_key,
            timeout=kwargs.get("timeout", 60),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        调用Claude API生成文本

        支持自动重试(最多3次,指数退避)

        Args:
            messages: 对话历史
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            生成结果字典
        """
        try:
            logger.debug(f"调用Claude API, 模型: {self.model}, 消息数: {len(messages)}")

            # Claude的消息格式需要分离system消息
            system_message = None
            formatted_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    formatted_messages.append(msg)

            # 调用API
            response: Message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message if system_message else "",
                messages=formatted_messages,
                **kwargs,
            )

            # 提取结果
            content = response.content[0].text
            usage = response.usage

            # 计算成本
            cost = self.estimate_cost(usage.input_tokens, usage.output_tokens)

            result = {
                "content": content,
                "usage": {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.input_tokens + usage.output_tokens,
                },
                "cost": cost,
                "model": response.model,
            }

            logger.info(
                f"Claude生成成功, "
                f"输入: {usage.input_tokens} tokens, "
                f"输出: {usage.output_tokens} tokens, "
                f"成本: ${cost:.6f}"
            )

            return result

        except Exception as e:
            # 统一错误处理
            if "rate_limit" in str(e).lower() or "429" in str(e):
                logger.warning(f"Claude限流: {e}")
                raise RateLimitError(f"Claude限流: {e}")
            elif "invalid_api_key" in str(e).lower() or "401" in str(e):
                raise APIKeyError(f"Claude API密钥无效: {e}")
            elif "maximum context" in str(e).lower() or "too many tokens" in str(e).lower():
                raise TokenLimitError(f"Token超限: {e}")
            else:
                raise LLMError(f"Claude API调用失败: {e}")

    def count_tokens(self, text: str) -> int:
        """
        计算Token数量(使用Claude的count_tokens API)

        Args:
            text: 待计算的文本

        Returns:
            Token数量
        """
        try:
            # Claude提供了count_tokens方法
            result = self.client.count_tokens(text)
            return result
        except Exception as e:
            logger.error(f"Token计数失败: {e}")
            # 降级方案: 粗略估计(1 token ≈ 3.5字符,Claude压缩率较高)
            return int(len(text) / 3.5)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        预估成本(美元)

        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            预估成本(美元)
        """
        # 从计费表获取单价
        pricing = CLAUDE_PRICING.get(
            self.model,
            CLAUDE_PRICING["claude-3-haiku-20240307"],  # 默认使用haiku价格
        )

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost
