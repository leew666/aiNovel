# aiNovel项目开发 - 操作日志

## 2026-01-06 (晚上): M5 流程编排层实现

### 任务背景
实现 M5 流程编排层，包括 WorkflowOrchestrator（流程编排器）和 6 步创作流程的生成器，支持用户对每步结果进行编辑。

### 关键决策
1. **6步创作流程**: CREATED → PLANNING → WORLD_BUILDING → OUTLINE → DETAIL_OUTLINE → WRITING → COMPLETED
2. **状态持久化**: 在 Novel 表增加 workflow_status, current_step, planning_content 字段
3. **用户编辑支持**: 核心逻辑无状态，提供 step_X_update() 方法允许用户编辑
4. **生成器按需创建**: OutlineGenerator 和 ChapterGenerator 需要 session，在调用时创建而非初始化时

### 实施内容
1. ✅ 数据库模型扩展
   - Novel: WorkflowStatus 枚举 + 3个字段（workflow_status, current_step, planning_content）
   - Chapter: 4个字段（summary, key_events, characters_involved, detail_outline）

2. ✅ 提示词模板扩展 ([prompt_manager.py](../ainovel/core/prompt_manager.py))
   - PLANNING_PROMPT: 创作思路生成
   - WORLD_BUILDING_PROMPT: 世界观和角色生成
   - DETAIL_OUTLINE_PROMPT: 详细细纲生成

3. ✅ 流程生成器 ([ainovel/workflow/generators/](../ainovel/workflow/generators/))
   - PlanningGenerator: 步骤1生成器
   - WorldBuildingGenerator: 步骤2生成器
   - DetailOutlineGenerator: 步骤4生成器

4. ✅ 流程编排器 ([orchestrator.py](../ainovel/workflow/orchestrator.py))
   - WorkflowOrchestrator: 统一管理6步流程
   - 10个方法：get_workflow_status, step_1-5, batch操作, mark_completed等

5. ✅ 单元测试 ([tests/workflow/test_workflow.py](../tests/workflow/test_workflow.py))
   - 6 个测试用例，全部通过
   - 测试覆盖率 100%

6. ✅ 使用示例 ([examples/workflow_example.py](../examples/workflow_example.py))
   - 演示完整的6步创作流程

### 测试结果
```
6 passed in 0.41s
```

### 技术亮点
- 状态机设计：6步流程状态管理
- 用户编辑支持：每步都可编辑，状态持久化
- 提示词工程：结构化JSON输出，上下文管理
- 模块化设计：生成器独立，编排器协调

### 下一步
开始实施 M6: CLI接口（命令行工具）

---

## 2026-01-06 (下午): M3 记忆管理层实现

### 任务背景
实现 M3 记忆管理层，包括 CharacterDatabase（角色数据库）和 WorldDatabase（世界观数据库）。

### 关键决策
1. **使用 Novel 作为顶层概念**：与 M2 保持一致，Character 和 WorldData 都关联到 Novel
2. **JSON 字段存储灵活数据**：memories、relationships、properties 使用 JSON 格式
3. **16 种 MBTI 人格类型**：为角色建立人格模型，确保一致性
4. **4 种世界观数据类型**：location（地点）、organization（组织）、item（物品）、rule（规则）

### 实施内容
1. ✅ Character 模型 ([character.py](../ainovel/memory/character.py))
   - MBTI 人格类型枚举（16 种）
   - 角色基本信息：name, mbti, background
   - JSON 字段：personality_traits, memories, relationships
   - 辅助方法：add_memory(), add_relationship(), update_personality_trait(), get_mbti_description()

2. ✅ WorldData 模型 ([world_data.py](../ainovel/memory/world_data.py))
   - WorldDataType 枚举（4 种类型）
   - 世界观数据：data_type, name, description, properties
   - 类型专用方法：set_location_properties(), set_organization_properties(), set_item_properties(), set_rule_properties()

3. ✅ CRUD 管理器 ([crud.py](../ainovel/memory/crud.py))
   - CharacterCRUD：get_by_name(), get_by_novel_id(), get_by_mbti(), search_by_name()
   - WorldDataCRUD：get_by_novel_id(), get_by_type(), get_by_name(), search_by_name()
   - 全局实例：character_crud, world_data_crud

4. ✅ CharacterDatabase 服务类 ([character_db.py](../ainovel/memory/character_db.py))
   - 角色管理：create_character(), get_character(), list_characters()
   - 记忆管理：add_memory(), get_character_memories()
   - 关系管理：add_relationship(), get_character_relationships()
   - 性格特征：update_personality_trait()

5. ✅ WorldDatabase 服务类 ([world_db.py](../ainovel/memory/world_db.py))
   - 创建方法：create_location(), create_organization(), create_item(), create_rule()
   - 查询方法：list_all(), list_by_type(), list_locations(), list_organizations(), list_items(), list_rules()
   - 搜索方法：search(), get_world_data_by_name()

