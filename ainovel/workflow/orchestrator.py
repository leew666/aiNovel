"""
流程编排器

管理小说创作的完整6步流程,并支持用户编辑每步结果
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ainovel.llm.base import BaseLLMClient
from ainovel.db.novel import WorkflowStatus
from ainovel.db.crud import novel_crud
from ainovel.workflow.generators.planning_generator import PlanningGenerator
from ainovel.workflow.generators.world_building_generator import WorldBuildingGenerator
from ainovel.workflow.generators.detail_outline_generator import DetailOutlineGenerator
from ainovel.core.outline_generator import OutlineGenerator
from ainovel.core.chapter_generator import ChapterGenerator
from ainovel.memory.character_db import CharacterDatabase
from ainovel.memory.world_db import WorldDatabase


class WorkflowOrchestrator:
    """流程编排器"""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        character_db: CharacterDatabase,
        world_db: WorldDatabase,
    ):
        """
        初始化编排器

        Args:
            llm_client: LLM客户端
            character_db: 角色数据库
            world_db: 世界观数据库
        """
        self.llm_client = llm_client
        self.character_db = character_db
        self.world_db = world_db

        # 初始化不需要session的生成器
        self.planning_gen = PlanningGenerator(llm_client)
        self.world_building_gen = WorldBuildingGenerator(llm_client, character_db, world_db)
        self.detail_outline_gen = DetailOutlineGenerator(llm_client)

    def get_workflow_status(self, session: Session, novel_id: int) -> Dict[str, Any]:
        """
        获取小说的工作流状态

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            状态信息
            {
                "novel_id": 1,
                "workflow_status": "planning",
                "current_step": 1,
                "can_continue": true
            }
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        return {
            "novel_id": novel.id,
            "workflow_status": novel.workflow_status.value,
            "current_step": novel.current_step,
            "can_continue": self._can_continue_to_next_step(novel),
        }

    def step_1_planning(
        self,
        session: Session,
        novel_id: int,
        initial_idea: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        步骤1：生成创作思路

        Args:
            session: 数据库会话
            novel_id: 小说ID
            initial_idea: 用户的初始想法（如果为None，则使用novel.description）

        Returns:
            生成结果
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        # 使用用户提供的想法或小说描述
        idea = initial_idea or novel.description or ""
        if not idea:
            raise ValueError("请提供初始想法或在小说描述中填写")

        # 生成创作思路
        result = self.planning_gen.generate_planning(initial_idea=idea)

        # 保存到数据库
        planning_json = json.dumps(result["planning"], ensure_ascii=False, indent=2)
        novel.planning_content = planning_json
        novel.workflow_status = WorkflowStatus.PLANNING
        novel.current_step = 1
        session.commit()

        result["novel_id"] = novel_id
        result["workflow_status"] = novel.workflow_status.value
        return result

    def step_1_update(
        self, session: Session, novel_id: int, planning_content: str
    ) -> Dict[str, Any]:
        """
        步骤1：用户编辑创作思路后更新

        Args:
            session: 数据库会话
            novel_id: 小说ID
            planning_content: 用户编辑后的创作思路（JSON字符串）

        Returns:
            更新结果
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        # 验证JSON格式
        try:
            planning_data = json.loads(planning_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"创作思路格式错误: {e}")

        novel.planning_content = planning_content
        session.commit()

        return {
            "novel_id": novel_id,
            "planning": planning_data,
            "message": "创作思路已更新",
        }

    def step_2_world_building(
        self, session: Session, novel_id: int
    ) -> Dict[str, Any]:
        """
        步骤2：生成世界背景和角色

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            生成结果
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        if not novel.planning_content:
            raise ValueError("请先完成步骤1（创作思路）")

        # 生成并保存世界观和角色
        result = self.world_building_gen.generate_and_save(
            session=session,
            novel_id=novel_id,
            planning_content=novel.planning_content,
        )

        # 更新状态
        novel.workflow_status = WorkflowStatus.WORLD_BUILDING
        novel.current_step = 2
        session.commit()

        result["novel_id"] = novel_id
        result["workflow_status"] = novel.workflow_status.value
        return result

    def step_3_outline(self, session: Session, novel_id: int) -> Dict[str, Any]:
        """
        步骤3：生成作品大纲

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            生成结果
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        # 创建OutlineGenerator实例（需要session）
        outline_gen = OutlineGenerator(self.llm_client, session)

        # 生成并保存大纲
        result = outline_gen.generate_and_save(novel_id=novel_id)

        # 更新状态
        novel.workflow_status = WorkflowStatus.OUTLINE
        novel.current_step = 3
        session.commit()

        result["novel_id"] = novel_id
        result["workflow_status"] = novel.workflow_status.value
        return result

    def step_4_detail_outline(
        self, session: Session, chapter_id: int
    ) -> Dict[str, Any]:
        """
        步骤4：为指定章节生成详细细纲

        Args:
            session: 数据库会话
            chapter_id: 章节ID

        Returns:
            生成结果
        """
        from ainovel.db.crud import chapter_crud

        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        novel = chapter.volume.novel

        # 生成并保存细纲
        result = self.detail_outline_gen.generate_and_save(
            session=session, chapter_id=chapter_id
        )

        # 更新小说状态（第一次生成细纲时）
        if novel.current_step < 4:
            novel.workflow_status = WorkflowStatus.DETAIL_OUTLINE
            novel.current_step = 4
            session.commit()

        result["novel_id"] = novel.id
        result["workflow_status"] = novel.workflow_status.value
        return result

    def step_4_batch_detail_outline(
        self, session: Session, novel_id: int
    ) -> Dict[str, Any]:
        """
        步骤4：为所有章节批量生成详细细纲

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            生成结果
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        # 获取所有章节
        all_chapters = []
        for volume in novel.volumes:
            all_chapters.extend(volume.chapters)

        if not all_chapters:
            raise ValueError("没有章节可生成细纲")

        results = []
        for chapter in all_chapters:
            try:
                result = self.detail_outline_gen.generate_and_save(
                    session=session, chapter_id=chapter.id
                )
                results.append(
                    {
                        "chapter_id": chapter.id,
                        "chapter_title": chapter.title,
                        "success": True,
                        "scenes_count": result["stats"]["scenes_count"],
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "chapter_id": chapter.id,
                        "chapter_title": chapter.title,
                        "success": False,
                        "error": str(e),
                    }
                )

        # 更新状态
        novel.workflow_status = WorkflowStatus.DETAIL_OUTLINE
        novel.current_step = 4
        session.commit()

        return {
            "novel_id": novel_id,
            "workflow_status": novel.workflow_status.value,
            "total_chapters": len(all_chapters),
            "results": results,
        }

    def step_5_writing(
        self,
        session: Session,
        chapter_id: int,
        style_guide: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        步骤5：为指定章节生成内容

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            style_guide: 写作风格指南

        Returns:
            生成结果
        """
        from ainovel.db.crud import chapter_crud

        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        novel = chapter.volume.novel

        # 创建ChapterGenerator实例（需要session）
        chapter_gen = ChapterGenerator(self.llm_client, session)

        # 生成并保存章节内容
        result = chapter_gen.generate_and_save(
            chapter_id=chapter_id, style_guide=style_guide
        )

        # 更新小说状态（第一次生成内容时）
        if novel.current_step < 5:
            novel.workflow_status = WorkflowStatus.WRITING
            novel.current_step = 5
            session.commit()

        result["novel_id"] = novel.id
        result["workflow_status"] = novel.workflow_status.value
        return result

    def mark_completed(self, session: Session, novel_id: int) -> Dict[str, Any]:
        """
        标记小说创作完成

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            结果信息
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise ValueError(f"小说不存在: {novel_id}")

        novel.workflow_status = WorkflowStatus.COMPLETED
        session.commit()

        return {
            "novel_id": novel_id,
            "workflow_status": novel.workflow_status.value,
            "message": "小说创作流程已完成",
        }

    def _can_continue_to_next_step(self, novel) -> bool:
        """检查是否可以继续到下一步"""
        current_step = novel.current_step

        if current_step == 0:
            return True  # 可以开始步骤1
        elif current_step == 1:
            return novel.planning_content is not None
        elif current_step == 2:
            # 检查是否有角色和世界观数据
            return len(novel.volumes) == 0  # 还没生成大纲，可以继续
        elif current_step == 3:
            return len(novel.volumes) > 0  # 已有大纲，可以继续
        elif current_step == 4:
            return True  # 可以继续写作
        elif current_step == 5:
            return True  # 可以标记完成
        else:
            return False
