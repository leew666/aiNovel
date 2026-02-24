"""
小说导入与改写路由

提供 Web 页面导入已有小说并逐章改写。
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ainovel.web.dependencies import SessionDep, LLMClientDep
from ainovel.core.novel_importer import import_and_rewrite_novel

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse, summary="导入改写页面")
async def import_page(request: Request):
    return templates.TemplateResponse("importer.html", {"request": request})


@router.post("/run", response_class=HTMLResponse, summary="导入并逐章改写")
async def run_import(request: Request, session: SessionDep, llm_client: LLMClientDep):
    form = await request.form()

    title = (form.get("title") or "").strip()
    raw_text = (form.get("raw_text") or "").strip()
    instruction = (form.get("instruction") or "").strip()

    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    if not raw_text:
        raise HTTPException(status_code=400, detail="原文不能为空")
    if not instruction:
        raise HTTPException(status_code=400, detail="改写指令不能为空")

    author = (form.get("author") or "").strip() or None
    genre = (form.get("genre") or "").strip() or None
    description = (form.get("description") or "").strip() or None
    rewrite_mode = (form.get("rewrite_mode") or "rewrite").strip().lower()
    preserve_plot = (form.get("preserve_plot") or "").lower() in {"1", "true", "on", "yes"}

    try:
        stats = import_and_rewrite_novel(
            session,
            llm_client,
            title=title,
            author=author,
            genre=genre,
            description=description,
            raw_text=raw_text,
            instruction=instruction,
            rewrite_mode=rewrite_mode,
            preserve_plot=preserve_plot,
        )
        return templates.TemplateResponse(
            "partials/import_result.html",
            {"request": request, "stats": stats},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导入失败: {exc}")
