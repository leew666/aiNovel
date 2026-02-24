"""
文风应用器

将结构化风格特征转换为可注入提示词的风格指南字符串，
并提供从数据库加载激活档案的便捷方法
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.db.crud import style_profile_crud


class StyleApplicator:
    """文风应用器：将风格特征格式化为写作指令"""

    @staticmethod
    def features_to_guide(style_features: Dict[str, Any]) -> str:
        """
        将结构化风格特征转换为可直接注入提示词的风格指南

        Args:
            style_features: 由 StyleAnalyzer 提取的风格特征字典

        Returns:
            格式化的风格指南字符串
        """
        lines = []

        summary = style_features.get("summary", "")
        if summary:
            lines.append(f"【总体风格】{summary}")

        sentence_patterns = style_features.get("sentence_patterns", [])
        if sentence_patterns:
            lines.append(f"【句式特征】{'；'.join(sentence_patterns)}")

        vocab = style_features.get("vocabulary_style", "")
        if vocab:
            lines.append(f"【词汇风格】{vocab}")

        perspective = style_features.get("narrative_perspective", "")
        if perspective:
            lines.append(f"【叙事视角】{perspective}")

        pacing = style_features.get("pacing", "")
        if pacing:
            lines.append(f"【节奏控制】{pacing}")

        dialogue = style_features.get("dialogue_style", "")
        if dialogue:
            lines.append(f"【对话风格】{dialogue}")

        description = style_features.get("description_density", "")
        if description:
            lines.append(f"【描写密度】{description}")

        tone = style_features.get("tone", "")
        if tone:
            lines.append(f"【情感基调】{tone}")

        techniques = style_features.get("special_techniques", [])
        if techniques:
            lines.append(f"【特色技法】{'；'.join(techniques)}")

        if not lines:
            return "采用网络小说常见风格，节奏紧凑，对话生动"

        return "\n".join(lines)

    @staticmethod
    def load_active_guide(session: Session, novel_id: int) -> str:
        """
        从数据库加载小说当前激活的文风档案，返回风格指南字符串

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            风格指南字符串；若无激活档案则返回空字符串
        """
        profile = style_profile_crud.get_active(session, novel_id)
        if not profile:
            logger.debug(f"小说 {novel_id} 无激活文风档案，使用默认风格")
            return ""

        # 优先使用预格式化的 style_guide，否则从 features 重新生成
        if profile.style_guide:
            logger.debug(f"加载文风档案: {profile.name} (ID={profile.id})")
            return profile.style_guide

        if profile.style_features:
            features = json.loads(profile.style_features)
            guide = StyleApplicator.features_to_guide(features)
            logger.debug(f"从特征重新生成风格指南: {profile.name}")
            return guide

        return ""

    @staticmethod
    def load_guide_by_id(session: Session, profile_id: int) -> str:
        """
        按档案ID加载风格指南

        Args:
            session: 数据库会话
            profile_id: 文风档案ID

        Returns:
            风格指南字符串；档案不存在则返回空字符串
        """
        profile = style_profile_crud.get_by_id(session, profile_id)
        if not profile:
            return ""

        if profile.style_guide:
            return profile.style_guide

        if profile.style_features:
            features = json.loads(profile.style_features)
            return StyleApplicator.features_to_guide(features)

        return ""
