# M5 流程编排层实现总结

**实施时间**: 2026-01-06
**状态**: ✅ 已完成
**测试结果**: 6/6 通过，所有workflow测试通过

---

## 实现内容

### 1. 数据库模型扩展

#### Novel 模型扩展 ([ainovel/db/novel.py](../ainovel/db/novel.py))

**新增枚举**:
- `WorkflowStatus`: 创作流程状态枚举
  - `CREATED`: 已创建
  - `PLANNING`: 规划中（步骤1）
  - `WORLD_BUILDING`: 世界构建中（步骤2）
  - `OUTLINE`: 大纲生成中（步骤3）
  - `DETAIL_OUTLINE`: 细纲生成中（步骤4）
  - `WRITING`: 写作中（步骤5）
  - `COMPLETED`: 已完成

**新增字段**:
```python
workflow_status: Mapped[WorkflowStatus]  # 创作流程状态
current_step: Mapped[int]                # 当前步骤（0-5）
planning_content: Mapped[str | None]     # 步骤1：创作思路内容
```

#### Chapter 模型扩展 ([ainovel/db/chapter.py](../ainovel/db/chapter.py))

**新增字段**:
```python
summary: Mapped[str | None]              # 章节概要（用于大纲）
key_events: Mapped[str | None]           # 关键事件列表（JSON格式）
characters_involved: Mapped[str | None]  # 涉及角色列表（JSON格式）
detail_outline: Mapped[str | None]       # 步骤4：详细细纲内容
```

### 2. 提示词模板扩展 ([ainovel/core/prompt_manager.py](../ainovel/core/prompt_manager.py))

**新增模板**:
1. **PLANNING_PROMPT**: 创作思路生成提示词
   - 输入：用户的模糊想法
   - 输出：结构化创作计划（题材、主题、核心冲突、篇幅估算等）

2. **WORLD_BUILDING_PROMPT**: 世界背景和角色生成提示词
   - 输入：创作思路
   - 输出：世界观数据 + 角色列表（JSON格式）

3. **DETAIL_OUTLINE_PROMPT**: 详细细纲生成提示词
   - 输入：大纲
   - 输出：每章的详细场景分解（JSON格式）

**新增方法**:
```python
PromptManager.generate_planning_prompt(initial_idea)
PromptManager.generate_world_building_prompt(planning_content)
PromptManager.generate_detail_outline_prompt(...)
```

### 3. 流程生成器模块 ([ainovel/workflow/generators/](../ainovel/workflow/generators/))

#### PlanningGenerator ([planning_generator.py](../ainovel/workflow/generators/planning_generator.py))

**核心功能**:
- 根据用户的模糊想法生成详细创作思路
- 解析LLM输出的JSON格式计划

**关键方法**:
```python
result = generator.generate_planning(initial_idea)
# 返回: {"planning": {...}, "usage": {...}, "cost": 0.01}
```

#### WorldBuildingGenerator ([world_building_generator.py](../ainovel/workflow/generators/world_building_generator.py))

**核心功能**:
- 根据创作思路生成世界观和角色
- 自动保存到数据库（WorldData + Character）

**关键方法**:
```python
result = generator.generate_and_save(session, novel_id, planning_content)
# 返回: {"world_building": {...}, "stats": {"world_data_created": 5, "characters_created": 4}}
```

#### DetailOutlineGenerator ([detail_outline_generator.py](../ainovel/workflow/generators/detail_outline_generator.py))

**核心功能**:
- 为每个章节生成详细细纲
- 场景分解、对话要点、情节转折、伏笔标注

**关键方法**:
```python
result = generator.generate_and_save(session, chapter_id)
# 返回: {"detail_outline": {...}, "stats": {"scenes_count": 5}}
```

### 4. 流程编排器 ([ainovel/workflow/orchestrator.py](../ainovel/workflow/orchestrator.py))

**核心类**: `WorkflowOrchestrator`

**流程管理方法**:
```python
# 获取工作流状态
orchestrator.get_workflow_status(session, novel_id)

# 步骤1：生成创作思路
orchestrator.step_1_planning(session, novel_id)
orchestrator.step_1_update(session, novel_id, planning_content)  # 用户编辑

# 步骤2：生成世界观和角色
orchestrator.step_2_world_building(session, novel_id)

# 步骤3：生成大纲
orchestrator.step_3_outline(session, novel_id)

# 步骤4：生成细纲
orchestrator.step_4_detail_outline(session, chapter_id)  # 单章
orchestrator.step_4_batch_detail_outline(session, novel_id)  # 批量

# 步骤5：生成章节内容
orchestrator.step_5_writing(session, chapter_id, style_guide)

# 标记完成
orchestrator.mark_completed(session, novel_id)
```

**用户编辑支持**:
- 每步生成后返回结果
- 提供 `step_X_update()` 方法允许用户编辑
- 状态持久化到数据库

---

## 测试验证

### 测试文件: [tests/workflow/test_workflow.py](../tests/workflow/test_workflow.py)

**测试用例（6个）**:

#### PlanningGenerator (1个)
1. ✅ `test_generate_planning`: 测试生成创作思路

