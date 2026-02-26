"""
工作流路由

提供6步创作流程的 API 接口
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel

from ainovel.web.dependencies import SessionDep, OrchestratorDep
from ainovel.web.schemas.workflow import *
from ainovel.db.crud import novel_crud, chapter_crud

router = APIRouter()

# 进程内全流程任务状态追踪
# { novel_id: { "phase": str, "error": str|None, "done": bool } }
_full_run_tasks: dict[int, dict] = {}


class FullRunRequest(BaseModel):
    """一键全流程生成请求"""
    initial_idea: Optional[str] = None


def _build_status_html(novel_id: int, workflow_status: str, phase: str, error: Optional[str], done: bool) -> str:
    """构建全流程状态 HTML 片段"""
    status_order = [
        "created", "planning", "world_building", "outline",
        "detail_outline", "writing", "quality_check", "completed",
    ]
    try:
        idx = status_order.index(workflow_status)
    except ValueError:
        idx = 0

    # 每步配置：(步骤编号, 显示名称, 该步骤变为 active 时的 idx)
    steps_cfg = [
        (1, "创作思路", 1),
        (2, "世界观角色", 2),
        (3, "生成大纲", 3),
        (4, "批量细纲", 4),
        (5, "章节正文", 5),
    ]

    step_parts = []
    for num, label, active_idx in steps_cfg:
        if idx > active_idx:
            icon, color = "✓", "#27ae60"
        elif idx == active_idx:
            icon, color = "⟳", "#3498db"
        else:
            icon, color = str(num), "#95a5a6"

        step_parts.append(
            f'<div style="text-align:center;flex-shrink:0;">'
            f'<div style="width:32px;height:32px;border-radius:50%;background:{color};color:white;'
            f'display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:13px;'
            f'margin:0 auto 4px;">{icon}</div>'
            f'<div style="font-size:11px;color:{color};">{label}</div>'
            f'</div>'
        )
        if num < 5:
            line_color = "#27ae60" if idx > active_idx else "#ddd"
            step_parts.append(
                f'<div style="flex:1;height:2px;background:{line_color};'
                f'margin:0 4px 16px;border-radius:1px;"></div>'
            )

    steps_html = "".join(step_parts)
    indicator = f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">{steps_html}</div>'

    if workflow_status == "completed" or (done and not error):
        return (
            f'<div id="full-run-area" class="card" style="border-left:4px solid #27ae60;">'
            f'<h3 style="color:#27ae60;margin-bottom:12px;">✓ 全部步骤已完成</h3>'
            f'{indicator}'
            f'<p style="color:#7f8c8d;font-size:13px;margin-bottom:12px;">创作流程已全部完成，可进入章节编辑器查看结果。</p>'
            f'<a href="/novels/editor/{novel_id}" class="btn">进入章节编辑器 →</a>'
            f'</div>'
        )

    if error:
        safe_error = str(error).replace("<", "&lt;").replace(">", "&gt;")
        return (
            f'<div id="full-run-area" class="card" style="border-left:4px solid #e74c3c;">'
            f'<h3 style="color:#e74c3c;margin-bottom:12px;">✗ 生成失败</h3>'
            f'{indicator}'
            f'<p style="background:#fdf0f0;padding:10px;border-radius:6px;font-size:13px;color:#c0392b;">{safe_error}</p>'
            f'<button hx-post="/workflow/{novel_id}/full-run" hx-target="#full-run-area" '
            f'hx-swap="outerHTML" hx-ext="json-enc" class="btn" style="margin-top:10px;background:#e74c3c;">重试</button>'
            f'</div>'
        )

    # 运行中：包含 HTMX 轮询属性，每 2 秒刷新
    return (
        f'<div id="full-run-area" class="card" '
        f'hx-get="/workflow/{novel_id}/full-run-status-html" '
        f'hx-trigger="every 2s" hx-swap="outerHTML">'
        f'<h3 style="margin-bottom:12px;">⚙ 自动生成中...</h3>'
        f'{indicator}'
        f'<p style="color:#3498db;font-size:13px;">当前阶段：{phase}</p>'
        f'</div>'
    )


async def _run_full_workflow(novel_id: int, initial_idea: Optional[str]) -> None:
    """后台协程：依次执行全部6步工作流"""
    from ainovel.web.dependencies import get_database, get_llm_client
    from ainovel.memory.character_db import CharacterDatabase
    from ainovel.memory.world_db import WorldDatabase
    from ainovel.workflow.orchestrator import WorkflowOrchestrator

    db = get_database()
    try:
        with db.session_scope() as session:
            llm_client = get_llm_client()
            orch = WorkflowOrchestrator(
                llm_client,
                CharacterDatabase(session),
                WorldDatabase(session),
            )

            _full_run_tasks[novel_id]["phase"] = "步骤1：生成创作思路"
            await asyncio.to_thread(orch.step_1_planning, session, novel_id, initial_idea)

            _full_run_tasks[novel_id]["phase"] = "步骤2：生成世界观和角色"
            await asyncio.to_thread(orch.step_2_world_building, session, novel_id)

            _full_run_tasks[novel_id]["phase"] = "步骤3~5：生成大纲、细纲和章节正文（耗时较长）"
            await asyncio.to_thread(
                orch.run_pipeline,
                session=session,
                novel_id=novel_id,
                from_step=3,
                to_step=5,
                max_workers=1,
            )

            _full_run_tasks[novel_id]["phase"] = "标记完成"
            await asyncio.to_thread(orch.mark_completed, session, novel_id)

            _full_run_tasks[novel_id] = {"phase": "已完成", "error": None, "done": True}
    except Exception as exc:
        _full_run_tasks[novel_id] = {"phase": "失败", "error": str(exc), "done": True}


@router.post("/{novel_id}/full-run", response_class=HTMLResponse)
async def full_run(
    novel_id: int,
    request_data: FullRunRequest,
    session: SessionDep,
) -> HTMLResponse:
    """一键全流程生成：后台依次执行步骤1→2→3→4→5→完成，立即返回状态 HTML"""
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail=f"小说不存在: {novel_id}")

    # 已完成则直接返回完成状态，不重新启动
    if novel.workflow_status.value == "completed":
        html = _build_status_html(novel_id, "completed", "已完成", None, True)
        return HTMLResponse(content=html)

    # 已有运行中任务则直接返回当前状态
    task = _full_run_tasks.get(novel_id)
    if task and not task["done"]:
        html = _build_status_html(novel_id, novel.workflow_status.value, task["phase"], task["error"], task["done"])
        return HTMLResponse(content=html)

    initial_idea = request_data.initial_idea or novel.description or ""
    _full_run_tasks[novel_id] = {"phase": "启动中...", "error": None, "done": False}
    asyncio.create_task(_run_full_workflow(novel_id, initial_idea))

    html = _build_status_html(novel_id, novel.workflow_status.value, "启动中...", None, False)
    return HTMLResponse(content=html)


@router.get("/{novel_id}/full-run-status-html", response_class=HTMLResponse)
async def full_run_status_html(novel_id: int, session: SessionDep) -> HTMLResponse:
    """轮询端点：返回当前全流程状态的 HTML 片段"""
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail=f"小说不存在: {novel_id}")

    task = _full_run_tasks.get(novel_id)
    if not task:
        # 无运行记录但已完成（服务器重启后），仍能正确显示完成状态
        html = _build_status_html(novel_id, novel.workflow_status.value, "", None, True)
        return HTMLResponse(content=html)

    html = _build_status_html(novel_id, novel.workflow_status.value, task["phase"], task["error"], task["done"])
    return HTMLResponse(content=html)


@router.get("/{novel_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """获取工作流状态"""
    try:
        result = orch.get_workflow_status(session, novel_id)
        return WorkflowStatusResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{novel_id}/step1", response_model=Step1Response)
async def step1_planning(
    novel_id: int,
    request_data: Step1Request,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """步骤1：生成创作思路"""
    try:
        result = await asyncio.to_thread(orch.step_1_planning, session, novel_id, request_data.initial_idea)
        return Step1Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{novel_id}/step1", response_model=dict)
async def step1_update(
    novel_id: int,
    request_data: Step1UpdateRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """步骤1：用户编辑创作思路"""
    try:
        result = orch.step_1_update(session, novel_id, request_data.planning_content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/step2", response_model=Step2Response)
async def step2_world_building(
    novel_id: int, session: SessionDep, orch: OrchestratorDep
):
    """步骤2：生成世界观和角色"""
    try:
        result = await asyncio.to_thread(orch.step_2_world_building, session, novel_id)
        return Step2Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{novel_id}/step2", response_model=dict)
async def step2_update(
    novel_id: int,
    request_data: Step2UpdateRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """步骤2：用户手动输入世界观内容"""
    try:
        result = orch.step_2_update(session, novel_id, request_data.world_building_content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/step3", response_model=Step3Response)
async def step3_outline(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤3：生成大纲"""
    try:
        result = await asyncio.to_thread(orch.step_3_outline, session, novel_id)
        return Step3Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/step4", response_model=Step4Response)
