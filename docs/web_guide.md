# Web 界面使用指南

## 快速启动

### 1. 安装依赖

```bash
# 如果使用 pip
pip install fastapi uvicorn[standard] jinja2 python-multipart pydantic-settings

# 或者安装整个项目（推荐）
pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# LLM 配置
LLM_PROVIDER=openai  # 或 claude、qwen
LLM_MODEL=gpt-4o-mini

# API 密钥（至少配置一个）
OPENAI_API_KEY=sk-xxx
# ANTHROPIC_API_KEY=sk-ant-xxx
# DASHSCOPE_API_KEY=sk-xxx

# 数据库
DATABASE_URL=sqlite:///data/ainovel.db

# Web 服务器
HOST=0.0.0.0
PORT=8000
DEBUG=true
RELOAD=true
```

### 3. 启动服务器

```bash
# 方法1：使用 Python 模块
PYTHONPATH=. python -m uvicorn ainovel.web.main:app --reload

# 方法2：直接运行 main.py
PYTHONPATH=. python ainovel/web/main.py

# 方法3：使用脚本（需要先 pip install -e .）
ainovel-web
```

### 4. 访问界面

打开浏览器访问：
- **首页**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs （FastAPI 自动生成）
- **健康检查**: http://localhost:8000/health

## 核心功能

### 1. 项目管理

#### 创建新项目
1. 访问首页
2. 点击"+ 创建新项目"按钮
3. 填写小说标题、简介、作者、类型
4. 提交创建

#### 查看项目列表
- 首页自动显示所有项目
- 包含项目名称、作者、状态、创建时间

### 2. 6步创作流程

#### 步骤1：创作思路
- **输入**: 用户的初始想法（可选）
- **输出**: 结构化创作思路（JSON格式）
- **支持编辑**: 可以手动修改生成的思路

#### 步骤2：世界观和角色
- **输入**: 无（使用步骤1的思路）
- **输出**: 角色列表 + 世界观数据
- **自动保存**: 存入 Character 和 WorldData 表

#### 步骤3：生成大纲
- **输入**: 无（使用步骤2的世界观）
- **输出**: 分卷大纲 + 章节列表
- **存储**: 创建 Volume 和 Chapter 记录

#### 步骤4：详细细纲
- **输入**: 章节ID（单章节）或 novel_id（批量）
- **输出**: 场景列表 + 关键事件
- **用途**: 为章节创作提供详细指引

#### 步骤5：章节创作
- **输入**: 章节ID + 文风指南（可选）
- **输出**: 完整章节内容
- **字数统计**: 自动统计字数

#### 步骤6：完成
- **操作**: 标记小说创作流程完成
- **状态**: 更新 workflow_status 为 COMPLETED

## API 接口

### 项目管理 API

```bash
# 获取所有项目
GET /novels/

# 创建项目
POST /novels/
{
  "title": "修仙废材逆袭",
  "description": "一个被退婚的废材少年...",
  "author": "AI",
  "genre": "玄幻"
}

# 获取项目详情
GET /novels/{novel_id}

# 更新项目
PUT /novels/{novel_id}
{
  "title": "新标题"
}

# 删除项目（级联删除所有数据）
DELETE /novels/{novel_id}
```

### 工作流 API

```bash
# 获取工作流状态
GET /workflow/{novel_id}/status

# 步骤1：生成创作思路
POST /workflow/{novel_id}/step1
{
  "initial_idea": "一个被退婚的废材少年..."
}

# 步骤1：更新创作思路
PUT /workflow/{novel_id}/step1
{
  "planning_content": "{...JSON...}"
}

# 步骤2：生成世界观
POST /workflow/{novel_id}/step2

# 步骤3：生成大纲
POST /workflow/{novel_id}/step3

# 步骤4：生成单章节细纲
POST /workflow/chapter/{chapter_id}/step4

# 步骤4：批量生成所有细纲
POST /workflow/{novel_id}/step4/batch

# 步骤5：生成章节内容
POST /workflow/chapter/{chapter_id}/step5
{
  "style_guide": "真人感写作风格..."
}

# 标记完成
POST /workflow/{novel_id}/complete
```

## 项目结构

```
ainovel/web/
├── main.py                # FastAPI 应用入口
├── config.py              # 配置管理
├── dependencies.py        # 依赖注入
├── routers/               # 路由模块
│   ├── novels.py          # 项目管理路由
│   └── workflow.py        # 工作流路由
├── schemas/               # Pydantic 模型
│   ├── novel.py
│   └── workflow.py
├── templates/             # Jinja2 模板
│   ├── base.html
│   ├── index.html
│   ├── workflow.html
│   └── error.html
└── static/                # 静态资源
    ├── css/
    └── js/
```

## 技术栈

- **后端框架**: FastAPI 0.104+
- **服务器**: Uvicorn (ASGI)
- **模板引擎**: Jinja2
- **前端交互**: HTMX 1.9
- **数据验证**: Pydantic 2.0+
- **配置管理**: Pydantic Settings
- **数据库**: SQLAlchemy 2.0 (通过 ainovel.db 模块)

## 开发建议

### 调试模式
在 `.env` 中设置：
```
DEBUG=true
RELOAD=true
```

### 查看日志
日志会输出到控制台（使用 loguru）：
```
2026-01-06 20:00:00 | INFO     | 🚀 AI小说创作系统 v0.1.0 启动中...
2026-01-06 20:00:00 | INFO     | ✅ 数据库初始化完成: sqlite:///data/ainovel.db
2026-01-06 20:00:00 | INFO     | 🌐 Web 服务器运行在 http://0.0.0.0:8000
```

### API 文档
访问 http://localhost:8000/docs 查看自动生成的 API 文档，支持在线测试。

## 常见问题

### Q: 如何切换 LLM 提供商？
A: 修改 `.env` 中的 `LLM_PROVIDER` 和 `LLM_MODEL`，并配置对应的 API 密钥。

### Q: 数据库文件在哪里？
A: 默认在 `data/ainovel.db`（SQLite），首次启动会自动创建。

### Q: 如何自定义端口？
A: 修改 `.env` 中的 `PORT` 配置。

### Q: 如何启用生产模式？
A: 设置 `DEBUG=false` 和 `RELOAD=false`，并使用生产级服务器：
```bash
uvicorn ainovel.web.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 下一步计划

- [ ] 完善 HTMX 组件（步骤4-6的交互）
- [ ] 添加角色管理页面
- [ ] 添加世界观管理页面
- [ ] 实现导出功能（EPUB/TXT）
- [ ] 添加用户认证（多用户支持）
- [ ] 实现流式输出（Server-Sent Events）
- [ ] 添加成本监控页面