#### WorldBuildingGenerator (1个)
2. ✅ `test_generate_world_building`: 测试生成世界观和角色

#### DetailOutlineGenerator (1个)
3. ✅ `test_generate_detail_outline`: 测试生成详细细纲

#### WorkflowOrchestrator (3个)
4. ✅ `test_get_workflow_status`: 测试获取工作流状态
5. ✅ `test_step_1_planning`: 测试步骤1生成创作思路
6. ✅ `test_step_1_update`: 测试步骤1用户编辑

**测试结果**:
```
6 passed in 0.41s
```

### 示例脚本: [examples/workflow_example.py](../examples/workflow_example.py)

演示了完整的6步创作流程：
1. 初始化数据库
2. 创建小说
3. 步骤1：生成创作思路
4. 步骤2：生成世界观和角色
5. 步骤3：生成大纲
6. 步骤4：批量生成细纲
7. 步骤5：生成第一章内容
8. 标记完成

---

## 技术亮点

### 1. 状态机设计

**工作流状态管理**:
```
CREATED → PLANNING → WORLD_BUILDING → OUTLINE → DETAIL_OUTLINE → WRITING → COMPLETED
```

**状态持久化**:
- `workflow_status`: 当前流程状态
- `current_step`: 当前步骤编号（0-5）
- 每步完成后自动更新

### 2. 用户编辑支持

**设计原则**:
- 核心逻辑无状态（不含 `input()`）
- 每步返回结果和元数据
- CLI 层负责展示和收集用户输入
- 阶段2可直接复用 WorkflowOrchestrator

**编辑流程**:
```python
# 生成
result = orchestrator.step_1_planning(session, novel_id)

# 用户编辑（可选）
edited_content = user_edit(result["planning"])
orchestrator.step_1_update(session, novel_id, edited_content)

# 继续下一步
orchestrator.step_2_world_building(session, novel_id)
```

### 3. 提示词工程

**结构化输出**:
- 统一使用JSON格式规范LLM输出
- 提供详细的输出格式说明和示例
- 自动解析并验证JSON

**上下文管理**:
- 步骤1：分析用户想法的核心要素
- 步骤2：基于创作思路生成世界观
- 步骤4：基于大纲生成场景分解

### 4. 模块化设计

**生成器独立**:
- PlanningGenerator: 不依赖数据库
- WorldBuildingGenerator: 依赖 CharacterDB + WorldDB
- DetailOutlineGenerator: 依赖 ChapterCRUD

**编排器协调**:
- 统一管理6步流程
- 自动创建所需的生成器实例
- 状态转换和持久化

---

## 文件结构

```
ainovel/
├── db/
│   ├── novel.py            # +WorkflowStatus枚举, +3个字段
│   └── chapter.py          # +4个字段（summary, key_events等）
├── core/
│   └── prompt_manager.py   # +3个提示词模板, +3个方法
└── workflow/
    ├── __init__.py
    ├── orchestrator.py     # 流程编排器
    └── generators/
        ├── __init__.py
        ├── planning_generator.py
        ├── world_building_generator.py
        └── detail_outline_generator.py

tests/workflow/
├── __init__.py
└── test_workflow.py        # 单元测试

examples/
└── workflow_example.py     # 使用示例
```

---

## 设计原则体现

### SOLID 原则

- **单一职责**: 每个生成器只负责一个步骤
- **开放/封闭**: 通过子类化可扩展新步骤
- **依赖倒置**: 依赖 `BaseLLMClient` 接口

### DRY 原则

- 提示词模板集中管理
- 生成器复用 PromptManager
- 统一的 JSON 解析逻辑

### KISS 原则

- 流程步骤清晰明了（1-5步）
- 用户编辑接口简单
- 状态转换自动化

---

## 与用户需求的对应

根据 [thaught.md](../thaught.md) 的需求：

✅ **步骤1（3-1）**: 根据模糊想法生成明确的创作思路 → `PlanningGenerator`
✅ **步骤2（3-2）**: 生成世界背景、角色 → `WorldBuildingGenerator`
✅ **步骤3（3-3）**: 生成作品大纲 → `OutlineGenerator`（已有）
✅ **步骤4（3-4）**: 生成作品细纲 → `DetailOutlineGenerator`
✅ **步骤5（3-5）**: 根据细纲创作内容 → `ChapterGenerator`（已有）
✅ **用户编辑支持**: 每步都可编辑结果 → `step_X_update()` 方法

---

## 后续计划

### 阶段1剩余任务

1. **M6: CLI接口** (命令行工具)
   - 封装 WorkflowOrchestrator 为CLI命令
   - 提供交互式编辑界面
   - 进度展示和错误处理

### 流程编排层潜在改进（后续考虑）

1. **断点续写**: 支持从任意步骤恢复
2. **版本管理**: 保存每步的历史版本
3. **分支流程**: 支持多个并行创作方向
4. **质量评估**: 自动评估生成结果质量
5. **智能推荐**: 基于已有内容推荐下一步操作

---

**实现完成**: 2026-01-06
**下一步**: 开始实施 M6 CLI接口