async def step4_detail_outline(chapter_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤4：生成详细细纲（单章节）"""
    try:
        result = await asyncio.to_thread(orch.step_4_detail_outline, session, chapter_id)
        return Step4Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/step4/batch", response_model=Step4BatchResponse)
async def step4_batch(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤4：批量生成所有章节细纲"""
    try:
        result = await asyncio.to_thread(orch.step_4_batch_detail_outline, session, novel_id)
        return Step4BatchResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/step5", response_model=Step5Response)
async def step5_writing(
    chapter_id: int,
    request_data: Step5Request,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """步骤5：生成章节内容"""
    try:
        result = await asyncio.to_thread(
            orch.step_5_writing,
            session,
            chapter_id,
            request_data.style_guide,
            authors_note=request_data.authors_note,
        )
        return Step5Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/step6", response_model=Step6Response)
async def step6_quality_check(chapter_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤6：质量检查（单章节）"""
    try:
        result = await asyncio.to_thread(orch.step_6_quality_check, session, chapter_id)
        return Step6Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/consistency-check", response_model=ConsistencyCheckResponse)
async def consistency_check(
    chapter_id: int,
    request_data: ConsistencyCheckRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """章节一致性检查（角色/世界观/时间线）"""
    try:
        result = await asyncio.to_thread(
            orch.check_chapter_consistency,
            session=session,
            chapter_id=chapter_id,
            content_override=request_data.content_override,
            strict=request_data.strict,
        )
        return ConsistencyCheckResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/rewrite", response_model=ChapterRewriteResponse)
async def rewrite_chapter(
    chapter_id: int,
    request_data: ChapterRewriteRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """章节局部改写/重写"""
    try:
        result = await asyncio.to_thread(
            orch.rewrite_chapter,
            session=session,
            chapter_id=chapter_id,
            instruction=request_data.instruction,
            target_scope=request_data.target_scope,
            range_start=request_data.range_start,
            range_end=request_data.range_end,
            preserve_plot=request_data.preserve_plot,
            rewrite_mode=request_data.rewrite_mode,
            save=request_data.save,
        )
        return ChapterRewriteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/rewrite/rollback", response_model=ChapterRollbackResponse)
async def rollback_rewrite(
    chapter_id: int,
    request_data: ChapterRollbackRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """章节改写回滚到历史版本"""
    try:
        result = await asyncio.to_thread(
            orch.rollback_chapter_rewrite,
            session=session,
            chapter_id=chapter_id,
            history_id=request_data.history_id,
            save=request_data.save,
        )
        return ChapterRollbackResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/step6/batch", response_model=Step6BatchResponse)
async def step6_batch(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤6：批量质量检查所有已生成章节"""
    try:
        result = await asyncio.to_thread(orch.step_6_batch_quality_check, session, novel_id)
        return Step6BatchResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/complete", response_model=dict)
async def mark_completed(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """标记小说创作完成"""
    try:
        result = orch.mark_completed(session, novel_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/pipeline/run", response_model=PipelineRunResponse)
async def pipeline_run(
    novel_id: int,
    request_data: PipelineRunRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """
    流水线批量运行：大纲 -> 细纲 -> 正文

    支持从任意合法步骤恢复，某章节失败不阻塞整体。
    """
    try:
        result = await asyncio.to_thread(
            orch.run_pipeline,
            session=session,
            novel_id=novel_id,
            from_step=request_data.from_step,
            to_step=request_data.to_step,
            chapter_range=request_data.chapter_range,
            regenerate=request_data.regenerate,
            max_workers=request_data.max_workers,
        )
        return PipelineRunResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{novel_id}/pipeline/status", response_model=dict)
async def pipeline_status(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """
    查询流水线当前状态：已完成章节数、待处理章节数、失败章节列表。
    """
    try:
        novel = novel_crud.get_by_id(session, novel_id)
        if not novel:
            raise HTTPException(status_code=404, detail=f"小说不存在: {novel_id}")

        all_chapters = []
        for volume in sorted(novel.volumes, key=lambda v: v.order):
            all_chapters.extend(sorted(volume.chapters, key=lambda c: c.order))

        chapters_with_outline = [c for c in all_chapters if c.detail_outline is not None]
        chapters_with_content = [c for c in all_chapters if c.content]
        chapters_missing_outline = [
            {"chapter_id": c.id, "chapter_title": c.title}
            for c in all_chapters
            if c.detail_outline is None
        ]
        chapters_missing_content = [
            {"chapter_id": c.id, "chapter_title": c.title}
            for c in all_chapters
            if not c.content
        ]

        return {
            "novel_id": novel_id,
            "workflow_status": novel.workflow_status.value,
            "current_step": novel.current_step,
            "total_chapters": len(all_chapters),
            "chapters_with_outline": len(chapters_with_outline),
            "chapters_with_content": len(chapters_with_content),
            "missing_outline": chapters_missing_outline,
            "missing_content": chapters_missing_content,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 章节编辑器辅助 API ============


class OutlineUpdateRequest(BaseModel):
    detail_outline: str


@router.get("/chapter/{chapter_id}/content")
async def get_chapter_content(chapter_id: int, session: SessionDep):
    """获取章节细纲和正文内容（供章节编辑器加载）"""
    chapter = chapter_crud.get_by_id(session, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return {
        "chapter_id": chapter.id,
        "title": chapter.title,
        "detail_outline": chapter.detail_outline,
        "content": chapter.content,
        "word_count": chapter.word_count,
    }


@router.put("/chapter/{chapter_id}/outline")
async def update_chapter_outline(
    chapter_id: int,
    request_data: OutlineUpdateRequest,
    session: SessionDep,
):
    """手动保存章节细纲"""
    chapter = chapter_crud.get_by_id(session, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    chapter_crud.update(session, chapter_id, detail_outline=request_data.detail_outline)
    return {"ok": True, "chapter_id": chapter_id}


@router.post("/{novel_id}/compress-summaries")
async def compress_novel_summaries(
    novel_id: int,
    session: SessionDep,
    orch: OrchestratorDep,
    force: bool = Query(False, description="强制重新压缩已有摘要"),
):
    """批量压缩小说已生成章节的摘要（供上下文压缩器使用）"""
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    try:
        from ainovel.core.context_compressor import ContextCompressor
        compressor = ContextCompressor(orch.llm_client, session)

        all_chapters = []
        for volume in sorted(novel.volumes, key=lambda v: v.order):
            all_chapters.extend(sorted(volume.chapters, key=lambda c: c.order))

        # 只处理有正文的章节
        target = [c for c in all_chapters if c.content and (force or not c.summary)]
        compressed = 0
        skipped = 0
        for chapter in target:
            if not force and chapter.summary:
                skipped += 1
                continue
            # force 时清空缓存让 compress_and_cache 重新生成
            if force:
                chapter_crud.update(session, chapter.id, summary=None)
            compressor.compress_and_cache(chapter.id)
            compressed += 1

        return {
            "ok": True,
            "novel_id": novel_id,
            "compressed": compressed,
            "skipped": skipped,
            "total_with_content": len([c for c in all_chapters if c.content]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"压缩失败: {e}")


@router.post("/{novel_id}/vectorize")
async def vectorize_novel(
    novel_id: int,
    session: SessionDep,
    force: bool = Query(False, description="强制重新向量化所有伏笔"),
):
    """对小说伏笔进行向量化索引（供章节编辑器调用）"""
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    try:
        from ainovel.memory.rag_retriever import RAGRetriever
        retriever = RAGRetriever(session)
        count = retriever.index_novel(novel_id, force=force)
        return {"ok": True, "indexed_count": count, "novel_id": novel_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"向量化失败: {e}")


# ============ KB2 专项分析 API ============


class AnalysisRequest(BaseModel):
    chapter_range: str | None = None  # 如 "1-10"，None 表示全部


@router.post("/{novel_id}/analyze/satisfaction", summary="爽点专项分析（KB2 帮回系统）")
async def analyze_satisfaction(
    novel_id: int,
    request_data: AnalysisRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """分析章节爽点密度、类型分布与三高评分"""
    try:
        return await asyncio.to_thread(orch.analyze_satisfaction, session, novel_id, request_data.chapter_range)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/analyze/rhythm", summary="节奏专项分析（KB2 帮回系统）")
async def analyze_rhythm(
    novel_id: int,
    request_data: AnalysisRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """分析快/中/慢场景比例与快慢交替合理性"""
    try:
        return await asyncio.to_thread(orch.analyze_rhythm, session, novel_id, request_data.chapter_range)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/analyze/conflict", summary="冲突专项分析（KB2 帮回系统）")
async def analyze_conflict(
    novel_id: int,
    request_data: AnalysisRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """分析明暗线强度、四维升级与不完全胜利"""
    try:
        return await asyncio.to_thread(orch.analyze_conflict, session, novel_id, request_data.chapter_range)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class CharacterAnalysisRequest(BaseModel):
    character_name: str
    chapter_range: str | None = None


@router.post("/{novel_id}/analyze/character", summary="人设专项检查（KB2 帮回系统）")
async def analyze_character(
    novel_id: int,
    request_data: CharacterAnalysisRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """检查角色价值观/行为/决策/语言四维一致性与成长弧光"""
    try:
        return await asyncio.to_thread(
            orch.analyze_character,
            session, novel_id, request_data.character_name, request_data.chapter_range
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/analyze/opening", summary="开篇质量专项检查（KB2 黄金开篇五大铁律）")
async def analyze_opening(
    novel_id: int,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """检查前3章是否符合黄金开篇五大铁律"""
    try:
        return await asyncio.to_thread(orch.analyze_opening, session, novel_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ HTML 视图路由 ============


@router.get("/{novel_id}", response_class=RedirectResponse)
async def workflow_page(novel_id: int):
    """重定向到小说详情页（工作流已整合到详情页）"""
    return RedirectResponse(url=f"/novels/view/{novel_id}", status_code=301)
