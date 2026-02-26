"""
大纲生成器

根据小说基本信息、角色和世界观生成详细的小说大纲
"""
import json
import re
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
        max_tokens: int = 80000,
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

        # 5. 调用LLM生成大纲（若输出截断则自动重试一次）
        messages = [{"role": "user", "content": prompt}]
        max_attempts = 2
        current_max_tokens = max_tokens
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        total_cost = 0.0
        # 续写模式下累积的前半段内容
        accumulated_content = ""

        try:
            for attempt in range(1, max_attempts + 1):
                response = self.llm_client.generate(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=current_max_tokens,
                )

                content = response.get("content", "")
                usage = response.get("usage", {})
                cost = response.get("cost", 0.0)
                finish_reason = response.get("finish_reason")

                total_usage["input_tokens"] += usage.get("input_tokens", 0)
                total_usage["output_tokens"] += usage.get("output_tokens", 0)
                total_usage["total_tokens"] += usage.get("total_tokens", 0)
                total_cost += cost

                logger.info(
                    f"大纲生成尝试 {attempt}/{max_attempts} 完成，"
                    f"finish_reason={finish_reason}, "
                    f"累计Token={total_usage['total_tokens']}, "
                    f"累计成本=${total_cost:.4f}"
                )

                # 续写模式：先尝试直接解析新内容，失败时再尝试合并前半段
                merged_content = accumulated_content + content if accumulated_content else content
                parse_content = content if accumulated_content else content

                # 6. 解析大纲JSON：优先解析本次返回，失败时尝试合并内容
                outline_data, parse_failed = self._parse_outline(parse_content)
                if parse_failed and accumulated_content:
                    outline_data, parse_failed = self._parse_outline(merged_content)
                if not parse_failed:
                    return {
                        "outline": outline_data,
                        "usage": total_usage,
                        "cost": total_cost,
                        "raw_content": merged_content,
                        "parse_failed": False,
                        "finish_reason": finish_reason,
                    }

                is_truncated = finish_reason == "length"
                if is_truncated and attempt < max_attempts:
                    current_max_tokens = min(current_max_tokens * 2, 12000)
                    accumulated_content = merged_content
                    # 重试时只发简洁指令，避免重复原始 prompt 导致输入 token 翻倍
                    messages = [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": content},
                        {
                            "role": "user",
                            "content": (
                                "你的输出被截断了，请继续补全剩余内容，"
                                "直接从上次截断处续写，保持JSON格式完整，"
                                "不要重复已输出的内容，不要输出解释文字。"
                            ),
                        },
                    ]
                    logger.warning(
                        "检测到大纲输出被截断（finish_reason=length），"
                        f"准备重试（max_tokens={current_max_tokens}）"
                    )
                    continue

                return {
                    "outline": outline_data,
                    "usage": total_usage,
                    "cost": total_cost,
                    "raw_content": merged_content,
                    "parse_failed": True,
                    "finish_reason": finish_reason,
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
        max_tokens: int = 80000,
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
        json_str = self._extract_json_candidate(content)
        if not json_str:
            return {"volumes": []}, True

        # 大概率是输出截断，直接返回失败并留给上层重试
        if json_str.count("{") > json_str.count("}"):
            logger.warning("大纲输出疑似被截断：JSON大括号未闭合")
            return {"volumes": []}, True

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

    def _extract_json_candidate(self, content: str) -> str:
        """从LLM输出中提取最可能的JSON字符串（支持未闭合代码块）。"""
        text = (content or "").strip()
        if not text:
            return ""

        # 优先提取 ```json ... ```；若代码块未闭合，则提取到文本末尾
        match = re.search(r"```(?:json)?\s*([\s\S]*?)(?:```|$)", text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate

        # 回退到首尾花括号包围内容
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1].strip()
        if start != -1:
            return text[start:].strip()
        return text
