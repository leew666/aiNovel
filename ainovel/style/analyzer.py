"""
文风分析器

接收参考文本，调用 LLM 提取结构化风格特征，并持久化到数据库
"""
import json
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.llm.base import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.db.crud import style_profile_crud


class StyleAnalyzer:
    """文风分析器：从参考文本中提取写作风格特征"""

    def __init__(self, llm_client: BaseLLMClient):
        """
        Args:
            llm_client: LLM客户端，用于调用模型分析文本
        """
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()

    def analyze(
        self,
        source_text: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        分析参考文本，提取风格特征

        Args:
            source_text: 待分析的参考文本（建议500字以上以保证分析质量）
            temperature: LLM温度（低温度保证输出稳定）
            max_tokens: 最大token数

        Returns:
            {
                "style_features": {...},  # 结构化风格特征字典
                "usage": {...},
                "cost": 0.01,
            }

        Raises:
            ValueError: 文本过短或LLM输出无法解析
        """
        if len(source_text.strip()) < 100:
            raise ValueError("参考文本过短（至少100字），无法有效分析风格")

        prompt = self.prompt_manager.generate_style_analysis_prompt(source_text)

        logger.info(f"开始分析文风，参考文本长度: {len(source_text)} 字符")

        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw_content = response["content"]
        style_features = self._parse_style_features(raw_content)

        logger.info(f"文风分析完成，提取特征: {list(style_features.keys())}")

        return {
            "style_features": style_features,
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
        }

    def analyze_and_save(
        self,
        session: Session,
        novel_id: int,
        name: str,
        source_text: str,
        set_active: bool = True,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        分析文风并保存到数据库（一步完成）

        Args:
            session: 数据库会话
            novel_id: 关联的小说ID
            name: 风格档案名称（如"金庸武侠风"）
            source_text: 参考文本
            set_active: 是否将此档案设为激活状态
            temperature: LLM温度
            max_tokens: 最大token数

        Returns:
            {
                "profile_id": 1,
                "name": "金庸武侠风",
                "style_features": {...},
                "style_guide": "...",
                "usage": {...},
                "cost": 0.01,
            }
        """
        result = self.analyze(source_text, temperature, max_tokens)
        style_features = result["style_features"]

        # 从特征生成可直接注入提示词的风格指南
        from ainovel.style.applicator import StyleApplicator
        style_guide = StyleApplicator.features_to_guide(style_features)

        # 如果需要激活，先停用同小说其他档案
        if set_active:
            existing = style_profile_crud.get_by_novel_id(session, novel_id)
            for p in existing:
                p.is_active = False

        # 创建新档案
        profile = style_profile_crud.create(
            session,
            novel_id=novel_id,
            name=name,
            source_text=source_text,
            style_features=json.dumps(style_features, ensure_ascii=False),
            style_guide=style_guide,
            is_active=set_active,
        )
        session.commit()

        logger.info(f"文风档案已保存: ID={profile.id}, 名称={name}, 激活={set_active}")

        return {
            "profile_id": profile.id,
            "name": name,
            "style_features": style_features,
            "style_guide": style_guide,
            "usage": result["usage"],
            "cost": result["cost"],
        }

    def _parse_style_features(self, content: str) -> Dict[str, Any]:
        """
        解析LLM输出的风格特征JSON

        Args:
            content: LLM原始输出

        Returns:
            风格特征字典

        Raises:
            ValueError: 无法解析JSON
        """
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError(f"无法从LLM输出中提取JSON: {content[:200]}")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"风格特征JSON解析失败: {e}")
