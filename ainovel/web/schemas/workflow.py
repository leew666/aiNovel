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


class ConsistencyCheckRequest(BaseModel):
    """一致性检查请求"""

    content_override: Optional[str] = Field(
        None, description="可选检查文本，不写入数据库"
    )
    strict: bool = Field(False, description="是否启用严格模式")


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


class Step6Response(BaseModel):
    """步骤6：质量检查响应"""

    novel_id: int
    workflow_status: str
    chapter_id: int
    chapter_title: str
    quality_report: dict[str, Any]
    stats: dict[str, Any]


class Step6BatchResponse(BaseModel):
    """步骤6：批量质量检查响应"""

    novel_id: int
    workflow_status: str
    total_chapters: int
    results: list[dict[str, Any]]


class ConsistencyCheckResponse(BaseModel):
    """一致性检查响应"""

    novel_id: int
    chapter_id: int
    chapter_title: str
    overall_risk: str
    summary: str = ""
    issues: list[dict[str, Any]]
    usage: dict[str, Any]
    cost: float


class PipelineRunRequest(BaseModel):
    """流水线运行请求"""

    from_step: int = Field(3, ge=3, le=5, description="起始步骤（3=大纲, 4=细纲, 5=正文）")
    to_step: int = Field(5, ge=3, le=5, description="结束步骤（须 >= from_step）")
    chapter_range: Optional[str] = Field(
        None, description="章节范围，如 '1-10' 或 '1,3,5'；None 表示全部"
    )
    regenerate: bool = Field(False, description="是否强制重新生成已有内容")


class PipelineTaskResult(BaseModel):
    """单章节任务结果"""

    chapter_id: int
    chapter_title: str
    step: int
    success: bool
    error: Optional[str] = None
    stats: dict[str, Any] = {}


class PipelineRunResponse(BaseModel):
    """流水线运行响应"""

    novel_id: int
    from_step: int
    to_step: int
    chapter_range: Optional[str]
    total: int
    succeeded: int
    failed: int
    skipped: int
    task_results: list[PipelineTaskResult]
    failed_chapter_ids: list[int]
