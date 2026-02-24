"""
系统配置路由

提供 LLM 配置的查看与更新页面，支持自定义 OpenAI 兼容端点和模型查询
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ainovel.web.config import settings

router = APIRouter(redirect_slashes=False)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 内置预设模型
_PRESET_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "claude": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
    "qwen": ["qwen-max", "qwen-plus", "qwen-turbo"],
}

# 内置提供商列表
_BUILTIN_PROVIDERS = ["openai", "claude", "qwen"]


def _read_env() -> dict[str, str]:
    """读取 .env 文件，返回 key-value 字典"""
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
    """将 key-value 字典写回 .env 文件"""
    lines = [f"{k}={v}" for k, v in data.items()]
    Path(".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, summary="配置页面")
async def settings_page(request: Request):
    """显示当前 LLM 配置"""
    provider = settings.LLM_PROVIDER.lower()
    is_custom = provider not in _BUILTIN_PROVIDERS
    key_map = {
        "openai": settings.OPENAI_API_KEY,
        "claude": settings.ANTHROPIC_API_KEY,
        "qwen": settings.DASHSCOPE_API_KEY,
    }
    # 自定义 provider 也用 openai_api_key
    current_key_set = bool(
        key_map.get(provider) if not is_custom else settings.OPENAI_API_KEY
    )
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "provider": provider,
            "is_custom": is_custom,
            "model": settings.LLM_MODEL,
            "openai_api_base": settings.OPENAI_API_BASE,
            "preset_models": _PRESET_MODELS,
            "builtin_providers": _BUILTIN_PROVIDERS,
            "openai_key_set": bool(settings.OPENAI_API_KEY),
            "claude_key_set": bool(settings.ANTHROPIC_API_KEY),
            "qwen_key_set": bool(settings.DASHSCOPE_API_KEY),
            "current_key_set": current_key_set,
            "daily_budget": settings.DAILY_BUDGET,
            "database_url": settings.DATABASE_URL,
        },
    )


@router.get("/models", summary="查询 OpenAI 兼容端点的可用模型列表")
async def list_models(api_base: str, api_key: Optional[str] = None):
    """
    调用指定 api_base 的 /models 接口，返回模型 ID 列表。
    api_key 优先使用参数值，否则回退到当前配置的 OPENAI_API_KEY。
    """
    import httpx

    key = api_key or settings.OPENAI_API_KEY or ""
    base = api_base.rstrip("/")
    url = f"{base}/models"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {key}"})
            resp.raise_for_status()
            data = resp.json()
            ids = sorted(m["id"] for m in data.get("data", []))
            return JSONResponse({"models": ids})
    except Exception as e:
        return JSONResponse({"models": [], "error": str(e)}, status_code=200)


@router.post("/save", response_class=HTMLResponse, summary="保存配置到 .env")
async def save_settings(request: Request):
    """将表单提交的配置写入 .env 文件"""
    form = await request.form()
    provider = (form.get("provider") or "openai").strip().lower()
    # 自定义 provider 名称
    custom_provider = (form.get("custom_provider") or "").strip().lower()
    if provider == "custom" and custom_provider:
        provider = custom_provider

    model = (form.get("model") or "").strip() or "gpt-4o-mini"
    openai_api_base = (form.get("openai_api_base") or "").strip() or "https://api.openai.com/v1"
    openai_key = (form.get("openai_key") or "").strip()
    claude_key = (form.get("claude_key") or "").strip()
    qwen_key = (form.get("qwen_key") or "").strip()
    daily_budget = (form.get("daily_budget") or "10.0").strip()

    existing = _read_env()
    existing["LLM_PROVIDER"] = provider
    existing["LLM_MODEL"] = model
    existing["OPENAI_API_BASE"] = openai_api_base
    existing["DAILY_BUDGET"] = daily_budget
    if openai_key:
        existing["OPENAI_API_KEY"] = openai_key
    if claude_key:
        existing["ANTHROPIC_API_KEY"] = claude_key
    if qwen_key:
        existing["DASHSCOPE_API_KEY"] = qwen_key
    _write_env(existing)

    return templates.TemplateResponse(
        "partials/settings_saved.html",
        {"request": request, "provider": provider, "model": model},
    )
