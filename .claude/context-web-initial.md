# Web 界面开发 - 初步上下文分析

## 任务目标
根据现有功能实现 Web 界面，为 aiNovel 项目提供可视化操作界面。

## 项目结构分析

### 当前状态
- **技术栈**: Python 3.10+, SQLAlchemy 2.0+
- **项目路径**: `/Users/lee/Documents/github/me/aiNovel`
- **核心模块**:
  - ✅ `ainovel/llm/` - LLM接入层（已完成：OpenAI/Claude/Qwen）
  - ✅ `ainovel/db/` - 数据库层（已完成：Novel/Volume/Chapter三层架构）
  - ✅ `ainovel/memory/` - 记忆管理（已完成：CharacterDB + WorldDB）
  - ✅ `ainovel/core/` - 生成核心（已完成：OutlineGenerator + ChapterGenerator）
  - ✅ `ainovel/workflow/` - 流程编排（已完成：WorkflowOrchestrator + 6步生成器）
  - ⚠️ `ainovel/web/` - Web界面（仅有空的 `__init__.py`）
  - 🔄 `ainovel/cli/` - CLI接口（待开发）

### 已实现功能（from operations-log.md）

#### 1. LLM接入层（M1）
- BaseLLMClient 抽象基类
- OpenAIClient/ClaudeClient/QwenClient 实现
- LLMFactory 工厂类
- 成本监控、重试机制、Token计数

#### 2. 数据库层（M2）
- Novel 模型：小说基本信息 + workflow_status + current_step + planning_content
- Volume 模型：分卷信息
- Chapter 模型：章节内容 + summary + key_events + detail_outline

#### 3. 记忆管理层（M3）
- Character 模型：16种MBTI人格 + memories + relationships
- WorldData 模型：location/organization/item/rule 四种类型

#### 4. 生成核心层（M4）
- OutlineGenerator：生成大纲
- ChapterGenerator：生成章节内容
- PromptManager：提示词管理

#### 5. 流程编排层（M5）
- WorkflowOrchestrator：管理6步创作流程
  - Step 1: Planning（创作思路）
  - Step 2: World Building（世界观和角色）
  - Step 3: Outline（大纲）
  - Step 4: Detail Outline（详细细纲）
  - Step 5: Writing（章节内容）
  - Step 6: Completed（标记完成）
- 每步都支持用户编辑

### 6步创作流程详解（from orchestrator.py）

#### 核心接口
```python
class WorkflowOrchestrator:
    # 状态查询
    get_workflow_status(session, novel_id) -> Dict

    # 步骤1：创作思路
    step_1_planning(session, novel_id, initial_idea=None) -> Dict
    step_1_update(session, novel_id, planning_content) -> Dict

    # 步骤2：世界观和角色
    step_2_world_building(session, novel_id) -> Dict

    # 步骤3：大纲
    step_3_outline(session, novel_id) -> Dict

    # 步骤4：详细细纲
    step_4_detail_outline(session, chapter_id) -> Dict
    step_4_batch_detail_outline(session, novel_id) -> Dict

    # 步骤5：章节内容
    step_5_writing(session, chapter_id, style_guide=None) -> Dict

    # 完成
    mark_completed(session, novel_id) -> Dict
```

#### 工作流状态机
```
CREATED → PLANNING → WORLD_BUILDING → OUTLINE → DETAIL_OUTLINE → WRITING → COMPLETED
```

## Web 框架选择分析

### README.md 中的计划
- 阶段2计划：FastAPI + HTMX Web界面（已注释在 pyproject.toml）
- 推荐的技术栈：
  ```python
  # "fastapi>=0.104.0",
  # "uvicorn>=0.24.0",
  # "jinja2>=3.1.2",
  ```

### 技术选型建议
1. **FastAPI** (后端框架)
   - 优势：异步支持、自动API文档、类型提示、与SQLAlchemy 2.0完美集成
   - 适用：已有Pydantic依赖，学习成本低

2. **HTMX** (前端交互)
   - 优势：无需React/Vue，服务端渲染，轻量级
   - 适用：简化开发，符合KISS原则

