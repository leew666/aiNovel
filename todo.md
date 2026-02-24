# 三项高优先级迭代清单（按当前仓库结构）

目标：把“上下文压缩 + 记忆卡 + 一致性检查”“大纲到正文流水线”“局部改写 + 模型适配”拆成可直接执行的开发任务。  
原则：KISS、YAGNI、DRY、SOLID。

## 迭代1：上下文压缩器 + 记忆卡 + 一致性检查

### 1.1 文件级改动

- [x] 修改 `ainovel/core/context_compressor.py`  
新增 `build_context_bundle(...)`，统一输出前情摘要、角色记忆卡、世界观卡片，替代分散拼接逻辑。

- [x] 修改 `ainovel/core/prompt_manager.py`  
扩展 `generate_chapter_prompt(...)` 入参，增加 `character_memory_cards`、`world_memory_cards`；新增 `CONSISTENCY_CHECK_PROMPT` 模板。

- [x] 修改 `ainovel/memory/character_db.py`  
新增 `get_memory_cards(novel_id: int, character_names: list[str], limit_per_character: int = 3) -> list[dict]`。

- [x] 修改 `ainovel/memory/world_db.py`  
新增 `get_world_cards(novel_id: int, keywords: list[str], limit: int = 8) -> list[dict]`。

- [x] 新增 `ainovel/workflow/generators/consistency_generator.py`  
负责“章节草稿 vs 角色/世界观/前情”的冲突检测与结构化输出。

- [x] 修改 `ainovel/core/chapter_generator.py`  
接入 `build_context_bundle(...)`；在生成后可选调用一致性检查器。

- [x] 修改 `ainovel/web/schemas/workflow.py`  
新增 `ConsistencyCheckRequest`、`ConsistencyCheckResponse`。

- [x] 修改 `ainovel/web/routers/workflow.py`  
新增 `POST /workflow/chapter/{chapter_id}/consistency-check`。

### 1.2 接口级定义（先定签名再实现）

- [x] Python 服务接口  
`ContextCompressor.build_context_bundle(volume_id: int, current_order: int, token_budget: int = 1200) -> dict[str, str]`

- [x] Python 服务接口  
`ConsistencyGenerator.check_chapter(session: Session, chapter_id: int, content: str) -> dict[str, Any]`

- [x] HTTP 接口  
`POST /workflow/chapter/{chapter_id}/consistency-check`  
请求：`{ "content_override": "可选", "strict": false }`  
响应：`{ "chapter_id": 1, "overall_risk": "low|medium|high", "issues": [...] }`

### 1.3 验收标准

- [x] 章节生成提示词中可见“前情 + 角色记忆卡 + 世界观卡片”三个区块。  
- [x] 一致性检查返回结构化问题（位置、冲突类型、修复建议）。  
- [x] 旧接口兼容（不传新参数时行为不变）。  

### 1.4 测试落点

- [x] 新增 `tests/core/test_context_bundle.py`  
- [x] 新增 `tests/workflow/test_consistency_generator.py`  
- [x] 更新 `tests/core/test_context_compressor.py`

---

## 迭代2：固化“大纲 -> 章节 -> 正文”可回滚流水线

### 2.1 文件级改动

- [x] 修改 `ainovel/workflow/orchestrator.py`
新增统一流水线入口 `run_pipeline(...)`；增加步骤前置校验、幂等保护、失败回滚点。

- [x] 新增 `ainovel/workflow/pipeline_runner.py`
封装批量运行、重试策略、失败章节收集，避免 `orchestrator.py` 继续膨胀（SRP）。

- [x] 修改 `ainovel/web/schemas/workflow.py`
新增 `PipelineRunRequest`、`PipelineRunResponse`、`PipelineTaskResult`。

- [x] 修改 `ainovel/web/routers/workflow.py`
新增 `POST /workflow/{novel_id}/pipeline/run`、`GET /workflow/{novel_id}/pipeline/status`。

- [x] 修改 `ainovel/cli/main.py`
新增命令：`ainovel pipeline-run <novel_id> --from-step 3 --to-step 5 --chapters 1-10`。

### 2.2 接口级定义

