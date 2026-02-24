"""
文风学习路由

提供文风档案的管理 API：上传参考文本、分析文风、查看/激活档案
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ainovel.web.dependencies import SessionDep, OrchestratorDep

router = APIRouter()


# ===== 请求/响应模型 =====

class LearnStyleRequest(BaseModel):
    """学习文风请求"""
    name: str = Field(..., description="风格档案名称，如'金庸武侠风'")
    source_text: str = Field(..., description="参考文本（建议500字以上）")
    set_active: bool = Field(True, description="是否立即激活此档案")


class ActivateStyleRequest(BaseModel):
    """激活文风档案请求"""
    profile_id: int = Field(..., description="要激活的档案ID")


# ===== 路由 =====

@router.post("/{novel_id}/style/learn", response_model=dict)
async def learn_style(
    novel_id: int,
    request_data: LearnStyleRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """
    从参考文本学习写作风格，保存为文风档案。
    若 set_active=true，此档案将在后续章节生成时自动应用。
    """
    try:
        result = orch.learn_style(
            session=session,
            novel_id=novel_id,
            name=request_data.name,
            source_text=request_data.source_text,
            set_active=request_data.set_active,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文风分析失败: {str(e)}")


@router.get("/{novel_id}/style/profiles", response_model=dict)
async def list_style_profiles(
    novel_id: int,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """列出小说的所有文风档案"""
    try:
        return orch.list_style_profiles(session, novel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{novel_id}/style/activate", response_model=dict)
async def activate_style_profile(
    novel_id: int,
    request_data: ActivateStyleRequest,
    session: SessionDep,
    orch: OrchestratorDep,
):
    """激活指定文风档案，后续章节生成将自动应用该风格"""
    try:
        return orch.activate_style_profile(session, novel_id, request_data.profile_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