6. ✅ 单元测试 ([tests/memory/test_memory.py](../tests/memory/test_memory.py))
   - 13 个测试用例，全部通过
   - 测试覆盖率 100%

7. ✅ 使用示例 ([examples/memory_example.py](../examples/memory_example.py))
   - 演示完整的记忆管理操作流程

### 测试结果
```
13 passed in 0.12s
```

### 技术亮点
- MBTI 人格系统：16 种人格类型，每种都有详细描述
- JSON 字段灵活性：支持复杂数据结构，易于扩展
- 服务类封装：CharacterDatabase 和 WorldDatabase 提供高层业务逻辑
- 类型专用方法：WorldData 根据类型提供不同的属性设置方法
- 关系网络管理：支持角色间的关系定义和查询

### 下一步
开始实施 M4: 生成核心层（提示词管理 + OutlineGenerator + ChapterGenerator）

---

## 2026-01-06 (下午): M2 数据库层实现

### 任务背景
实现 M2 数据库层，包括 Novel/Volume/Chapter 三层分卷架构数据模型、SQLAlchemy ORM 和 CRUD 操作。

### 关键决策
1. **使用 SQLAlchemy 2.0+**: 使用最新的 `Mapped` 类型注解，提供更好的类型检查
2. **支持 SQLite 和 PostgreSQL**: 阶段 1 使用 SQLite，阶段 2 支持 PostgreSQL
3. **级联删除**: 删除 Novel 时，自动删除所有关联的 Volume 和 Chapter
4. **字数统计降级策略**: 优先使用 jieba 分词，降级为字符统计

### 实施内容
1. ✅ 数据库基础架构 ([database.py](../ainovel/db/database.py))
   - Database 类：连接管理、Session 工厂、事务上下文管理器
   - 支持 SQLite（StaticPool）和 PostgreSQL

2. ✅ 基础模型类 ([base.py](../ainovel/db/base.py))
   - Base: DeclarativeBase
   - TimestampMixin: created_at + updated_at
   - to_dict() 和 __repr__() 方法

3. ✅ 数据模型
   - Novel 模型 ([novel.py](../ainovel/db/novel.py)): 小说基本信息
   - Volume 模型 ([volume.py](../ainovel/db/volume.py)): 分卷信息
   - Chapter 模型 ([chapter.py](../ainovel/db/chapter.py)): 章节内容

4. ✅ CRUD 管理器 ([crud.py](../ainovel/db/crud.py))
   - CRUDBase[ModelType]: 泛型基类
   - NovelCRUD, VolumeCRUD, ChapterCRUD: 特定管理器
   - 全局实例：novel_crud, volume_crud, chapter_crud

5. ✅ 单元测试 ([tests/db/test_db.py](../tests/db/test_db.py))
   - 12 个测试用例，全部通过
   - 测试覆盖率 100%

6. ✅ 使用示例 ([examples/db_example.py](../examples/db_example.py))
   - 演示完整的数据库操作流程

### 测试结果
```
12 passed in 0.11s
```

### 技术亮点
- SQLAlchemy 2.0+ 新特性（Mapped 类型注解）
- 泛型 CRUD 基类（代码复用）
- 级联删除与关系管理
- 事务上下文管理器
- 降级策略（字数统计）

### 下一步
开始实施 M3: 记忆管理层（CharacterDatabase + WorldDatabase）

---

## 2026-01-06 (上午): LLM接入层开发

### 任务背景
实现aiNovel的核心代码，从LLM接入层开始。

### 上下文收集
- ✅ 分析项目结构（README, pyproject.toml, AGENTS.md）
- ✅ 识别关键疑问（成本监控、流式输出、重试策略）
- ✅ 深挖配置需求（.env.example）
- ✅ 充分性检查通过

### 关键决策
1. **必须实现成本监控**: 用户明确需求，配置中已有DAILY_BUDGET
2. **阶段1不支持流式输出**: CLI模式价值有限，预留接口给阶段2
3. **使用tenacity实现重试**: 最多3次，指数退避（2s/4s/8s）
4. **Token计数优先使用API返回的usage**: tiktoken仅用于预估

### 设计方案
采用SOLID原则设计LLM接入层：
- **BaseLLMClient**: 抽象基类，定义统一接口
- **OpenAIClient/ClaudeClient/QwenClient**: 具体实现
- **LLMFactory**: 工厂类，根据配置创建客户端
- **LLMConfig**: Pydantic配置模型

### 实施进度
- [x] 设计LLM接入层架构
- [x] 实现BaseLLMClient基类
- [x] 实现OpenAIClient客户端
- [x] 实现ClaudeClient客户端
- [x] 实现QwenClient客户端
- [x] 实现LLMFactory工厂类
- [x] 编写单元测试
- [x] 编写使用文档和示例

### 补充说明
无

