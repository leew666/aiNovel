"""
大纲生成器

根据小说基本信息、角色和世界观生成详细的小说大纲
"""
import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from ainovel.llm import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.db import novel_crud, volume_crud, chapter_crud
from ainovel.db.novel import Novel
from ainovel.memory import CharacterDatabase, WorldDatabase
from ainovel.exceptions import NovelNotFoundError, InsufficientDataError, JSONParseError


class OutlineGenerator:
    """大纲生成器"""

    def __init__(self, llm_client: BaseLLMClient, session: Session):
        """
        初始化大纲生成器

        Args:
            llm_client: LLM客户端
            session: 数据库会话
        """
        self.llm_client = llm_client
        self.session = session
        self.prompt_manager = PromptManager()
        self.character_db = CharacterDatabase(session)
        self.world_db = WorldDatabase(session)

    def generate_outline(
        self,
        novel_id: int,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        生成小说大纲

        Args:
            novel_id: 小说ID
            temperature: LLM温度参数
            max_tokens: 最大生成token数

        Returns:
            生成结果，包含大纲数据和token使用情况

        Raises:
            ValueError: 如果小说不存在或数据不足
        """
        logger.info(f"开始为小说 ID={novel_id} 生成大纲")

        # 1. 获取小说信息
        novel = novel_crud.get_by_id(self.session, novel_id)
        if novel is None:
            raise NovelNotFoundError(novel_id)

        # 2. 获取角色和世界观数据
        characters = self.character_db.list_characters(novel_id)
        world_data = self.world_db.list_all(novel_id)

        if not characters:
            raise InsufficientDataError(
                f"小说 ID {novel_id} 尚未创建角色，无法生成大纲",
                missing_data="characters"
            )

        # 3. 转换为字典格式
        character_list = [char.to_dict() for char in characters]
        world_data_list = [data.to_dict() for data in world_data]

        # 4. 生成提示词
        prompt = self.prompt_manager.generate_outline_prompt(
            title=novel.title,
            description=novel.description or "待补充",
            author=novel.author or "佚名",
            world_data_list=world_data_list,
            character_list=character_list,
        )

        logger.debug(f"大纲生成提示词长度: {len(prompt)} 字符")

        # 5. 调用LLM生成大纲
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
                f"大纲生成完成，Token使用: {usage['total_tokens']}, 成本: ${cost:.4f}"
            )

            # 6. 解析大纲JSON
            outline_data, parse_failed = self._parse_outline(content)

            return {
                "outline": outline_data,
                "usage": usage,
                "cost": cost,
                "raw_content": content,
                "parse_failed": parse_failed,
            }

        except Exception as e:
            logger.error(f"大纲生成失败: {e}")
            raise

    def save_outline(
        self, novel_id: int, outline_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        保存大纲到数据库

        Args:
            novel_id: 小说ID
            outline_data: 大纲数据

        Returns:
            保存结果统计信息

        Raises:
            ValueError: 如果数据格式错误
        """
        logger.info(f"开始保存小说 ID={novel_id} 的大纲")

        volumes = outline_data.get("volumes", [])
        if not volumes:
            raise ValueError("大纲数据为空，无法保存")

        stats = {"volumes_created": 0, "chapters_created": 0}

        for volume_data in volumes:
            # 创建分卷
            volume = volume_crud.create(
                self.session,
                novel_id=novel_id,
                title=volume_data["title"],
                order=volume_data["order"],
                description=volume_data.get("description", ""),
            )
            stats["volumes_created"] += 1

            # 创建章节
            for chapter_data in volume_data.get("chapters", []):
                chapter_crud.create(
                    self.session,
                    volume_id=volume.id,
                    title=chapter_data["title"],
                    order=chapter_data["order"],
                    content=f"# 章节梗概\n{chapter_data.get('summary', '')}\n\n"
                    f"# 关键事件\n"
                    + "\n".join([f"- {e}" for e in chapter_data.get("key_events", [])]),
                )
                stats["chapters_created"] += 1

        self.session.flush()
        logger.info(
            f"大纲保存完成: {stats['volumes_created']} 个分卷, "
            f"{stats['chapters_created']} 个章节"
        )

        return stats

    def generate_and_save(
        self,
        novel_id: int,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        生成并保存大纲（一步完成）

        Args:
            novel_id: 小说ID
            temperature: LLM温度参数
            max_tokens: 最大生成token数

        Returns:
            包含大纲数据、保存统计和token使用情况的结果
        """
        result = self.generate_outline(novel_id, temperature, max_tokens)

        if result["parse_failed"]:
            # 解析失败时保存原始文本到 novel.outline_raw，跳过入库
            novel = novel_crud.get_by_id(self.session, novel_id)
            if novel:
                novel.outline_raw = result["raw_content"]
                self.session.commit()
            return {
                "outline": result["outline"],
                "stats": {"volumes_created": 0, "chapters_created": 0},
                "usage": result["usage"],
                "cost": result["cost"],
                "raw_content": result["raw_content"],
                "parse_failed": True,
            }

        stats = self.save_outline(novel_id, result["outline"])

        return {
            "outline": result["outline"],
            "stats": stats,
            "usage": result["usage"],
            "cost": result["cost"],
            "raw_content": result["raw_content"],
            "parse_failed": False,
        }

    def _parse_outline(self, content: str) -> tuple[Dict[str, Any], bool]:
        """
        解析LLM生成的大纲JSON

        Returns:
            (outline_data, parse_failed)
            解析失败时返回空结构和 parse_failed=True，不抛异常
        """
        # 尝试从代码块中提取JSON
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            json_str = content.strip()

        try:
            data = json.loads(json_str)

            if "volumes" not in data:
                return {"volumes": []}, True

            for volume in data["volumes"]:
                if "title" not in volume or "order" not in volume:
                    return {"volumes": []}, True
                if "chapters" not in volume:
                    volume["chapters"] = []
                for chapter in volume["chapters"]:
                    if "title" not in chapter or "order" not in chapter:
                        return {"volumes": []}, True

            return data, False

        except json.JSONDecodeError as e:
            logger.error(f"大纲JSON解析失败: {e}\n内容: {json_str[:200]}")
            return {"volumes": []}, True
