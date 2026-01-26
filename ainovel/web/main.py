"""
FastAPI 主应用

初始化 FastAPI 应用，配置路由、中间件、模板引擎
"""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from loguru import logger

from ainovel.web.config import settings
from ainovel.web.dependencies import get_database

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI小说创作系统 Web 界面",
    debug=settings.DEBUG,
)


# ============ 静态文件和模板配置 ============

# 获取当前文件所在目录
BASE_DIR = Path(__file__).resolve().parent

# 配置静态文件
static_path = BASE_DIR / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# 配置模板引擎
templates_path = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_path))


# ============ 生命周期事件 ============


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")

    # 初始化数据库
    db = get_database()
    db.create_all_tables()
    logger.info(f"✅ 数据库初始化完成: {settings.DATABASE_URL}")

    # 创建数据目录
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    logger.info(f"✅ 数据目录已创建: {data_dir.absolute()}")

    logger.info(f"🌐 Web 服务器运行在 http://{settings.HOST}:{settings.PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("🛑 应用关闭")


# ============ 根路由 ============


@app.get("/", response_class=HTMLResponse, summary="首页")
async def index(request: Request):
    """
    首页 - 小说项目列表

    显示所有小说项目，支持创建新项目
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    )


@app.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口

    用于监控和容器健康检查
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ============ 注册路由 ============

from ainovel.web.routers import novels, workflow

app.include_router(novels.router, prefix="/novels", tags=["小说项目"])
app.include_router(workflow.router, prefix="/workflow", tags=["创作流程"])
# app.include_router(characters.router, prefix="/characters", tags=["角色管理"])  # 阶段2
# app.include_router(world.router, prefix="/world", tags=["世界观管理"])  # 阶段2


# ============ 错误处理 ============


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 错误处理"""
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 404,
            "error_message": "页面未找到",
        },
        status_code=404,
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """500 错误处理"""
    logger.error(f"Internal error: {exc}")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_code": 500,
            "error_message": "服务器内部错误",
        },
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ainovel.web.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )
