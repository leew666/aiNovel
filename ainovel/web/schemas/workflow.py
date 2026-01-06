"""
工作流相关的 Pydantic 模型
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


# ============ 请求模型 ============


class Step1Request(BaseModel):
    """步骤1：创作思路生成请求"""

    initial_idea: Optional[str] = Field(None, description="用户的初始想法")


class Step1UpdateRequest(BaseModel):
    """步骤1：用户编辑创作思路后更新"""

    planning_content: str = Field(..., description="编辑后的创作思路（JSON字符串）")


class Step5Request(BaseModel):
    """步骤5：章节内容生成请求"""

    style_guide: Optional[str] = Field(None, description="写作风格指南")


# ============ 响应模型 ============


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应"""

    novel_id: int
    workflow_status: str
    current_step: int
    can_continue: bool


class Step1Response(BaseModel):
    """步骤1：创作思路生成响应"""

    novel_id: int
    workflow_status: str
    planning: dict[str, Any]
    stats: dict[str, Any]


class Step2Response(BaseModel):
    """步骤2：世界观和角色生成响应"""

    novel_id: int
    workflow_status: str
    characters: list[dict[str, Any]]
    world_data: list[dict[str, Any]]
    stats: dict[str, Any]


class Step3Response(BaseModel):
    """步骤3：大纲生成响应"""

    novel_id: int
    workflow_status: str
    volumes: list[dict[str, Any]]
    stats: dict[str, Any]


class Step4Response(BaseModel):
    """步骤4：详细细纲生成响应"""

    novel_id: int
    workflow_status: str
    chapter_id: int
    chapter_title: str
    detail_outline: dict[str, Any]
    stats: dict[str, Any]


class Step4BatchResponse(BaseModel):
    """步骤4：批量细纲生成响应"""

    novel_id: int
    workflow_status: str
    total_chapters: int
    results: list[dict[str, Any]]


class Step5Response(BaseModel):
    """步骤5：章节内容生成响应"""

    novel_id: int
    workflow_status: str
    chapter_id: int
    chapter_title: str
    content: str
    stats: dict[str, Any]
