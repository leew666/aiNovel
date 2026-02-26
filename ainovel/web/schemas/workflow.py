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

    planning_content: str = Field(..., description="编辑后的创作思路")


class Step5Request(BaseModel):
    """步骤5：章节内容生成请求"""

    style_guide: Optional[str] = Field(None, description="写作风格指南")
    authors_note: Optional[str] = Field(None, description="作者备注，动态注入的写作指令（参考KoboldAI Author's Note）")


class ConsistencyCheckRequest(BaseModel):
    """一致性检查请求"""

    content_override: Optional[str] = Field(
        None, description="可选检查文本，不写入数据库"
    )
    strict: bool = Field(False, description="是否启用严格模式")


class ChapterRewriteRequest(BaseModel):
    """章节改写请求"""

    instruction: str = Field(..., min_length=1, description="改写指令")
    target_scope: str = Field("paragraph", description="改写范围：paragraph 或 chapter")
    range_start: Optional[int] = Field(None, ge=1, description="段落起始（1-based）")
    range_end: Optional[int] = Field(None, ge=1, description="段落结束（1-based）")
    preserve_plot: bool = Field(True, description="是否保持主线剧情不变")
    rewrite_mode: str = Field("rewrite", description="改写模式：rewrite/polish/expand")
    save: bool = Field(False, description="是否保存改写结果到章节正文")


class ChapterRollbackRequest(BaseModel):
    """章节改写回滚请求"""

    history_id: Optional[str] = Field(None, description="指定回滚版本ID；为空时回滚最近一次")
    save: bool = Field(True, description="是否保存回滚结果到章节正文")


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
    planning: str
    stats: dict[str, Any]


class Step2Response(BaseModel):
    """步骤2：世界观和角色生成响应"""

    novel_id: int
    workflow_status: str
    characters: list[dict[str, Any]]
    world_data: list[dict[str, Any]]
    stats: dict[str, Any]
    raw_content: Optional[str] = Field(None, description="大模型原始输出文本")
    parse_failed: bool = Field(False, description="JSON解析是否失败，失败时需用户手动修改raw_content")


class Step3Response(BaseModel):
    """步骤3：大纲生成响应"""

    novel_id: int
    workflow_status: str
    volumes: list[dict[str, Any]]
    stats: dict[str, Any]
    raw_content: Optional[str] = Field(None, description="大模型原始输出文本")
    parse_failed: bool = Field(False, description="JSON解析是否失败，失败时需用户手动修改raw_content")


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


class ChapterRewriteResponse(BaseModel):
    """章节改写响应"""

    novel_id: int
    chapter_id: int
    chapter_title: str
    rewrite_mode: str
    target_scope: str
    range_start: Optional[int] = None
    range_end: Optional[int] = None
    instruction: str
    preserve_plot: bool
    original_content: str
    new_content: str
    diff_summary: str
    saved: bool
    history_id: str
    usage: dict[str, Any]
    cost: float
    model: Optional[str] = None


class ChapterRollbackResponse(BaseModel):
    """章节改写回滚响应"""

    novel_id: int
    chapter_id: int
    chapter_title: str
    history_id: Optional[str] = None
    rolled_back_content: str
    saved: bool


class PipelineRunRequest(BaseModel):
    """流水线运行请求"""

    from_step: int = Field(3, ge=3, le=5, description="起始步骤（3=大纲, 4=细纲, 5=正文）")
    to_step: int = Field(5, ge=3, le=5, description="结束步骤（须 >= from_step）")
    chapter_range: Optional[str] = Field(
        None, description="章节范围，如 '1-10' 或 '1,3,5'；None 表示全部"
    )
    regenerate: bool = Field(False, description="是否强制重新生成已有内容")
    max_workers: int = Field(1, ge=1, le=16, description="并行线程数，1=串行，>1=多线程并行")


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
