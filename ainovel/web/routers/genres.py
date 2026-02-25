"""
题材与情节标签路由

提供小说类型列表和对应情节标签的查询接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ainovel.core.genre_data import (
    get_all_genres,
    get_all_plots,
    get_plots_for_genre,
    check_conflicts,
    GenreInfo,
    PlotTag,
)

router = APIRouter()


class GenreListResponse(BaseModel):
    genres: list[dict]


class PlotListResponse(BaseModel):
    genre_id: str | None
    plots: list[dict]
    conflicts: list[str] = []


@router.get("/", response_model=GenreListResponse, summary="获取所有题材列表")
async def list_genres():
    """返回所有主题材，按热度降序排列"""
    return GenreListResponse(genres=list(get_all_genres()))


@router.get("/{genre_id}/plots", response_model=PlotListResponse, summary="获取题材对应的情节标签")
async def list_plots_for_genre(genre_id: str):
    """
    根据题材 ID 返回情节标签列表。
    推荐搭配排在前面，其余情节补充在后。
    """
    plots = get_plots_for_genre(genre_id)
    if not plots:
        raise HTTPException(status_code=404, detail=f"题材 '{genre_id}' 不存在")
    return PlotListResponse(genre_id=genre_id, plots=plots)


@router.get("/plots/all", response_model=PlotListResponse, summary="获取所有情节标签")
async def list_all_plots():
    """返回全部情节标签，按热度降序"""
    return PlotListResponse(genre_id=None, plots=list(get_all_plots()))


@router.post("/conflicts/check", summary="检测类型组合冲突")
async def check_genre_conflicts(selected_ids: list[str]):
    """
    传入选中的 genre_id 和 plot_id 列表，返回冲突警告。
    空列表表示无冲突。
    """
    warnings = check_conflicts(selected_ids)
    return {"conflicts": warnings, "has_conflict": len(warnings) > 0}
