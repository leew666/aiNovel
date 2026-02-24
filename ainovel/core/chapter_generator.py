"""
章节生成器

根据大纲和前文生成具体的章节内容
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.llm import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.core.context_compressor import ContextCompressor
from ainovel.db import novel_crud, volume_crud, chapter_crud
from ainovel.memory import CharacterDatabase, WorldDatabase


class ChapterGenerator:
    """章节生成器"""

    def __init__(self, llm_client: BaseLLMClient, session: Session):
        """
        初始化章节生成器

        Args:
            llm_client: LLM客户端
            session: 数据库会话
        """
        self.llm_client = llm_client
        self.session = session
        self.prompt_manager = PromptManager()
        self.character_db = CharacterDatabase(session)
        self.world_db = WorldDatabase(session)
        self.context_compressor = ContextCompressor(llm_client, session)

    def generate_chapter(
        self,
        chapter_id: int,
        style_guide: str = "",
        word_count_min: int = 2000,
        word_count_max: int = 3000,
        temperature: float = 0.8,
        max_tokens: int = 4000,
        use_previous_context: bool = True,
        context_window_size: int = 3,
    ) -> Dict[str, Any]:
        """
        生成章节内容

        Args:
            chapter_id: 章节ID
            style_guide: 写作风格指南
            word_count_min: 最小字数
            word_count_max: 最大字数
            temperature: LLM温度参数
            max_tokens: 最大生成token数
            use_previous_context: 是否使用前文上下文
            context_window_size: 上下文窗口大小（前N章）

        Returns:
            生成结果，包含章节内容和token使用情况

        Raises:
            ValueError: 如果章节不存在或数据不足
        """
        logger.info(f"开始生成章节 ID={chapter_id}")

        # 1. 获取章节信息
        chapter = chapter_crud.get_by_id(self.session, chapter_id)
        if chapter is None:
            raise ValueError(f"章节 ID {chapter_id} 不存在")

        # 2. 获取分卷和小说信息
        volume = volume_crud.get_by_id(self.session, chapter.volume_id)
        if volume is None:
            raise ValueError(f"分卷 ID {chapter.volume_id} 不存在")

        novel = novel_crud.get_by_id(self.session, volume.novel_id)
        if novel is None:
            raise ValueError(f"小说 ID {volume.novel_id} 不存在")

        # 3. 解析章节梗概和关键事件
        chapter_summary, key_events = self._parse_chapter_outline(chapter.content)

        # 4. 获取涉及的角色信息
        character_names = self._extract_character_names(chapter.content)
        character_list = self._get_characters_info(volume.novel_id, character_names)

        # 5. 获取世界观数据
        world_data = self.world_db.list_all(volume.novel_id)
        world_data_list = [data.to_dict() for data in world_data]

        # 6. 生成上下文包（前情 + 角色记忆卡 + 世界观卡片）
        previous_context = ""
        character_memory_cards: List[Dict[str, Any]] = []
        world_memory_cards: List[Dict[str, Any]] = []
        if use_previous_context:
            context_bundle = self.context_compressor.build_context_bundle(
                volume_id=chapter.volume_id,
                current_order=chapter.order,
                window_size=context_window_size,
                token_budget=800,
                novel_id=volume.novel_id,
                character_names=character_names,
                world_keywords=key_events,
            )
            previous_context = context_bundle.get("previous_context", "")
            character_memory_cards = context_bundle.get("character_memory_cards", [])
            world_memory_cards = context_bundle.get("world_memory_cards", [])
        else:
            character_memory_cards = self.character_db.get_memory_cards(
                novel_id=volume.novel_id,
                character_names=character_names,
                limit_per_character=3,
            )
            world_memory_cards = self.world_db.get_world_cards(
                novel_id=volume.novel_id,
                keywords=key_events,
                limit=8,
            )

        # 7. 生成提示词
        prompt = self.prompt_manager.generate_chapter_prompt(
            title=novel.title,
            volume_title=volume.title,
            chapter_order=chapter.order,
            chapter_title=chapter.title,
            chapter_summary=chapter_summary,
            key_events=key_events,
            character_list=character_list,
            world_data_list=world_data_list,
            previous_context=previous_context,
            character_memory_cards=character_memory_cards,
            world_memory_cards=world_memory_cards,
            style_guide=style_guide,
            word_count_min=word_count_min,
            word_count_max=word_count_max,
        )

        logger.debug(f"章节生成提示词长度: {len(prompt)} 字符")

        # 8. 调用LLM生成章节
        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.llm_client.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response["content"]
            usage = response["usage"]
            cost = response["cost"]

            logger.info(
                f"章节生成完成，Token使用: {usage['total_tokens']}, 成本: ${cost:.4f}"
            )

            return {
                "content": content,
                "usage": usage,
                "cost": cost,
            }

        except Exception as e:
            logger.error(f"章节生成失败: {e}")
            raise

    def save_chapter_content(self, chapter_id: int, content: str) -> Dict[str, Any]:
        """
        保存章节内容到数据库

        Args:
            chapter_id: 章节ID
            content: 章节内容

        Returns:
            保存结果统计信息
        """
        logger.info(f"开始保存章节 ID={chapter_id} 的内容")

        chapter = chapter_crud.get_by_id(self.session, chapter_id)
        if chapter is None:
            raise ValueError(f"章节 ID {chapter_id} 不存在")

        # 更新章节内容
        chapter_crud.update(self.session, chapter_id, content=content)

        # 更新字数统计
        chapter.update_word_count()
        self.session.flush()

        logger.info(f"章节保存完成，字数: {chapter.word_count}")

        return {
            "chapter_id": chapter_id,
            "word_count": chapter.word_count,
        }

    def generate_and_save(
        self,
        chapter_id: int,
        style_guide: str = "",
        word_count_min: int = 2000,
        word_count_max: int = 3000,
        temperature: float = 0.8,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        生成并保存章节内容（一步完成）

        Args:
            chapter_id: 章节ID
            style_guide: 写作风格指南
            word_count_min: 最小字数
            word_count_max: 最大字数
            temperature: LLM温度参数
            max_tokens: 最大生成token数

        Returns:
            包含章节内容、保存统计和token使用情况的结果
        """
        result = self.generate_chapter(
            chapter_id=chapter_id,
            style_guide=style_guide,
            word_count_min=word_count_min,
            word_count_max=word_count_max,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        stats = self.save_chapter_content(chapter_id, result["content"])

        return {
            "content": result["content"],
            "stats": stats,
            "usage": result["usage"],
            "cost": result["cost"],
        }

    def generate_context_summary(
        self, content: str, temperature: float = 0.5, max_tokens: int = 300
    ) -> str:
        """
        生成章节摘要（向后兼容接口，内部委托给 ContextCompressor）

        Args:
            content: 章节内容
            temperature: 保留参数（ContextCompressor 内部固定使用 0.3）
            max_tokens: 保留参数

        Returns:
            章节摘要
        """
        from ainovel.core.context_compressor import CompressionLevel
        return self.context_compressor._compress_single(content, CompressionLevel.DETAILED)

    def _parse_chapter_outline(self, content: str) -> tuple[str, List[str]]:
        """
        解析章节大纲，提取梗概和关键事件

        Args:
            content: 章节内容（包含大纲信息）

        Returns:
            (章节梗概, 关键事件列表)
        """
        summary = ""
        key_events = []

        lines = content.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("# 章节梗概"):
                current_section = "summary"
            elif line.startswith("# 关键事件"):
                current_section = "events"
            elif line.startswith("#"):
                current_section = None
            elif current_section == "summary" and line:
                summary += line + "\n"
            elif current_section == "events" and line.startswith("-"):
                key_events.append(line[1:].strip())

        return summary.strip() or "待补充", key_events or ["推进剧情发展"]

    def _extract_character_names(self, content: str) -> List[str]:
        """
        从章节大纲中提取涉及的角色名称

        Args:
            content: 章节内容

        Returns:
            角色名称列表
        """
        # 简单实现：从"涉及角色"部分提取
        # 实际使用中可以从大纲JSON的characters_involved字段获取
        names = []
        lines = content.split("\n")

        for line in lines:
            if "涉及角色" in line or "characters_involved" in line:
                # 提取方括号内的内容
                if "[" in line and "]" in line:
                    start = line.find("[")
                    end = line.find("]")
                    chars_str = line[start + 1 : end]
                    names = [c.strip().strip('"') for c in chars_str.split(",")]
                    break

        return names

    def _get_characters_info(
        self, novel_id: int, character_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        获取角色详细信息

        Args:
            novel_id: 小说ID
            character_names: 角色名称列表

        Returns:
            角色信息列表
        """
        if not character_names:
            # 如果未指定角色，返回所有角色
            characters = self.character_db.list_characters(novel_id, limit=10)
        else:
            # 根据名称查询角色
            characters = []
            for name in character_names:
                char = self.character_db.get_character_by_name(novel_id, name)
                if char:
                    characters.append(char)

        return [char.to_dict() for char in characters]

    def _generate_previous_context(
        self, volume_id: int, current_order: int, window_size: int
    ) -> str:
        """
        生成前情回顾（委托给 ContextCompressor）

        Args:
            volume_id: 分卷ID
            current_order: 当前章节序号
            window_size: 上下文窗口大小

        Returns:
            前情回顾文本
        """
        return self.context_compressor.build_previous_context(
            volume_id=volume_id,
            current_order=current_order,
            window_size=window_size,
        )
