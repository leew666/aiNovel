"""
Lorebook 引擎

参考 SillyTavern WorldInfo 机制：扫描章节文本，当文本中出现条目的触发关键词时，
自动将该条目注入到 LLM 上下文，实现按需加载而非全量传入。

核心流程：
1. 扫描文本（章节大纲 / 前情回顾 / 关键事件）
2. 对每个 WorldData / Character 条目，检查其 lorebook_keywords 是否出现在文本中
3. 命中的条目按优先级排序后返回，供 ContextCompressor 注入 prompt
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.memory.world_data import WorldData
from ainovel.memory.character import Character
from ainovel.memory.crud import world_data_crud, character_crud


@dataclass
class LorebookEntry:
    """Lorebook 命中条目"""
    entry_type: str          # "world" | "character"
    name: str
    content: Dict[str, Any]  # 原始卡片数据
    matched_keywords: List[str] = field(default_factory=list)
    hit_count: int = 0       # 命中关键词数量，用于排序


class LorebookEngine:
    """
    Lorebook 引擎

    职责：
    - 扫描输入文本，匹配 WorldData / Character 的 lorebook_keywords
    - 返回命中条目列表，按命中数降序排列
    - 支持 token 预算限制，超出时截断低优先级条目
    """

    def __init__(self, session: Session):
        self.session = session

    def scan(
        self,
        novel_id: int,
        text: str,
        max_world_entries: int = 8,
        max_character_entries: int = 5,
    ) -> Dict[str, List[LorebookEntry]]:
        """
        扫描文本，返回命中的世界观和角色条目

        Args:
            novel_id: 小说 ID
            text: 待扫描文本（章节大纲、关键事件、前情回顾等拼接）
            max_world_entries: 最多返回的世界观条目数
            max_character_entries: 最多返回的角色条目数

        Returns:
            {"world": [...], "character": [...]}
        """
        normalized_text = text.lower()

        world_hits = self._scan_world_data(novel_id, normalized_text, max_world_entries)
        char_hits = self._scan_characters(novel_id, normalized_text, max_character_entries)

        logger.debug(
            f"Lorebook 扫描完成：世界观命中 {len(world_hits)} 条，角色命中 {len(char_hits)} 条"
        )
        return {"world": world_hits, "character": char_hits}

    def scan_and_format(
        self,
        novel_id: int,
        text: str,
        max_world_entries: int = 8,
        max_character_entries: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        扫描并返回格式化卡片（与现有 get_world_cards / get_memory_cards 格式兼容）

        Returns:
            {
                "world_cards": [{"name": ..., "data_type": ..., "description": ..., "properties": ...}],
                "character_cards": [{"name": ..., "mbti": ..., "goals": ..., ...}]
            }
        """
        hits = self.scan(novel_id, text, max_world_entries, max_character_entries)

        world_cards = [entry.content for entry in hits["world"]]
        character_cards = [entry.content for entry in hits["character"]]

        return {"world_cards": world_cards, "character_cards": character_cards}

    # ------------------------------------------------------------------ #
    # 内部方法
    # ------------------------------------------------------------------ #

    def _scan_world_data(
        self, novel_id: int, normalized_text: str, limit: int
    ) -> List[LorebookEntry]:
        """扫描世界观数据，返回命中条目"""
        all_data: List[WorldData] = world_data_crud.get_by_novel_id(
            self.session, novel_id, skip=0, limit=200
        )

        hits: List[LorebookEntry] = []
        for item in all_data:
            keywords = item.lorebook_keywords or []

            # 无关键词时降级：用 name 作为隐式关键词
            if not keywords:
                keywords = [item.name]

            matched = [kw for kw in keywords if kw.strip().lower() in normalized_text]
            if matched:
                hits.append(
                    LorebookEntry(
                        entry_type="world",
                        name=item.name,
                        content={
                            "name": item.name,
                            "data_type": item.data_type.value,
                            "description": item.description,
                            "properties": item.properties or {},
                        },
                        matched_keywords=matched,
                        hit_count=len(matched),
                    )
                )

        hits.sort(key=lambda e: e.hit_count, reverse=True)
        return hits[:limit]

    def _scan_characters(
        self, novel_id: int, normalized_text: str, limit: int
    ) -> List[LorebookEntry]:
        """扫描角色数据，返回命中条目"""
        all_chars: List[Character] = character_crud.get_by_novel_id(
            self.session, novel_id, skip=0, limit=100
        )

        hits: List[LorebookEntry] = []
        for char in all_chars:
            keywords = char.lorebook_keywords or []

            # 无关键词时降级：用角色名作为隐式关键词
            if not keywords:
                keywords = [char.name]

            matched = [kw for kw in keywords if kw.strip().lower() in normalized_text]
            if matched:
                # 构建与 get_memory_cards 兼容的卡片格式
                important_memories = []
                if char.memories:
                    sorted_mems = sorted(
                        char.memories,
                        key=lambda m: (
                            {"high": 0, "medium": 1, "low": 2}.get(
                                m.get("importance", "medium"), 1
                            )
                        ),
                    )
                    important_memories = [
                        m.get("content", "") for m in sorted_mems[:3]
                    ]

                hits.append(
                    LorebookEntry(
                        entry_type="character",
                        name=char.name,
                        content={
                            "name": char.name,
                            "mbti": char.mbti.value if char.mbti else "",
                            "goals": char.goals or "",
                            "current_status": char.current_status or "",
                            "current_mood": char.current_mood or "",
                            "important_memories": important_memories,
                            "relationships": char.relationships or {},
                        },
                        matched_keywords=matched,
                        hit_count=len(matched),
                    )
                )

        hits.sort(key=lambda e: e.hit_count, reverse=True)
        return hits[:limit]
