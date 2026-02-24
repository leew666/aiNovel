"""
一致性检查生成器

对章节内容进行角色设定、世界观、时间线一致性检查。
"""
import json
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ainovel.llm.base import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.core.context_compressor import ContextCompressor
from ainovel.db.crud import chapter_crud
from ainovel.memory import CharacterDatabase, WorldDatabase


class ConsistencyGenerator:
    """一致性检查生成器"""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()

    def check_chapter(
        self,
        session: Session,
        chapter_id: int,
        content: Optional[str] = None,
        content_override: Optional[str] = None,
        strict: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1800,
    ) -> Dict[str, Any]:
        """
        检查章节一致性

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            content_override: 可选替代文本，不落库
            strict: 是否启用严格模式
            temperature: 温度
            max_tokens: 最大token
        """
        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        chapter_content = content if content is not None else content_override
        if chapter_content is None:
            chapter_content = chapter.content
        if not chapter_content:
            raise ValueError(f"章节内容为空，无法检查: {chapter_id}")

        volume = chapter.volume
        novel = volume.novel

        character_names = self._extract_character_names(chapter)
        keywords = self._extract_world_keywords(chapter)

        character_db = CharacterDatabase(session)
        world_db = WorldDatabase(session)
        character_memory_cards = character_db.get_memory_cards(
            novel_id=novel.id,
            character_names=character_names,
            limit_per_character=3,
        )
        world_memory_cards = world_db.get_world_cards(
            novel_id=novel.id,
            keywords=keywords,
            limit=8,
        )

        compressor = ContextCompressor(self.llm_client, session)
        previous_context = compressor.build_previous_context(
            volume_id=volume.id,
            current_order=chapter.order,
            window_size=5,
            token_budget=700,
        )

        prompt = self.prompt_manager.generate_consistency_check_prompt(
            title=novel.title,
            volume_title=volume.title,
            chapter_order=chapter.order,
            chapter_title=chapter.title,
            chapter_summary=chapter.summary or "暂无梗概",
            chapter_content=chapter_content,
            previous_context=previous_context,
            character_memory_cards=character_memory_cards,
            world_memory_cards=world_memory_cards,
            strict=strict,
        )

        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw_content = response["content"]
        report = self._parse_consistency_report(raw_content)

        return {
            "chapter_id": chapter_id,
            "overall_risk": report.get("overall_risk", "medium"),
            "summary": report.get("summary", ""),
            "issues": report.get("issues", []),
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
            "raw_content": raw_content,
        }

    def _parse_consistency_report(self, content: str) -> Dict[str, Any]:
        """解析一致性检查 JSON"""
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

    @staticmethod
    def _extract_character_names(chapter) -> List[str]:
        """从章节存储字段提取角色名"""
        if not chapter.characters_involved:
            return []
        try:
            data = json.loads(chapter.characters_involved)
            if isinstance(data, list):
                return [str(name) for name in data if str(name).strip()]
        except (TypeError, json.JSONDecodeError):
            return []
        return []

    @staticmethod
    def _extract_world_keywords(chapter) -> List[str]:
        """从关键事件和梗概提取世界观关键词（粗粒度）"""
        keywords: List[str] = []
        if chapter.summary:
            keywords.extend([part.strip() for part in chapter.summary.split("，") if part.strip()])
        if chapter.key_events:
            try:
                events = json.loads(chapter.key_events)
                if isinstance(events, list):
                    keywords.extend([str(e).strip() for e in events if str(e).strip()])
            except (TypeError, json.JSONDecodeError):
                pass
        # 去重并控制长度
        dedup = []
        seen = set()
        for kw in keywords:
            short_kw = kw[:20]
            if short_kw and short_kw not in seen:
                seen.add(short_kw)
                dedup.append(short_kw)
            if len(dedup) >= 12:
                break
        return dedup
