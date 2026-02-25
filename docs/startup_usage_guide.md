# aiNovel 项目分析与启动使用指南

更新时间：2026-02-24

## 1. 项目分析（当前代码基线）

### 1.1 架构与模块

当前项目是典型分层结构：

- `ainovel/cli/`：命令行入口（项目管理 + 步骤化创作）
- `ainovel/web/`：FastAPI 服务与页面模板
- `ainovel/workflow/`：创作流程编排（Step1~Step6）
- `ainovel/core/`：大纲与章节生成核心
- `ainovel/memory/`：角色与世界观数据管理
- `ainovel/llm/`：多模型接入（OpenAI / Claude / Qwen）
- `ainovel/db/`：SQLAlchemy 模型与 CRUD

### 1.2 当前可用能力

- CLI 支持：`create-project`、`list-projects`、`step1`~`step5`、`complete`
- Web API 支持：项目 CRUD、工作流状态、Step1~Step6 接口
- 数据库默认：SQLite（`data/ainovel.db`）
- 已验证测试：`pytest -q` 通过（`78 passed`）

### 1.3 当前限制（使用前建议知悉）

- Web 模板页面仍在迭代中，实际生产建议优先使用 CLI 或 `/docs` 中的 API 调试页面。
- CLI 目前未提供 `step6` 命令；质量检查步骤可通过 Web API 调用。

---

## 2. 启动指南

### 2.1 环境要求

- Python `>=3.10`
- 至少一个 LLM 平台 API Key（OpenAI / Anthropic / DashScope）

### 2.2 安装依赖

```bash
git clone <your-repo-url>
cd aiNovel

# 1) 创建虚拟环境
python3 -m venv .venv

# 2) 激活虚拟环境（macOS/Linux）
source .venv/bin/activate

# 2') 激活虚拟环境（Windows PowerShell）
# .venv\Scripts\Activate.ps1

# 3) 安装项目
pip install -e .
```

### 2.3 环境变量配置

```bash
cp .env.example .env
```

最小配置示例（建议同时覆盖 CLI 与 Web）：

```env
# API Key（至少一个）
OPENAI_API_KEY=sk-xxx
# ANTHROPIC_API_KEY=...
# DASHSCOPE_API_KEY=...

# CLI 使用
DEFAULT_LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# Web 使用
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# 数据库
DATABASE_URL=sqlite:///data/ainovel.db
```

---

## 3. 使用说明

## 3.1 CLI 工作流

> 如果命令 `ainovel` 不存在，请先确认执行过 `pip install -e .`，或者使用 `python -m ainovel.cli.main` 代替。

### 1）查看可用命令

```bash
ainovel --help
```

### 2）创建项目

```bash
ainovel create-project "修仙废材逆袭" --author "AI创作" --genre "玄幻"
ainovel list-projects
```

记下项目 ID（下面示例按 `1` 演示）。

### 3）执行创作流程

```bash
# Step1 创作思路
ainovel step1 1 --idea "一个被退婚的废材少年，偶然获得神秘戒指"

# Step2 世界观与角色
ainovel step2 1

# Step3 大纲
ainovel step3 1

# Step4 细纲（批量）
ainovel step4 1 --batch

# Step5 章节创作（章节序号范围）
ainovel step5 1 --chapters 1-3

# 标记流程完成
ainovel complete 1
```

---

## 3.2 Web （推荐）

source .venv/bin/activate

### 1）启动服务

```bash
python -m uvicorn ainovel.web.main:app --reload
```

访问地址：

- 首页：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

### 2）API 最小调用顺序（示例）

```bash
# 创建小说
curl -X POST "http://127.0.0.1:8000/novels/" \
  -H "Content-Type: application/json" \
  -d '{"title":"修仙废材逆袭","description":"主角从底层崛起","author":"AI","genre":"玄幻"}'

# 假设 novel_id=1
# Step1
curl -X POST "http://127.0.0.1:8000/workflow/1/step1" \
  -H "Content-Type: application/json" \
  -d '{"initial_idea":"一个被退婚的废材少年，偶然获得神秘戒指"}'

# Step2
curl -X POST "http://127.0.0.1:8000/workflow/1/step2"

# Step3
curl -X POST "http://127.0.0.1:8000/workflow/1/step3"
```

补充：

- Step4（批量细纲）：`POST /workflow/{novel_id}/step4/batch`
- Step5（单章创作）：`POST /workflow/chapter/{chapter_id}/step5`，Body 至少传 `{}` 或 `{"style_guide":"..."}`  
- Step6（质量检查）：`POST /workflow/chapter/{chapter_id}/step6` 或 `POST /workflow/{novel_id}/step6/batch`

---

## 4. 常见问题

### Q1：`ainovel: command not found`

- 原因：未安装 editable package。
- 处理：执行 `pip install -e .`，或临时使用 `python -m ainovel.cli.main ...`。

### Q2：提示 API 密钥未配置

- 检查 `.env` 是否存在且字段名正确（尤其区分 CLI 的 `DEFAULT_LLM_PROVIDER` 与 Web 的 `LLM_PROVIDER`）。
- 至少配置当前 provider 对应的 key。

### Q3：数据库文件在哪里

- 默认路径：`data/ainovel.db`。

---

## 5. 开发建议

- 提交前运行：`pytest -q`
- 先走 CLI 主链路，再补充 Web/API 验证，可以更快定位流程问题。
