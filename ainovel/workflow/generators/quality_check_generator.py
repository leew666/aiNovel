"""
质量检查生成器

步骤6：对已生成的章节内容进行多维度质量检查，识别问题并给出修改建议
"""
import json
import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from ainovel.llm.base import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.db.crud import chapter_crud


class QualityCheckGenerator:
    """质量检查生成器"""

    def __init__(self, llm_client: BaseLLMClient):
        """
        初始化生成器

        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()

    def check_chapter(
        self,
        session: Session,
        chapter_id: int,
        temperature: float = 0.3,
        max_tokens: int = 3000,
    ) -> Dict[str, Any]:
        """
        对指定章节进行质量检查

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            temperature: 温度参数（低温度保证检查结果稳定）
            max_tokens: 最大token数

        Returns:
            包含检查结果和元数据的字典
            {
                "quality_report": {...},  # 质量报告JSON对象
                "usage": {...},           # Token使用情况
                "cost": 0.01,             # 成本
                "raw_content": ""         # 原始LLM输出
            }

        Raises:
            ValueError: 章节不存在或内容为空
        """
        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        if not chapter.content:
            raise ValueError(f"章节内容为空，无法进行质量检查: {chapter_id}")

        volume = chapter.volume
        novel = volume.novel

        # 获取涉及角色的详细信息
        characters_involved = (
            json.loads(chapter.characters_involved) if chapter.characters_involved else []
        )
        character_list = self._get_character_info(session, novel.id, characters_involved)

        # 获取前情回顾（用于检查连贯性）
        previous_context = self._get_previous_context(session, chapter)

        # 生成提示词
        prompt = self.prompt_manager.generate_quality_check_prompt(
            title=novel.title,
            volume_title=volume.title,
            chapter_order=chapter.order,
            chapter_title=chapter.title,
            chapter_summary=chapter.summary or "暂无梗概",
            chapter_content=chapter.content,
            character_list=character_list,
            previous_context=previous_context,
        )

        # 调用LLM
        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw_content = response["content"]

        # 解析JSON
        quality_report = self._parse_quality_report(raw_content)

        return {
            "quality_report": quality_report,
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
            "raw_content": raw_content,
        }

    def save_quality_report(
        self, session: Session, chapter_id: int, quality_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        保存质量报告到章节

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            quality_report: 质量报告数据

        Returns:
            保存统计信息
        """
        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        chapter.quality_report = json.dumps(quality_report, ensure_ascii=False, indent=2)
        session.commit()

        # 统计问题数量
        issues = quality_report.get("issues", [])
        overall_score = quality_report.get("overall_score", 0)

        return {
            "chapter_id": chapter_id,
            "overall_score": overall_score,
            "issues_count": len(issues),
            "critical_issues": sum(1 for i in issues if i.get("severity") == "critical"),
        }

    def check_and_save(
        self,
        session: Session,
        chapter_id: int,
        temperature: float = 0.3,
        max_tokens: int = 3000,
    ) -> Dict[str, Any]:
        """
        检查并保存质量报告（一步完成）

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            检查结果和保存统计
        """
        result = self.check_chapter(
            session=session,
            chapter_id=chapter_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        stats = self.save_quality_report(
            session=session,
            chapter_id=chapter_id,
            quality_report=result["quality_report"],
        )

        result["stats"] = stats
        return result

    def batch_check(
        self, session: Session, novel_id: int
    ) -> Dict[str, Any]:
        """
        批量检查小说所有已生成章节

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            批量检查结果
        """
        from ainovel.db.crud import novel_crud

        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        # 收集所有有内容的章节
        chapters_with_content = []
        for volume in novel.volumes:
            for chapter in volume.chapters:
                if chapter.content:
                    chapters_with_content.append(chapter)

        if not chapters_with_content:
            raise ValueError("没有已生成内容的章节可供检查")

        results = []
        for chapter in chapters_with_content:
            try:
                result = self.check_and_save(session=session, chapter_id=chapter.id)
                results.append({
                    "chapter_id": chapter.id,
                    "chapter_title": chapter.title,
                    "success": True,
                    "overall_score": result["stats"]["overall_score"],
                    "issues_count": result["stats"]["issues_count"],
                    "critical_issues": result["stats"]["critical_issues"],
                })
            except Exception as e:
                results.append({
                    "chapter_id": chapter.id,
                    "chapter_title": chapter.title,
                    "success": False,
                    "error": str(e),
                })

        return {
            "novel_id": novel_id,
            "total_chapters": len(chapters_with_content),
            "results": results,
        }

    def _get_character_info(
        self, session: Session, novel_id: int, character_names: List[str]
    ) -> List[Dict[str, Any]]:
        """获取角色详细信息"""
        from ainovel.memory.crud import character_crud

        characters = []
        for name in character_names:
            char = character_crud.get_by_name(session, novel_id, name)
            if char:
                characters.append({
                    "name": char.name,
                    "mbti": char.mbti.value,
                    "background": char.background,
                    "personality_traits": char.personality_traits,
                    "memories": char.memories,
                })
        return characters

    def _get_previous_context(self, session: Session, chapter) -> str:
        """获取前情回顾（前N章的概要）"""
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

    def _parse_quality_report(self, content: str) -> Dict[str, Any]:
        """
        解析LLM输出的质量报告JSON

        Args:
            content: LLM输出内容

        Returns:
            质量报告字典

        Raises:
            ValueError: JSON解析失败
        """
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError(f"无法从输出中提取JSON: {content[:200]}")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
