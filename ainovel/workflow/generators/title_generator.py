"""
书名与简介生成器

KB2 v5.0 第十一步：为小说生成最具吸引力的书名候选和黄金结构简介
"""
import json
import re
from typing import Dict, Any

from loguru import logger

from ainovel.llm.base import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager


def _extract_json(raw: str) -> Dict[str, Any]:
    """从 LLM 输出中提取 JSON 对象"""
    # 优先匹配 ```json ... ``` 代码块
    match = re.search(r"```json\s*([\s\S]+?)\s*```", raw)
    if match:
        return json.loads(match.group(1))
    # 降级：直接尝试解析整段
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(raw[start:end])
    raise ValueError("无法从 LLM 输出中提取 JSON")


class TitleSynopsisGenerator:
    """书名与简介生成器（KB2 第十一步）"""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()

    def generate(
        self,
        draft_title: str,
        genre: str,
        plots: str,
        story_core: str,
        protagonist: str,
        key_appeal: str,
        temperature: float = 0.8,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        生成书名候选列表和黄金结构简介

        Args:
            draft_title: 草稿书名（可为空）
            genre: 类型标签（如"玄幻"）
            plots: 情节标签（如"系统流,逆袭"）
            story_core: 故事核心（一句话概括）
            protagonist: 主角设定描述
            key_appeal: 核心爽点描述
            temperature: 温度（稍高以增加创意）
            max_tokens: 最大 token 数

        Returns:
            {
                "titles": [{"name": str, "scores": {...}, "reason": str}],
                "synopsis": {"hook": str, "summary": str, "cliffhanger": str, "full_text": str},
                "marketing_keywords": [str],
                "target_audience": str,
                "usage": {...},
                "cost": float,
                "raw_content": str
            }
        """
        prompt = self.prompt_manager.generate_title_synopsis_prompt(
            draft_title=draft_title,
            genre=genre,
            plots=plots,
            story_core=story_core,
            protagonist=protagonist,
            key_appeal=key_appeal,
        )

        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw_content = response.get("content") or ""
        logger.debug(f"书名简介生成原始输出(前300字符): {raw_content[:300]}")

        try:
            data = _extract_json(raw_content)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON 解析失败，返回原始内容: {e}")
            data = {"raw": raw_content}

        return {
            **data,
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
            "raw_content": raw_content,
        }
