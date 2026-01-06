"""
OpenAI客户端实现

支持的模型:
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo
- gpt-3.5-turbo
"""

from typing import List, Dict, Any
from openai import OpenAI
from openai.types.chat import ChatCompletion
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from loguru import logger
import tiktoken

from ainovel.llm.base import BaseLLMClient
from ainovel.llm.exceptions import (
    APIKeyError,
    TokenLimitError,
    RateLimitError,
    LLMError,
)


# OpenAI模型计费表(美元/1k tokens, 2024年1月数据)
OPENAI_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


class OpenAIClient(BaseLLMClient):
    """OpenAI API客户端"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", **kwargs):
        """
        初始化OpenAI客户端

        Args:
            api_key: OpenAI API密钥
            model: 模型名称,默认gpt-4o-mini
            **kwargs: 其他配置(api_base, timeout等)
        """
        super().__init__(api_key, model, **kwargs)

        # 验证API密钥
        if not api_key or api_key == "your_openai_api_key_here":
            raise APIKeyError("OpenAI API密钥未配置或无效")

        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=kwargs.get("api_base", "https://api.openai.com/v1"),
            timeout=kwargs.get("timeout", 60),
        )

        # 初始化tiktoken编码器(用于Token计数)
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(f"模型 {model} 无对应编码器,使用cl100k_base")
            self.encoding = tiktoken.get_encoding("cl100k_base")

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
        调用OpenAI API生成文本

        支持自动重试(最多3次,指数退避)

        Args:
            messages: 对话历史
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            生成结果字典
        """
        try:
            logger.debug(f"调用OpenAI API, 模型: {self.model}, 消息数: {len(messages)}")

            # 调用API
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # 提取结果
            content = response.choices[0].message.content
            usage = response.usage

            # 计算成本
            cost = self.estimate_cost(usage.prompt_tokens, usage.completion_tokens)

            result = {
                "content": content,
                "usage": {
                    "input_tokens": usage.prompt_tokens,
                    "output_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
                "cost": cost,
                "model": response.model,
            }

            logger.info(
                f"OpenAI生成成功, "
                f"输入: {usage.prompt_tokens} tokens, "
                f"输出: {usage.completion_tokens} tokens, "
                f"成本: ${cost:.6f}"
            )

            return result

        except Exception as e:
            # 统一错误处理
            if "rate_limit" in str(e).lower() or "429" in str(e):
                logger.warning(f"OpenAI限流: {e}")
                raise RateLimitError(f"OpenAI限流: {e}")
            elif "invalid_api_key" in str(e).lower() or "401" in str(e):
                raise APIKeyError(f"OpenAI API密钥无效: {e}")
            elif "maximum context length" in str(e).lower():
                raise TokenLimitError(f"Token超限: {e}")
            else:
                raise LLMError(f"OpenAI API调用失败: {e}")

    def count_tokens(self, text: str) -> int:
        """
        使用tiktoken计算Token数量

        Args:
            text: 待计算的文本

        Returns:
            Token数量
        """
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"Token计数失败: {e}")
            # 降级方案: 粗略估计(1 token ≈ 4字符)
            return len(text) // 4

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
        pricing = OPENAI_PRICING.get(
            self.model,
            OPENAI_PRICING["gpt-4o-mini"],  # 默认使用gpt-4o-mini价格
        )

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost
