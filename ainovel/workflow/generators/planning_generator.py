"""
创作思路生成器

步骤1：根据用户的模糊想法生成详细的创作思路和计划
"""
from typing import Dict, Any

from loguru import logger

from ainovel.llm.base import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager


class PlanningGenerator:
    """创作思路生成器"""

    def __init__(self, llm_client: BaseLLMClient):
        """
        初始化生成器

        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()

    def generate_planning(
        self,
        initial_idea: str,
        genre_id: str | None = None,
        plot_ids: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        生成创作思路

        Args:
            initial_idea: 用户的初始想法
            genre_id: 主题材 ID
            plot_ids: 情节流派标签 ID 列表
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            包含创作思路和元数据的字典
            {
                "planning": str,  # LLM原始输出
                "usage": {...},   # Token使用情况
                "cost": 0.01,     # 成本
            }
        """
        # 生成提示词（注入类型与情节上下文）
        prompt = self.prompt_manager.generate_planning_prompt(
            initial_idea, genre_id=genre_id, plot_ids=plot_ids
        )

        # 调用LLM
        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw_content = response["content"] or ""
        logger.debug(f"LLM原始输出(前500字符): {raw_content[:500]}")

        return {
            "planning": raw_content,
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
        }
