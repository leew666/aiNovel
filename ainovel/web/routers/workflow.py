"""
工作流路由

提供6步创作流程的 API 接口
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ainovel.web.dependencies import SessionDep, OrchestratorDep
from ainovel.web.schemas.workflow import *
from ainovel.db.crud import novel_crud

router = APIRouter()

# 配置模板
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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
        result = orch.step_1_planning(session, novel_id, request_data.initial_idea)
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
        result = orch.step_2_world_building(session, novel_id)
        return Step2Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/step3", response_model=Step3Response)
async def step3_outline(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤3：生成大纲"""
    try:
        result = orch.step_3_outline(session, novel_id)
        return Step3Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/step4", response_model=Step4Response)
async def step4_detail_outline(chapter_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤4：生成详细细纲（单章节）"""
    try:
        result = orch.step_4_detail_outline(session, chapter_id)
        return Step4Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/step4/batch", response_model=Step4BatchResponse)
async def step4_batch(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤4：批量生成所有章节细纲"""
    try:
        result = orch.step_4_batch_detail_outline(session, novel_id)
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
        result = orch.step_5_writing(session, chapter_id, request_data.style_guide)
        return Step5Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapter/{chapter_id}/step6", response_model=Step6Response)
async def step6_quality_check(chapter_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤6：质量检查（单章节）"""
    try:
        result = orch.step_6_quality_check(session, chapter_id)
        return Step6Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{novel_id}/step6/batch", response_model=Step6BatchResponse)
async def step6_batch(novel_id: int, session: SessionDep, orch: OrchestratorDep):
    """步骤6：批量质量检查所有已生成章节"""
    try:
        result = orch.step_6_batch_quality_check(session, novel_id)
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


# ============ HTML 视图路由 ============


@router.get("/{novel_id}", response_class=HTMLResponse)
async def workflow_page(novel_id: int, request: Request, session: SessionDep):
    """工作流页面（6步流程）"""
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说项目不存在")

    return templates.TemplateResponse(
        "workflow.html",
        {
            "request": request,
            "novel": novel,
        },
    )
