"""
世界背景和角色生成器

步骤2：根据创作思路生成完整的世界背景和主要角色
"""
import json
import re
from typing import Dict, Any, List
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ainovel.llm.base import BaseLLMClient
from ainovel.core.prompt_manager import PromptManager
from ainovel.memory.character_db import CharacterDatabase
from ainovel.memory.world_db import WorldDatabase
from ainovel.memory.character import Character, MBTIType
from ainovel.memory.world_data import WorldData, WorldDataType


class WorldBuildingGenerator:
    """世界背景和角色生成器"""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        character_db: CharacterDatabase,
        world_db: WorldDatabase,
    ):
        """
        初始化生成器

        Args:
            llm_client: LLM客户端
            character_db: 角色数据库
            world_db: 世界观数据库
        """
        self.llm_client = llm_client
        self.character_db = character_db
        self.world_db = world_db
        self.prompt_manager = PromptManager()

    def generate_world_building(
        self,
        planning_content: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        生成世界背景和角色

        Args:
            planning_content: 创作思路内容（JSON字符串）
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            包含世界观和角色数据的字典
            {
                "world_building": {
                    "world_data": [...],
                    "characters": [...]
                },
                "usage": {...},
                "cost": 0.01,
                "raw_content": ""
            }
        """
        # 生成提示词
        prompt = self.prompt_manager.generate_world_building_prompt(planning_content)

        # 调用LLM
        response = self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        raw_content = response["content"]

        # 解析JSON，失败时返回空结构并标记
        world_building_data, parse_failed = self._parse_world_building(raw_content)

        return {
            "world_building": world_building_data,
            "usage": response.get("usage", {}),
            "cost": response.get("cost", 0),
            "raw_content": raw_content,
            "parse_failed": parse_failed,
        }

    def save_world_building(
        self, session: Session, novel_id: int, world_building_data: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        保存世界观和角色到数据库

        Args:
            session: 数据库会话
            novel_id: 小说ID
            world_building_data: 世界观和角色数据

        Returns:
            保存统计信息
            {
                "world_data_created": 5,
                "characters_created": 4
            }
        """
        # 清理该小说的旧角色和世界观数据，避免重复执行步骤2时数据累积
        session.execute(delete(Character).where(Character.novel_id == novel_id))
        session.execute(delete(WorldData).where(WorldData.novel_id == novel_id))

        world_data_list = world_building_data.get("world_data", [])
        character_list = world_building_data.get("characters", [])

        # 保存世界观数据
        world_count = 0
        for wd in world_data_list:
            data_type_str = wd["data_type"].upper()
            data_type = WorldDataType[data_type_str]
            properties = wd.get("properties", {})

            if data_type == WorldDataType.LOCATION:
                self.world_db.create_location(
                    novel_id=novel_id,
                    name=wd["name"],
                    description=wd["description"],
                    **properties,
                )
            elif data_type == WorldDataType.ORGANIZATION:
                self.world_db.create_organization(
                    novel_id=novel_id,
                    name=wd["name"],
                    description=wd["description"],
                    **properties,
                )
            elif data_type == WorldDataType.ITEM:
                self.world_db.create_item(
                    novel_id=novel_id,
                    name=wd["name"],
                    description=wd["description"],
                    **properties,
                )
            elif data_type == WorldDataType.RULE:
                self.world_db.create_rule(
                    novel_id=novel_id,
                    name=wd["name"],
                    description=wd["description"],
                    **properties,
                )
            world_count += 1

        # 保存角色
        char_count = 0
        for char in character_list:
            mbti_str = char["mbti"].upper()
            mbti = MBTIType[mbti_str]

            self.character_db.create_character(
                novel_id=novel_id,
                name=char["name"],
                mbti=mbti,
                background=char["background"],
                personality_traits=char.get("personality_traits", {}),
            )
            char_count += 1

        return {
            "world_data_created": world_count,
            "characters_created": char_count,
        }

    def generate_and_save(
        self,
        session: Session,
        novel_id: int,
        planning_content: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        生成并保存世界观和角色（一步完成）

        Args:
            session: 数据库会话
            novel_id: 小说ID
            planning_content: 创作思路内容
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            生成结果和保存统计
        """
        result = self.generate_world_building(
            planning_content=planning_content,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 解析失败时跳过入库，由调用方保存原始文本
        if result["parse_failed"]:
            result["stats"] = {"world_data_created": 0, "characters_created": 0}
        else:
            stats = self.save_world_building(
                session=session, novel_id=novel_id, world_building_data=result["world_building"]
            )
            result["stats"] = stats

        return result

    def _parse_world_building(self, content: str) -> tuple[Dict[str, Any], bool]:
        """
        解析LLM输出的世界观和角色JSON

        Args:
            content: LLM输出内容

        Returns:
            (world_building_data, parse_failed)
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
                return {"world_data": [], "characters": []}, True

        try:
            world_building_data = json.loads(json_str)
            return world_building_data, False
        except json.JSONDecodeError:
            return {"world_data": [], "characters": []}, True