3. **Jinja2** (模板引擎)
   - 优势：FastAPI官方推荐，Python生态标准
   - 适用：服务端渲染HTML

4. **Tailwind CSS** (样式框架，可选)
   - 优势：快速构建美观界面
   - 备选：直接用简单CSS

## Web 界面设计方向

### 核心页面规划
1. **项目管理页**
   - 列表显示所有小说项目
   - 创建新项目
   - 查看项目状态（workflow_status）

2. **6步流程页**（核心页面）
   - 顶部：进度条显示当前步骤（1-6）
   - Step 1：思路讨论
     - 输入框：初始想法
     - 按钮：生成创作思路
     - 编辑区：可编辑JSON结果
   - Step 2：世界观和角色
     - 按钮：生成世界观
     - 展示：角色列表 + 世界观数据
   - Step 3：大纲
     - 按钮：生成大纲
     - 展示：卷列表 + 章节列表
   - Step 4：详细细纲
     - 选择章节
     - 按钮：生成细纲 / 批量生成
     - 展示：场景列表
   - Step 5：章节创作
     - 选择章节
     - 输入：文风指南（可选）
     - 按钮：生成内容
     - 展示：章节内容
   - Step 6：完成
     - 按钮：标记完成
     - 导出：EPUB/TXT（阶段3）

3. **角色管理页**
   - 列表：所有角色 + MBTI
   - 详情：记忆 + 关系网络
   - 编辑：性格特征

4. **世界观管理页**
   - 分类显示：地点/组织/物品/规则
   - 搜索功能

5. **成本监控页**（可选）
   - Token使用统计
   - 成本预估

### 用户交互流程
```
1. 创建项目 → 输入小说名称、描述
2. 进入6步流程页
3. 每步操作：
   - 点击"生成"按钮
   - 等待进度提示（HTMX局部刷新）
   - 查看结果
   - 可选编辑
   - 点击"下一步"
4. 完成创作 → 导出/查看
```

## 关键疑问（优先级排序）

### 优先级高
1. ✅ **接口设计**: WorkflowOrchestrator 已提供完整接口，无需修改
2. ❓ **流式输出**: 是否需要实时显示生成进度？（影响用户体验）
3. ❓ **数据库连接**: FastAPI 如何管理 SQLAlchemy Session？（依赖注入）

### 优先级中
4. ❓ **文件上传**: 阶段3文风学习需要上传参考作品，现在是否预留接口？
5. ❓ **用户认证**: 是否需要多用户支持？（影响数据隔离）
6. ❓ **前端复杂度**: 是否需要实时预览（如章节内容）？（影响HTMX vs React选择）

### 优先级低
7. ❓ **部署方式**: Docker化还是直接运行？
8. ❓ **静态资源**: CSS/JS 如何组织？

## 技术约束

### 必须遵循（from CLAUDE.md）
- ✅ 使用简体中文注释
- ✅ 遵循SOLID + DRY原则
- ✅ 每次改动必须本地验证
- ✅ 复用现有模块（不自研）
- ✅ 禁止MVP/占位符，必须完整实现

### 测试要求
- 单元测试：FastAPI 提供 TestClient
- 集成测试：模拟完整6步流程
- 必须本地 AI 自动执行

## 观察报告

### 信息充足之处
- ✅ 后端逻辑完整（WorkflowOrchestrator 提供所有接口）
- ✅ 数据模型完善（Novel/Volume/Chapter + Character + WorldData）
- ✅ 技术选型明确（FastAPI + HTMX 已在README规划）
- ✅ 6步流程清晰（每步都有 generate 和 update 接口）

### 信息不足之处
- ❓ 是否需要流式输出（影响接口设计：同步 vs 异步）
- ❓ 数据库 Session 管理策略（影响 FastAPI 依赖注入设计）
- ❓ 是否需要 WebSocket（实时进度）

### 建议深入方向
1. 查找 FastAPI + SQLAlchemy 2.0 的最佳实践（Session管理）
2. 确认是否需要流式输出（查看 BaseLLMClient 是否支持）
3. 设计 RESTful API 接口规范

## 下一步行动
1. 深挖疑问1-3（高优先级）
2. 设计 FastAPI 路由结构
3. 进入充分性检查阶段
