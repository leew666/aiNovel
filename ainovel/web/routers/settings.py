"""
系统配置路由

提供 LLM 配置的查看与更新页面，支持多个自定义 OpenAI 兼容提供商
"""
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ainovel.web.config import settings
from ainovel.llm.factory import LLMFactory
from ainovel.web.dependencies import reset_llm_client

router = APIRouter(redirect_slashes=False)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_PRESET_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "claude": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
    "qwen": ["qwen-max", "qwen-plus", "qwen-turbo"],
}

_BUILTIN_PROVIDERS = ["openai", "claude", "qwen"]


def _read_env() -> dict[str, str]:
    env_path = Path(".env")
    result: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result


def _write_env(data: dict[str, str]) -> None:
    env_path = Path(".env")
    original_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    written_keys: set[str] = set()
    result: list[str] = []
    for line in original_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, _ = stripped.partition("=")
            k = k.strip()
            if k in data:
                result.append(f"{k}={data[k]}")
                written_keys.add(k)
                continue
        result.append(line)
    for k, v in data.items():
        if k not in written_keys:
            result.append(f"{k}={v}")
    env_path.write_text("\n".join(result) + "\n", encoding="utf-8")


def _save_custom_providers(providers: list) -> None:
    """将自定义 provider 列表持久化到 .env 并同步内存。"""
    json_str = json.dumps(providers, ensure_ascii=False)
    existing = _read_env()
    existing["CUSTOM_PROVIDERS"] = json_str
    _write_env(existing)
    settings.CUSTOM_PROVIDERS = json_str


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, summary="配置页面")
async def settings_page(request: Request):
    provider = settings.LLM_PROVIDER.lower()
    is_custom = provider not in _BUILTIN_PROVIDERS
    active_custom = settings.get_custom_provider(provider) if is_custom else None
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "provider": provider,
            "is_custom": is_custom,
            "active_custom": active_custom,
            "custom_providers": settings.get_custom_providers(),
            "openai_model": settings.OPENAI_MODEL,
            "openai_api_base": settings.OPENAI_API_BASE,
            "openai_key_set": bool(settings.OPENAI_API_KEY),
            "claude_model": settings.ANTHROPIC_MODEL,
            "claude_key_set": bool(settings.ANTHROPIC_API_KEY),
            "qwen_model": settings.QIANWEN_MODEL,
            "qwen_api_base": settings.DASHSCOPE_API_BASE,
            "qwen_key_set": bool(settings.DASHSCOPE_API_KEY),
            "preset_models": _PRESET_MODELS,
            "daily_budget": settings.DAILY_BUDGET,
            "database_url": settings.DATABASE_URL,
        },
    )


@router.get("/models", summary="查询 OpenAI 兼容端点的可用模型列表")
async def list_models(api_base: str, api_key: Optional[str] = None):
    import httpx
    key = api_key or settings.OPENAI_API_KEY or ""
    base = api_base.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
            resp.raise_for_status()
            ids = sorted(m["id"] for m in resp.json().get("data", []))
            return JSONResponse({"models": ids})
    except Exception as e:
        return JSONResponse({"models": [], "error": str(e)}, status_code=200)