- [x] Python 服务接口
`WorkflowOrchestrator.run_pipeline(session: Session, novel_id: int, from_step: int, to_step: int, chapter_range: str | None = None, regenerate: bool = False) -> dict[str, Any]`

- [x] Python 服务接口
`PipelineRunner.run(session: Session, novel_id: int, plan: dict[str, Any]) -> dict[str, Any]`

- [x] HTTP 接口
`POST /workflow/{novel_id}/pipeline/run`
请求：`{ "from_step": 3, "to_step": 5, "chapter_range": "1-20", "regenerate": false }`

- [x] HTTP 接口
`GET /workflow/{novel_id}/pipeline/status`
响应：当前任务状态、已完成章节、失败章节、可重试章节。

### 2.3 验收标准

- [x] 支持从任意合法步骤恢复执行（例如 3 -> 5）。
- [x] 支持按章节范围批量生成。
- [x] 某章节失败不阻塞整体，失败项可二次重跑。

### 2.4 测试落点

- [x] 新增 `tests/workflow/test_pipeline_runner.py`
- [ ] 更新 `tests/workflow/test_workflow.py`
- [ ] 新增 `tests/web/test_workflow_pipeline_api.py`

---

## 迭代3：局部改写/重写 + 模型适配层增强

### 3.1 文件级改动

- [ ] 新增 `ainovel/core/chapter_rewriter.py`  
提供段落级改写（润色/扩写/删减/风格迁移）与整章重写能力。

- [ ] 修改 `ainovel/core/prompt_manager.py`  
新增 `REWRITE_PROMPT`、`POLISH_PROMPT`、`EXPAND_PROMPT` 模板。

- [ ] 修改 `ainovel/web/schemas/workflow.py`  
新增 `ChapterRewriteRequest`、`ChapterRewriteResponse`。

- [ ] 修改 `ainovel/web/routers/workflow.py`  
新增 `POST /workflow/chapter/{chapter_id}/rewrite`。

- [ ] 修改 `ainovel/llm/base.py`  
补充可选能力接口（JSON 输出模式、结构化响应能力声明）。

- [ ] 修改 `ainovel/llm/factory.py`  
增加 Provider 注册机制：`register_provider(name, client_cls)`，减少硬编码分支。

- [ ] 修改 `ainovel/web/routers/settings.py`  
设置页读取可用 provider 列表时，兼容“动态注册 provider”。

### 3.2 接口级定义

- [ ] Python 服务接口  
`ChapterRewriter.rewrite(chapter_id: int, instruction: str, target_scope: str = "paragraph", range_start: int | None = None, range_end: int | None = None, preserve_plot: bool = True) -> dict[str, Any]`

- [ ] Python 服务接口  
`LLMFactory.register_provider(name: str, client_cls: type[BaseLLMClient]) -> None`

- [ ] HTTP 接口  
`POST /workflow/chapter/{chapter_id}/rewrite`  
请求：`{ "instruction": "强化冲突", "target_scope": "paragraph", "range_start": 3, "range_end": 6 }`  
响应：`{ "chapter_id": 1, "new_content": "...", "diff_summary": "...", "usage": {...} }`

### 3.3 验收标准

- [ ] 支持“指定段落范围”改写，不必整章重生。  
- [ ] 改写后保留原文版本快照，支持回滚。  
- [ ] 新增 provider 无需改动核心业务流程代码。  

### 3.4 测试落点

- [ ] 新增 `tests/core/test_chapter_rewriter.py`  
- [ ] 更新 `tests/llm/test_llm.py`（注册机制与兼容性）  
- [ ] 新增 `tests/web/test_chapter_rewrite_api.py`

---

## 建议执行顺序（两周节奏）

- [ ] Week 1 上半：迭代1（上下文 + 一致性）  
- [ ] Week 1 下半：迭代2（流水线运行与回滚）  
- [ ] Week 2：迭代3（局部改写 + 适配层）  

## 完成定义（DoD）

- [ ] 每项迭代至少 1 个新增 API + 1 组自动化测试。  
- [ ] 每项迭代更新 `README.md` 的功能说明与调用示例。  
- [ ] 所有新增/修改文件统一 UTF-8（无 BOM）。  
