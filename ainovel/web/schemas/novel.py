"""
小说相关的 Pydantic 模型

定义API请求和响应的数据格式
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============ 请求模型 (Request Models) ============


class NovelCreate(BaseModel):
    """创建小说项目请求"""

    title: str = Field(..., min_length=1, max_length=200, description="小说标题")
    description: Optional[str] = Field(None, max_length=1000, description="小说简介/初始想法")
    author: str = Field(default="AI", max_length=100, description="作者名称")
    genre: Optional[str] = Field(None, max_length=50, description="主题材 ID（如 xuanhuan、urban）")
    plots: Optional[list[str]] = Field(None, description="情节流派标签 ID 列表（如 ['rebirth', 'revenge']）")


class NovelUpdate(BaseModel):
    """更新小说项目请求"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    author: Optional[str] = Field(None, max_length=100)
    genre: Optional[str] = Field(None, max_length=50)
    plots: Optional[list[str]] = Field(None, description="情节流派标签 ID 列表")


# ============ 响应模型 (Response Models) ============


class NovelResponse(BaseModel):
    """小说项目响应"""

    id: int
    title: str
    description: Optional[str]
    author: str
    genre: Optional[str]
    plots: Optional[list[str]] = None  # 反序列化为列表
    workflow_status: str  # WorkflowStatus 枚举值
    current_step: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # 将数据库中逗号分隔字符串转换为列表
        data = obj.__dict__.copy() if hasattr(obj, "__dict__") else dict(obj)
        if isinstance(data.get("plots"), str):
            data["plots"] = [p for p in data["plots"].split(",") if p]
        elif data.get("plots") is None:
            data["plots"] = []
        return super().model_validate(data, **kwargs)

    class Config:
        from_attributes = True  # Pydantic v2


class NovelListResponse(BaseModel):
    """小说项目列表响应"""

    total: int
    novels: list[NovelResponse]


class NovelDetailResponse(NovelResponse):
    """小说项目详情响应（包含统计信息）"""

    volumes_count: int = 0
    chapters_count: int = 0
    total_words: int = 0
