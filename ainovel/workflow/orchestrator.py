"""
流程编排器

管理小说创作的完整6步流程,并支持用户编辑每步结果
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ainovel.workflow.pipeline_runner import PipelineRunner

from ainovel.llm.base import BaseLLMClient
from ainovel.db.novel import WorkflowStatus
from ainovel.db.crud import novel_crud
from ainovel.workflow.generators.planning_generator import PlanningGenerator
from ainovel.workflow.generators.world_building_generator import WorldBuildingGenerator
from ainovel.workflow.generators.detail_outline_generator import DetailOutlineGenerator
from ainovel.workflow.generators.quality_check_generator import QualityCheckGenerator
from ainovel.workflow.generators.consistency_generator import ConsistencyGenerator
from ainovel.core.outline_generator import OutlineGenerator
from ainovel.core.chapter_generator import ChapterGenerator
from ainovel.memory.character_db import CharacterDatabase
from ainovel.memory.world_db import WorldDatabase
from ainovel.style.analyzer import StyleAnalyzer
from ainovel.style.applicator import StyleApplicator
from ainovel.exceptions import (
    NovelNotFoundError,
    ChapterNotFoundError,
    InsufficientDataError,
    InvalidFormatError,
)


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
        self.quality_check_gen = QualityCheckGenerator(llm_client)
        self.consistency_gen = ConsistencyGenerator(llm_client)
        self.style_analyzer = StyleAnalyzer(llm_client)

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
            raise NovelNotFoundError(novel_id)

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
            raise NovelNotFoundError(novel_id)

        # 使用用户提供的想法或小说描述
        idea = initial_idea or novel.description or ""
        if not idea:
            raise InsufficientDataError(
                "无法生成创作思路，缺少初始想法",
                missing_data="initial_idea或novel.description"
            )

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
            raise NovelNotFoundError(novel_id)

        # 验证JSON格式
        try:
            planning_data = json.loads(planning_content)
        except json.JSONDecodeError as e:
            raise InvalidFormatError("创作思路JSON", str(e))

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
            raise NovelNotFoundError(novel_id)

        if not novel.planning_content:
            raise InsufficientDataError(
                "无法生成世界观和角色，请先完成步骤1（创作思路）",
                missing_data="planning_content"
            )

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
            raise NovelNotFoundError(novel_id)

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
            raise NovelNotFoundError(novel_id)

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
        style_profile_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        步骤5：为指定章节生成内容

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            style_guide: 写作风格指南（直接传入文本，优先级最高）
            style_profile_id: 指定文风档案ID（次优先）；若两者均为None则自动加载激活档案

        Returns:
            生成结果
        """
        from ainovel.db.crud import chapter_crud

        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        novel = chapter.volume.novel

        # 按优先级确定最终使用的风格指南
        if style_guide is None:
            if style_profile_id is not None:
                style_guide = StyleApplicator.load_guide_by_id(session, style_profile_id)
            else:
                style_guide = StyleApplicator.load_active_guide(session, novel.id)

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

    def step_6_quality_check(
        self,
        session: Session,
        chapter_id: int,
    ) -> Dict[str, Any]:
        """
        步骤6：对指定章节进行质量检查

        Args:
            session: 数据库会话
            chapter_id: 章节ID

        Returns:
            检查结果
        """
        from ainovel.db.crud import chapter_crud

        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        novel = chapter.volume.novel

        result = self.quality_check_gen.check_and_save(
            session=session, chapter_id=chapter_id
        )

        # 更新小说状态（第一次质量检查时）
        if novel.current_step < 6:
            novel.workflow_status = WorkflowStatus.QUALITY_CHECK
            novel.current_step = 6
            session.commit()

        result["novel_id"] = novel.id
        result["workflow_status"] = novel.workflow_status.value
        result["chapter_id"] = chapter_id
        result["chapter_title"] = chapter.title
        return result

    def step_6_batch_quality_check(
        self, session: Session, novel_id: int
    ) -> Dict[str, Any]:
        """
        步骤6：批量检查小说所有已生成章节

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            批量检查结果
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise NovelNotFoundError(novel_id)

        result = self.quality_check_gen.batch_check(session=session, novel_id=novel_id)

        # 更新状态
        novel.workflow_status = WorkflowStatus.QUALITY_CHECK
        novel.current_step = 6
        session.commit()

        result["workflow_status"] = novel.workflow_status.value
        return result

    def check_chapter_consistency(
        self,
        session: Session,
        chapter_id: int,
        content_override: Optional[str] = None,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        检查章节一致性（不改写章节正文）

        Args:
            session: 数据库会话
            chapter_id: 章节ID
            content_override: 可选替代文本，不写入数据库
            strict: 严格模式

        Returns:
            一致性检查结果
        """
        from ainovel.db.crud import chapter_crud

        chapter = chapter_crud.get_by_id(session, chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        result = self.consistency_gen.check_chapter(
            session=session,
            chapter_id=chapter_id,
            content_override=content_override,
            strict=strict,
        )
        result["novel_id"] = chapter.volume.novel_id
        result["chapter_title"] = chapter.title
        return result

    def learn_style(
        self,
        session: Session,
        novel_id: int,
        name: str,
        source_text: str,
        set_active: bool = True,
    ) -> Dict[str, Any]:
        """
        从参考文本学习写作风格，保存为文风档案

        Args:
            session: 数据库会话
            novel_id: 关联小说ID
            name: 档案名称（如"金庸武侠风"）
            source_text: 参考文本（建议500字以上）
            set_active: 是否立即激活此档案

        Returns:
            {
                "profile_id": 1,
                "name": "...",
                "style_features": {...},
                "style_guide": "...",
                "novel_id": 1,
            }
        """
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise NovelNotFoundError(novel_id)

        result = self.style_analyzer.analyze_and_save(
            session=session,
            novel_id=novel_id,
            name=name,
            source_text=source_text,
            set_active=set_active,
        )
        result["novel_id"] = novel_id
        return result

    def list_style_profiles(self, session: Session, novel_id: int) -> Dict[str, Any]:
        """
        列出小说的所有文风档案

        Args:
            session: 数据库会话
            novel_id: 小说ID

        Returns:
            档案列表
        """
        from ainovel.db.crud import style_profile_crud

        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise NovelNotFoundError(novel_id)

        profiles = style_profile_crud.get_by_novel_id(session, novel_id)
        return {
            "novel_id": novel_id,
            "profiles": [p.to_dict() for p in profiles],
        }

    def activate_style_profile(
        self, session: Session, novel_id: int, profile_id: int
    ) -> Dict[str, Any]:
        """
        激活指定文风档案

        Args:
            session: 数据库会话
            novel_id: 小说ID
            profile_id: 要激活的档案ID

        Returns:
            激活结果
        """
        from ainovel.db.crud import style_profile_crud

        profile = style_profile_crud.set_active(session, novel_id, profile_id)
        if not profile:
            raise ValueError(f"文风档案不存在或不属于该小说: profile_id={profile_id}")
        session.commit()
        return {"novel_id": novel_id, "active_profile_id": profile_id, "name": profile.name}

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
            raise NovelNotFoundError(novel_id)

        novel.workflow_status = WorkflowStatus.COMPLETED
        session.commit()

        return {
            "novel_id": novel_id,
            "workflow_status": novel.workflow_status.value,
            "message": "小说创作流程已完成",
        }

    def run_pipeline(
        self,
        session: Session,
        novel_id: int,
        from_step: int = 3,
        to_step: int = 5,
        chapter_range: Optional[str] = None,
        regenerate: bool = False,
    ) -> Dict[str, Any]:
        """
        统一流水线入口：大纲 -> 细纲 -> 正文

        Args:
            session: 数据库会话
            novel_id: 小说ID
            from_step: 起始步骤（3=大纲, 4=细纲, 5=正文）
            to_step: 结束步骤（须 >= from_step）
            chapter_range: 章节范围，如 "1-10" 或 "1,3,5"；None 表示全部
            regenerate: 是否强制重新生成已有内容

        Returns:
            PipelineResult.to_dict()
        """
        runner = PipelineRunner(self)
        plan = {
            "from_step": from_step,
            "to_step": to_step,
            "chapter_range": chapter_range,
            "regenerate": regenerate,
        }
        return runner.run(session, novel_id, plan)

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