@router.post("/save", response_class=HTMLResponse, summary="保存内置 provider 配置")
async def save_settings(request: Request):
    """保存内置 provider（openai/claude/qwen）配置及激活 provider。"""
    form = await request.form()
    provider = (form.get("provider") or "openai").strip().lower()
    daily_budget = (form.get("daily_budget") or "10.0").strip()

    existing = _read_env()
    existing["LLM_PROVIDER"] = provider
    existing["DAILY_BUDGET"] = daily_budget
    settings.LLM_PROVIDER = provider
    settings.DAILY_BUDGET = float(daily_budget)

    if provider == "claude":
        model = (form.get("model") or "").strip()
        key = (form.get("claude_key") or "").strip()
        if model:
            existing["ANTHROPIC_MODEL"] = model
            settings.ANTHROPIC_MODEL = model
        if key:
            existing["ANTHROPIC_API_KEY"] = key
            settings.ANTHROPIC_API_KEY = key
    elif provider == "qwen":
        model = (form.get("model") or "").strip()
        api_base = (form.get("openai_api_base") or "").strip()
        key = (form.get("qwen_key") or "").strip()
        if model:
            existing["QIANWEN_MODEL"] = model
            settings.QIANWEN_MODEL = model
        if api_base:
            existing["DASHSCOPE_API_BASE"] = api_base
            settings.DASHSCOPE_API_BASE = api_base
        if key:
            existing["DASHSCOPE_API_KEY"] = key
            settings.DASHSCOPE_API_KEY = key
    else:
        # openai 或切换到某个自定义 provider（只更新激活，不改其配置）
        if provider == "openai":
            model = (form.get("model") or "").strip()
            api_base = (form.get("openai_api_base") or "").strip()
            key = (form.get("openai_key") or "").strip()
            if model:
                existing["OPENAI_MODEL"] = model
                settings.OPENAI_MODEL = model
            if api_base:
                existing["OPENAI_API_BASE"] = api_base
                settings.OPENAI_API_BASE = api_base
            if key:
                existing["OPENAI_API_KEY"] = key
                settings.OPENAI_API_KEY = key

    _write_env(existing)
    reset_llm_client()
    return templates.TemplateResponse(
        "partials/settings_saved.html",
        {"request": request, "provider": provider, "model": settings.LLM_MODEL},
    )


# ===== 自定义 provider CRUD API =====

class CustomProviderBody(BaseModel):
    name: str
    api_key: str
    api_base: str
    model: str


@router.get("/custom-providers", summary="获取自定义 provider 列表")
async def get_custom_providers():
    providers = settings.get_custom_providers()
    # 隐藏 api_key 明文
    masked = [
        {**p, "api_key": "***" if p.get("api_key") else ""}
        for p in providers
    ]
    return JSONResponse({"providers": masked})


@router.post("/custom-providers", summary="新增自定义 provider")
async def add_custom_provider(body: CustomProviderBody):
    name = body.name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="name 不能为空")
    if name in _BUILTIN_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"'{name}' 是内置提供商名称，请换一个")
    providers = settings.get_custom_providers()
    if any(p["name"].lower() == name for p in providers):
        raise HTTPException(status_code=400, detail=f"提供商 '{name}' 已存在，请使用编辑接口")
    providers.append({"name": name, "api_key": body.api_key, "api_base": body.api_base, "model": body.model})
    _save_custom_providers(providers)
    return JSONResponse({"ok": True, "name": name})


@router.put("/custom-providers/{name}", summary="编辑自定义 provider")
async def update_custom_provider(name: str, body: CustomProviderBody):
    name = name.strip().lower()
    providers = settings.get_custom_providers()
    for i, p in enumerate(providers):
        if p["name"].lower() == name:
            providers[i] = {
                "name": name,
                "api_key": body.api_key or p["api_key"],  # 留空则保持原值
                "api_base": body.api_base,
                "model": body.model,
            }
            _save_custom_providers(providers)
            if settings.LLM_PROVIDER.lower() == name:
                reset_llm_client()
            return JSONResponse({"ok": True, "name": name})
    raise HTTPException(status_code=404, detail=f"提供商 '{name}' 不存在")


@router.delete("/custom-providers/{name}", summary="删除自定义 provider")
async def delete_custom_provider(name: str):
    name = name.strip().lower()
    providers = settings.get_custom_providers()
    new_providers = [p for p in providers if p["name"].lower() != name]
    if len(new_providers) == len(providers):
        raise HTTPException(status_code=404, detail=f"提供商 '{name}' 不存在")
    _save_custom_providers(new_providers)
    # 若删除的是当前激活 provider，切回 openai
    if settings.LLM_PROVIDER.lower() == name:
        settings.LLM_PROVIDER = "openai"
        existing = _read_env()
        existing["LLM_PROVIDER"] = "openai"
        _write_env(existing)
        reset_llm_client()
    return JSONResponse({"ok": True, "name": name})


@router.post("/custom-providers/{name}/activate", summary="激活自定义 provider")
async def activate_custom_provider(name: str):
    name = name.strip().lower()
    if not settings.get_custom_provider(name):
        raise HTTPException(status_code=404, detail=f"提供商 '{name}' 不存在")
    settings.LLM_PROVIDER = name
    existing = _read_env()
    existing["LLM_PROVIDER"] = name
    _write_env(existing)
    reset_llm_client()
    return JSONResponse({"ok": True, "name": name, "model": settings.LLM_MODEL})
