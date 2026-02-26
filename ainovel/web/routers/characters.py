"""
角色卡管理路由

提供角色卡的查看与编辑功能（HTMX 驱动）
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ainovel.web.dependencies import SessionDep
from ainovel.db.crud import novel_crud
from ainovel.memory.character_db import CharacterDatabase
from ainovel.memory.character import MBTIType

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/novels/{novel_id}/characters", response_class=HTMLResponse, summary="角色列表页")
async def list_characters(novel_id: int, request: Request, session: SessionDep):
    """角色卡列表页面"""
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说项目不存在")

    char_db = CharacterDatabase(session)
    characters = char_db.list_characters(novel_id)

    return templates.TemplateResponse(
        "characters.html",
        {"request": request, "novel": novel, "characters": characters},
    )


@router.get("/characters/{character_id}/edit", response_class=HTMLResponse, summary="角色编辑页")
async def edit_character(character_id: int, request: Request, session: SessionDep):
    """角色卡详情/编辑页面"""
    char_db = CharacterDatabase(session)
    character = char_db.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")

    novel = novel_crud.get_by_id(session, character.novel_id)

    return templates.TemplateResponse(
        "character_edit.html",
        {"request": request, "character": character, "novel": novel},
    )


@router.post("/characters/{character_id}/edit", response_class=HTMLResponse, summary="保存角色编辑")
async def save_character(character_id: int, request: Request, session: SessionDep):
    """接收表单数据，更新角色卡，返回成功提示片段"""
    char_db = CharacterDatabase(session)
    character = char_db.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")

    form = await request.form()

    # 处理口头禅：换行分隔的多行文本 → 列表
    catchphrases_raw = form.get("catchphrases", "")
    catchphrases = [p.strip() for p in catchphrases_raw.splitlines() if p.strip()]

    char_db.update_character(
        character_id,
        background=form.get("background", character.background),
        goals=form.get("goals") or None,
        current_status=form.get("current_status") or None,
        current_mood=form.get("current_mood") or None,
        catchphrases=catchphrases,
    )

    return templates.TemplateResponse(
        "partials/character_saved.html",
        {"request": request, "character": character},
    )


@router.post("/novels/{novel_id}/characters/new", response_class=HTMLResponse, summary="新增角色")
async def create_character(novel_id: int, request: Request, session: SessionDep):
    """接收表单数据，创建新角色，重定向回角色列表页"""
    novel = novel_crud.get_by_id(session, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说项目不存在")

    form = await request.form()
    name = (form.get("name") or "").strip()
    background = (form.get("background") or "").strip()
    mbti_str = (form.get("mbti") or "INTJ").strip().upper()

    if not name:
        raise HTTPException(status_code=400, detail="角色名不能为空")
    if not background:
        raise HTTPException(status_code=400, detail="背景故事不能为空")

    try:
        mbti = MBTIType[mbti_str]
    except KeyError:
        mbti = MBTIType.INTJ

    char_db = CharacterDatabase(session)
    char_db.create_character(
        novel_id=novel_id,
        name=name,
        mbti=mbti,
        background=background,
    )
    session.commit()

    return RedirectResponse(url=f"/novels/{novel_id}/characters", status_code=303)
