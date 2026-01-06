"""
创作思路生成器

步骤1：根据用户的模糊想法生成详细的创作思路和计划
"""
import json
import re
from typing import Dict, Any

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
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        生成创作思路

        Args:
            initial_idea: 用户的初始想法
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            包含创作思路和元数据的字典
            {
                "planning": {...},  # 创作思路JSON对象
                "usage": {...},     # Token使用情况
                "cost": 0.01,       # 成本
                "raw_content": ""   # 原始LLM输出
            }
        """
        # 生成提示词
        prompt = self.prompt_manager.generate_planning_prompt(initial_idea)

        # 调用LLM
        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw_content = response["content"]

        # 解析JSON
        planning_data = self._parse_planning(raw_content)

        return {
            "planning": planning_data,
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
            "raw_content": raw_content,
        }

    def _parse_planning(self, content: str) -> Dict[str, Any]:
        """
        解析LLM输出的创作思路JSON

        Args:
            content: LLM输出内容

        Returns:
            创作思路字典

        Raises:
            ValueError: JSON解析失败
        """
        # 尝试提取JSON代码块
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接查找JSON对象
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError(f"无法从输出中提取JSON: {content[:200]}")

        try:
            planning_data = json.loads(json_str)
            return planning_data
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
