"""
阿里通义千问客户端实现

支持的模型:
- qwen-max
- qwen-turbo
- qwen-plus
"""

from typing import List, Dict, Any
import dashscope
from dashscope import Generation
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


# 通义千问模型计费表(人民币/1k tokens, 2024年1月数据)
QWEN_PRICING = {
    "qwen-max": {"input": 0.02, "output": 0.02},
    "qwen-turbo": {"input": 0.003, "output": 0.003},
    "qwen-plus": {"input": 0.008, "output": 0.008},
}


class QwenClient(BaseLLMClient):
    """阿里通义千问API客户端"""

    def __init__(self, api_key: str, model: str = "qwen-max", **kwargs):
        """
        初始化通义千问客户端

        Args:
            api_key: DashScope API密钥
            model: 模型名称,默认qwen-max
            **kwargs: 其他配置
        """
        super().__init__(api_key, model, **kwargs)

        # 验证API密钥
        if not api_key or api_key == "your_dashscope_api_key_here":
            raise APIKeyError("DashScope API密钥未配置或无效")

        # 设置API密钥(dashscope使用全局配置)
        dashscope.api_key = api_key

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
        调用通义千问API生成文本

        支持自动重试(最多3次,指数退避)

        Args:
            messages: 对话历史
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            生成结果字典
        """
        try:
            logger.debug(f"调用通义千问API, 模型: {self.model}, 消息数: {len(messages)}")

            # 调用API
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                result_format="message",  # 返回消息格式
                **kwargs,
            )

            # 检查响应状态
            if response.status_code != 200:
                raise LLMError(f"通义千问API返回错误: {response.message}")

            # 提取结果
            content = response.output.choices[0].message.content
            usage = response.usage

            # 计算成本
            cost = self.estimate_cost(usage.input_tokens, usage.output_tokens)

            result = {
                "content": content,
                "usage": {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                },
                "cost": cost,
                "model": self.model,
            }

            logger.info(
                f"通义千问生成成功, "
                f"输入: {usage.input_tokens} tokens, "
                f"输出: {usage.output_tokens} tokens, "
                f"成本: ¥{cost:.6f}"
            )

            return result

        except Exception as e:
            # 统一错误处理
            error_msg = str(e).lower()

            if "rate_limit" in error_msg or "throttling" in error_msg:
                logger.warning(f"通义千问限流: {e}")
                raise RateLimitError(f"通义千问限流: {e}")
            elif "invalid api" in error_msg or "unauthorized" in error_msg:
                raise APIKeyError(f"通义千问API密钥无效: {e}")
            elif "tokens exceed" in error_msg or "length" in error_msg:
                raise TokenLimitError(f"Token超限: {e}")
            else:
                raise LLMError(f"通义千问API调用失败: {e}")

    def count_tokens(self, text: str) -> int:
        """
        计算Token数量

        通义千问暂无官方Token计数API,使用粗略估计

        Args:
            text: 待计算的文本

        Returns:
            Token数量
        """
        # 粗略估计: 中文1字≈1 token, 英文1词≈1 token
        # 简化处理: 1 token ≈ 2字符
        return len(text) // 2

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        预估成本(人民币)

        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            预估成本(人民币)
        """
        # 从计费表获取单价
        pricing = QWEN_PRICING.get(
            self.model,
            QWEN_PRICING["qwen-max"],  # 默认使用qwen-max价格
        )

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost
