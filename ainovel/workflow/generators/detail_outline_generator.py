"""
详细细纲生成器

步骤4：根据大纲为每个章节生成详细细纲
"""
import json
import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from ainovel.llm.base import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.db.crud import chapter_crud


class DetailOutlineGenerator:
    """详细细纲生成器"""

    def __init__(self, llm_client: BaseLLMClient):
        """
        初始化生成器

        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()

    def generate_detail_outline(
        self,
        session: Session,
        chapter_id: int,
        temperature: float = 0.7,
        max_tokens: int = 3000,
    ) -> Dict[str, Any]:
        """
        为指定章节生成详细细纲

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            包含细纲和元数据的字典
            {
                "detail_outline": {...},  # 细纲JSON对象
                "usage": {...},           # Token使用情况
                "cost": 0.01,             # 成本
                "raw_content": ""         # 原始LLM输出
            }

        Raises:
            ValueError: 章节不存在或数据不完整
        """
        # 获取章节信息
        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        volume = chapter.volume
        novel = volume.novel

        # 解析章节大纲信息
        summary = chapter.summary or "暂无梗概"
        key_events = json.loads(chapter.key_events) if chapter.key_events else []
        characters_involved = (
            json.loads(chapter.characters_involved) if chapter.characters_involved else []
        )

        # 获取涉及角色的详细信息
        character_list = self._get_character_info(session, novel.id, characters_involved)

        # 获取世界观信息
        world_data_list = self._get_world_data(session, novel.id)

        # 获取前情回顾（前N章内容）
        previous_context = self._get_previous_context(session, chapter)

        # 生成提示词
        prompt = self.prompt_manager.generate_detail_outline_prompt(
            title=novel.title,
            volume_title=volume.title,
            chapter_order=chapter.order,
            chapter_title=chapter.title,
            chapter_summary=summary,
            key_events=key_events,
            character_list=character_list,
            world_data_list=world_data_list,
            previous_context=previous_context,
        )

        # 调用LLM
        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw_content = response["content"]

        # 解析JSON，失败时返回空结构并标记
        detail_outline_data, parse_failed = self._parse_detail_outline(raw_content)

        return {
            "detail_outline": detail_outline_data,
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
            "raw_content": raw_content,
            "parse_failed": parse_failed,
        }

    def save_detail_outline(
        self, session: Session, chapter_id: int, detail_outline: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        保存细纲到章节

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            detail_outline: 细纲数据

        Returns:
            保存统计信息
        """
        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        # 将细纲保存为JSON字符串；解析失败时直接存原始文本供用户编辑
        if isinstance(detail_outline, dict):
            chapter.detail_outline = json.dumps(detail_outline, ensure_ascii=False, indent=2)
        else:
            chapter.detail_outline = str(detail_outline)
        session.commit()

        return {
            "chapter_id": chapter_id,
            "scenes_count": len(detail_outline.get("scenes", [])) if isinstance(detail_outline, dict) else 0,
        }

    def generate_and_save(
        self,
        session: Session,
        chapter_id: int,
        temperature: float = 0.7,
        max_tokens: int = 3000,
    ) -> Dict[str, Any]:
        """
        生成并保存细纲（一步完成）

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            生成结果和保存统计
        """
        result = self.generate_detail_outline(
            session=session,
            chapter_id=chapter_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 解析失败时用原始文本代替空dict入库
        outline_to_save = result["raw_content"] if result["parse_failed"] else result["detail_outline"]
        stats = self.save_detail_outline(
            session=session, chapter_id=chapter_id, detail_outline=outline_to_save
        )

        result["stats"] = stats
        return result

    def _get_character_info(
        self, session: Session, novel_id: int, character_names: List[str]
    ) -> List[Dict[str, Any]]:
        """获取角色详细信息"""
        from ainovel.memory.crud import character_crud

        characters = []
        for name in character_names:
            char = character_crud.get_by_name(session, novel_id, name)
            if char:
                characters.append(
                    {
                        "name": char.name,
                        "mbti": char.mbti.value,
                        "background": char.background,
                        "personality_traits": char.personality_traits,
                        "memories": char.memories,
                    }
                )
        return characters

    def _get_world_data(self, session: Session, novel_id: int) -> List[Dict[str, Any]]:
        """获取世界观数据"""
        from ainovel.memory.crud import world_data_crud

        world_data_list = world_data_crud.get_by_novel_id(session, novel_id)
        return [
            {
                "data_type": wd.data_type.value,
                "title": wd.name,
                "content": wd.description,
            }
            for wd in world_data_list
        ]

    def _get_previous_context(self, session: Session, chapter) -> str:
        """获取前情回顾（前N章的概要）"""
        # 获取同一分卷中前面的章节
        previous_chapters = (
            session.query(chapter_crud.model)
            .filter(
                chapter_crud.model.volume_id == chapter.volume_id,
                chapter_crud.model.order < chapter.order,
            )
            .order_by(chapter_crud.model.order.desc())
            .limit(3)
            .all()
        )

        if not previous_chapters:
            return "本章为开篇，无前情"

        context_parts = []
        for ch in reversed(previous_chapters):
            context_parts.append(f"第{ch.order}章 {ch.title}: {ch.summary or '暂无概要'}")

        return "\n".join(context_parts)

    def _parse_detail_outline(self, content: str) -> tuple[Dict[str, Any], bool]:
        """
        解析LLM输出的细纲JSON

        Args:
            content: LLM输出内容

        Returns:
            (detail_outline_data, parse_failed)
            解析失败时返回空结构和 parse_failed=True，不抛异常
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
                return {"scenes": []}, True

        try:
            detail_outline_data = json.loads(json_str)
            return detail_outline_data, False
        except json.JSONDecodeError:
            return {"scenes": []}, True
