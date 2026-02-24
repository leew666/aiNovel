"""
CharacterDatabase 服务类

提供角色管理的业务逻辑封装
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ainovel.memory.character import Character, MBTIType
from ainovel.memory.crud import character_crud


class CharacterDatabase:
    """角色数据库服务类"""

    def __init__(self, session: Session):
        """
        初始化角色数据库

        Args:
            session: 数据库会话
        """
        self.session = session

    def create_character(
        self,
        novel_id: int,
        name: str,
        mbti: MBTIType,
        background: str,
        personality_traits: Dict[str, int] | None = None,
    ) -> Character:
        """
        创建角色

        Args:
            novel_id: 小说 ID
            name: 角色名称
            mbti: MBTI 人格类型
            background: 背景故事
            personality_traits: 性格特征（可选）

        Returns:
            创建的角色实例
        """
        character = character_crud.create(
            self.session,
            novel_id=novel_id,
            name=name,
            mbti=mbti,
            background=background,
            personality_traits=personality_traits or {},
            memories=[],
            relationships={},
        )
        return character

    def get_character(self, character_id: int) -> Optional[Character]:
        """
        根据 ID 获取角色

        Args:
            character_id: 角色 ID

        Returns:
            角色实例，不存在则返回 None
        """
        return character_crud.get_by_id(self.session, character_id)

    def get_character_by_name(self, novel_id: int, name: str) -> Optional[Character]:
        """
        根据名称获取角色

        Args:
            novel_id: 小说 ID
            name: 角色名称

        Returns:
            角色实例，不存在则返回 None
        """
        return character_crud.get_by_name(self.session, novel_id, name)

    def list_characters(self, novel_id: int, skip: int = 0, limit: int = 100) -> List[Character]:
        """
        列出小说的所有角色

        Args:
            novel_id: 小说 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            角色列表
        """
        return character_crud.get_by_novel_id(self.session, novel_id, skip, limit)

    def list_characters_by_mbti(
        self, novel_id: int, mbti: MBTIType, skip: int = 0, limit: int = 100
    ) -> List[Character]:
        """
        列出指定 MBTI 类型的角色

        Args:
            novel_id: 小说 ID
            mbti: MBTI 人格类型
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            角色列表
        """
        return character_crud.get_by_mbti(self.session, novel_id, mbti, skip, limit)

    def search_characters(
        self, novel_id: int, keyword: str, skip: int = 0, limit: int = 100
    ) -> List[Character]:
        """
        搜索角色

        Args:
            novel_id: 小说 ID
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            角色列表
        """
        return character_crud.search_by_name(self.session, novel_id, keyword, skip, limit)

    def add_memory(
        self,
        character_id: int,
        event: str,
        content: str,
        chapter_id: int | None = None,
        volume_id: int | None = None,
        importance: str = "medium",
    ) -> Character:
        """
        为角色添加记忆

        Args:
            character_id: 角色 ID
            event: 事件名称
            content: 记忆内容
            chapter_id: 发生在哪一章（可选）
            volume_id: 发生在哪一卷（可选）
            importance: 重要性（high/medium/low）

        Returns:
            更新后的角色实例

        Raises:
            ValueError: 如果角色不存在
        """
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")

        character.add_memory(event, content, chapter_id, volume_id, importance)
        self.session.flush()
        return character

    def add_relationship(
        self,
        character_id: int,
        target_character_name: str,
        relation_type: str,
        intimacy: int = 5,
        first_met_chapter: int | None = None,
        notes: str = "",
    ) -> Character:
        """
        为角色添加关系

        Args:
            character_id: 角色 ID
            target_character_name: 关联角色名称
            relation_type: 关系类型
            intimacy: 亲密度（1-10）
            first_met_chapter: 初次相遇的章节
            notes: 备注

        Returns:
            更新后的角色实例

        Raises:
            ValueError: 如果角色不存在
        """
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")

        character.add_relationship(
            target_character_name, relation_type, intimacy, first_met_chapter, notes
        )
        self.session.flush()
        return character

    def update_personality_trait(
        self, character_id: int, trait_name: str, value: int
    ) -> Character:
        """
        更新角色的性格特征

        Args:
            character_id: 角色 ID
            trait_name: 特征名称
            value: 特征值（1-10）

        Returns:
            更新后的角色实例

        Raises:
            ValueError: 如果角色不存在
        """
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")

        character.update_personality_trait(trait_name, value)
        self.session.flush()
        return character

    def get_character_memories(
        self, character_id: int, importance: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        获取角色的记忆列表

        Args:
            character_id: 角色 ID
            importance: 重要性筛选（可选：high/medium/low）

        Returns:
            记忆列表

        Raises:
            ValueError: 如果角色不存在
        """
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")

        memories = character.memories or []

        if importance:
            memories = [m for m in memories if m.get("importance") == importance]

        return memories

    def get_character_relationships(self, character_id: int) -> Dict[str, Dict[str, Any]]:
        """
        获取角色的关系网络

        Args:
            character_id: 角色 ID

        Returns:
            关系网络字典

        Raises:
            ValueError: 如果角色不存在
        """
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")

        return character.relationships or {}

    def delete_character(self, character_id: int) -> bool:
        """
        删除角色

        Args:
            character_id: 角色 ID

        Returns:
            删除成功返回 True，角色不存在返回 False
        """
        return character_crud.delete(self.session, character_id)

    def update_character(self, character_id: int, **kwargs) -> Character:
        """
        通用更新接口，支持更新任意角色字段

        Args:
            character_id: 角色 ID
            **kwargs: 要更新的字段和值（支持 name/background/mbti/personality_traits/
                      current_mood/current_status/goals/catchphrases）

        Returns:
            更新后的角色实例

        Raises:
            ValueError: 如果角色不存在
        """
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")

        allowed = {"name", "background", "mbti", "personality_traits",
                   "current_mood", "current_status", "goals", "catchphrases"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(character, key, value)

        self.session.flush()
        return character

    def update_mood(self, character_id: int, mood: str) -> Character:
        """更新角色当前心情"""
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")
        character.update_mood(mood)
        self.session.flush()
        return character

    def update_status(self, character_id: int, status: str) -> Character:
        """更新角色最近发生的事"""
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")
        character.update_status(status)
        self.session.flush()
        return character

    def update_goals(self, character_id: int, goals: str) -> Character:
        """更新角色当前目标"""
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")
        character.update_goals(goals)
        self.session.flush()
        return character

    def add_catchphrase(self, character_id: int, phrase: str) -> Character:
        """为角色添加口头禅"""
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")
        character.add_catchphrase(phrase)
        self.session.flush()
        return character

    def remove_catchphrase(self, character_id: int, phrase: str) -> Character:
        """删除角色口头禅"""
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"角色 ID {character_id} 不存在")
        character.remove_catchphrase(phrase)
        self.session.flush()
        return character
