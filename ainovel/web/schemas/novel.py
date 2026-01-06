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
    genre: Optional[str] = Field(None, max_length=50, description="小说类型（如玄幻、都市）")


class NovelUpdate(BaseModel):
    """更新小说项目请求"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    author: Optional[str] = Field(None, max_length=100)
    genre: Optional[str] = Field(None, max_length=50)


# ============ 响应模型 (Response Models) ============


class NovelResponse(BaseModel):
    """小说项目响应"""

    id: int
    title: str
    description: Optional[str]
    author: str
    genre: Optional[str]
    workflow_status: str  # WorkflowStatus 枚举值
    current_step: int
    created_at: datetime
    updated_at: datetime

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
