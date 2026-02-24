"""
小说项目管理路由

提供小说项目的 CRUD 操作
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ainovel.web.dependencies import SessionDep
from ainovel.web.schemas.novel import (
    NovelCreate,
    NovelUpdate,
    NovelResponse,
    NovelListResponse,
    NovelDetailResponse,
)
from ainovel.db.crud import novel_crud
from ainovel.db.novel import Novel

router = APIRouter()

# 配置模板
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_model=NovelListResponse, summary="获取小说列表")
async def list_novels(session: SessionDep, skip: int = 0, limit: int = 100):
    """
    获取所有小说项目列表

    Args:
        session: 数据库会话
        skip: 跳过记录数
        limit: 返回记录数

    Returns:
        小说列表
    """
    novels = novel_crud.get_all(session, skip=skip, limit=limit)
    total = novel_crud.count(session)

    return NovelListResponse(
        total=total,
        novels=[NovelResponse.model_validate(novel) for novel in novels],
    )


@router.post("/", response_model=NovelResponse, status_code=201, summary="创建小说项目")
async def create_novel(novel_data: NovelCreate, session: SessionDep):
    """
    创建新的小说项目

    Args:
        novel_data: 小说数据
        session: 数据库会话

    Returns:
        创建的小说项目
    """
    # 保存到数据库
    created_novel = novel_crud.create(
        session,
        title=novel_data.title,
        description=novel_data.description,
        author=novel_data.author,
        genre=novel_data.genre,
    )

    return NovelResponse.model_validate(created_novel)


@router.get("/{novel_id:int}", response_model=NovelDetailResponse, summary="获取小说详情")
async def get_novel(novel_id: int, session: SessionDep):
    """
    获取指定小说项目的详细信息

    Args:
        novel_id: 小说ID
        session: 数据库会话

    Returns:
        小说详情

    Raises:
        HTTPException: 小说不存在时返回 404
    """
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说项目不存在")

    # 计算统计信息
    volumes_count = len(novel.volumes)
    chapters_count = sum(len(volume.chapters) for volume in novel.volumes)
    total_words = sum(
        chapter.word_count or 0
        for volume in novel.volumes
        for chapter in volume.chapters
    )

    response = NovelResponse.model_validate(novel)
    return NovelDetailResponse(
        **response.model_dump(),
        volumes_count=volumes_count,
        chapters_count=chapters_count,
        total_words=total_words,
    )


@router.put("/{novel_id:int}", response_model=NovelResponse, summary="更新小说项目")
async def update_novel(novel_id: int, novel_data: NovelUpdate, session: SessionDep):
    """
    更新小说项目信息

    Args:
        novel_id: 小说ID
        novel_data: 更新数据
        session: 数据库会话

    Returns:
        更新后的小说项目

    Raises:
        HTTPException: 小说不存在时返回 404
    """
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说项目不存在")

    # 更新字段
    update_data = novel_data.model_dump(exclude_unset=True)
    updated_novel = novel_crud.update(session, novel_id, **update_data)

    return NovelResponse.model_validate(updated_novel)


@router.delete("/{novel_id:int}", status_code=204, summary="删除小说项目")
async def delete_novel(novel_id: int, session: SessionDep):
    """
    删除小说项目（级联删除所有关联数据）

    Args:
        novel_id: 小说ID
        session: 数据库会话

    Raises:
        HTTPException: 小说不存在时返回 404
    """
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说项目不存在")

    novel_crud.delete(session, novel_id)


# ============ HTML 视图路由（使用 HTMX） ============


@router.get("/list-html", response_class=HTMLResponse, summary="小说列表 HTML 片段")
async def list_novels_html(request: Request, session: SessionDep):
    """返回小说列表的 HTML 片段，供首页 HTMX 加载"""
    novels = novel_crud.get_all(session, skip=0, limit=100)
    return templates.TemplateResponse(
        "partials/novel_list.html",
        {"request": request, "novels": novels},
    )


@router.post("/create-html", response_class=HTMLResponse, summary="创建小说并返回 HTML 片段")
async def create_novel_html(request: Request, session: SessionDep):
    """接收表单数据，创建小说，返回新卡片 HTML 片段"""
    form = await request.form()
    novel = novel_crud.create(
        session,
        title=form.get("title", ""),
        description=form.get("description") or None,
        author=form.get("author") or "AI",
        genre=form.get("genre") or None,
    )
    return templates.TemplateResponse(
        "partials/novel_card.html",
        {"request": request, "novel": novel},
    )


@router.get("/view/{novel_id}", response_class=HTMLResponse, summary="小说详情页")
async def view_novel(novel_id: int, request: Request, session: SessionDep):
    """
    小说详情页面（HTML）

    包含项目信息和工作流入口
    """
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说项目不存在")

    volumes_count = len(novel.volumes)
    chapters_count = sum(len(v.chapters) for v in novel.volumes)
    total_words = sum(
        c.word_count or 0 for v in novel.volumes for c in v.chapters
    )

    return templates.TemplateResponse(
        "novel_detail.html",
        {
            "request": request,
            "novel": novel,
            "volumes_count": volumes_count,
            "chapters_count": chapters_count,
            "total_words": total_words,
        },
    )
