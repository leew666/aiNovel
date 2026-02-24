# GitHub AI 小说创作项目对比（2026-02-24）

本文档用于沉淀一次公开仓库调研结果，作为本项目功能规划参考。

## 调研范围

- 数据时间：2026-02-24（UTC）
- 数据来源：
  - GitHub API（`/repos`、`/search/repositories`）
  - 各仓库 README
- 关注维度：
  - 社区认可度：Stars / Forks
  - 活跃度：最近更新时间、最近推送时间
  - 功能价值：是否可直接迁移到 AI 长篇小说创作场景

## 候选仓库概览

| 仓库 | Stars | Forks | Open Issues | 最近推送 | License | 定位 |
|---|---:|---:|---:|---|---|---|
| `oobabooga/text-generation-webui` | 46080 | 5885 | 2661 | 2026-02-03 | AGPL-3.0 | 本地 LLM 通用前端，生态最强 |
| `SillyTavern/SillyTavern` | 23464 | 4780 | 375 | 2026-02-23 | AGPL-3.0 | 角色/剧情创作前端，扩展能力强 |
| `KoboldAI/KoboldAI-Client` | 3857 | 853 | 121 | 2025-01-16 | AGPL-3.0 | 经典 AI 写作工具，偏旧 |
| `BlinkDL/AI-Writer` | 3552 | 560 | 17 | 2025-05-15 | Apache-2.0 | 中文网文生成先驱（README 标注过时） |
| `YILING0013/AI_NovelGenerator` | 3461 | 645 | 58 | 2025-12-22 | AGPL-3.0 | 面向长篇小说的一体化生成 |
| `THUDM/LongWriter` | 1831 | 182 | 30 | 2025-06-24 | Apache-2.0 | 长文本生成研究与模型能力 |
| `MaoXiaoYuZ/Long-Novel-GPT` | 1001 | 182 | 31 | 2025-11-05 | NOASSERTION | 长篇小说 Agent 流程化生成 |
| `raestrada/storycraftr` | 110 | 21 | 12 | 2026-02-14 | MIT | CLI 写作流水线（结构化） |
| `302ai/302_novel_writing` | 11 | 3 | 0 | 2025-08-26 | Apache-2.0 | Web 端 AI 写作产品化样例 |

## 高评价功能（优先借鉴）

### 1) 分层生成流水线（大纲 -> 章节 -> 正文）

- 代表项目：`MaoXiaoYuZ/Long-Novel-GPT`、`raestrada/storycraftr`
- 价值：
  - 将“创意”与“扩写”职责解耦，降低一次生成失败的成本
  - 有利于局部重试和质量闸门插入
- 原则映射：
  - `KISS`：流程直观
  - `SOLID(SRP)`：每阶段单一职责

### 2) 上下文记忆 + 一致性检查

- 代表项目：`YILING0013/AI_NovelGenerator`、`KoboldAI/KoboldAI-Client`
- 价值：
  - 抑制人物设定漂移、时间线冲突、伏笔遗失
  - 长篇续写时显著提升连贯性
- 原则映射：
  - `DRY`：复用世界观/角色信息，避免重复喂上下文
  - `KISS`：统一记忆入口和检查入口

### 3) 局部改写与版本分支编辑

- 代表项目：`MaoXiaoYuZ/Long-Novel-GPT`、`oobabooga/text-generation-webui`
- 价值：
  - 只改坏片段，不重生成整章，节省 token 与人工校对时间
  - 支持多版本分叉对比，降低创作试错成本
- 原则映射：
  - `YAGNI`：先做必要的“局部可控”，不追求全自动一次成稿

### 4) 多后端模型适配层（OpenAI/OpenRouter/Ollama/本地）

- 代表项目：`SillyTavern/SillyTavern`、`oobabooga/text-generation-webui`、`raestrada/storycraftr`
- 价值：
  - 模型供应切换成本低
  - 有助于成本/质量按场景动态切换
- 原则映射：
  - `SOLID(DIP/OCP)`：依赖抽象接口，新增提供方尽量不改核心流程

### 5) 插件化扩展机制

- 代表项目：`SillyTavern/SillyTavern`、`oobabooga/text-generation-webui`
- 价值：
  - 核心保持稳定，功能通过扩展生长
  - 社区贡献路径清晰，降低主干复杂度
- 原则映射：
  - `OCP`：对扩展开放，对核心修改封闭

### 6) 离线优先与隐私写作

- 代表项目：`oobabooga/text-generation-webui`
- 价值：
  - 小说草稿隐私保护更强
  - 对企业/敏感题材场景更友好
- 原则映射：
  - `KISS`：部署路径清晰，用户心智负担低

## 对本项目的落地优先级建议

1. 构建“上下文压缩器 + 角色/世界观记忆卡 + 一致性检查”最小闭环。  
2. 固化“大纲 -> 章节 -> 正文”的可回滚流水线。  
3. 增加“局部改写/重写”入口，支持片段级重生成。  
4. 统一 LLM Provider 适配接口，隔离具体模型实现。  
5. 最后引入插件点（检索、审校、风格迁移等）。

## 风险与注意事项

- 高星仓库不等于直接可复用，需二次评估代码质量、许可协议与维护状态。
- AGPL 项目作为参考实现可行，但代码复用需审慎处理许可证影响。
- 研究型项目（如 `THUDM/LongWriter`）更适合作为能力与评测参考，不一定是完整产品方案。

## 参考链接

- https://github.com/oobabooga/text-generation-webui
- https://github.com/SillyTavern/SillyTavern
- https://github.com/KoboldAI/KoboldAI-Client
- https://github.com/YILING0013/AI_NovelGenerator
- https://github.com/BlinkDL/AI-Writer
- https://github.com/THUDM/LongWriter
- https://github.com/MaoXiaoYuZ/Long-Novel-GPT
- https://github.com/raestrada/storycraftr
- https://github.com/302ai/302_novel_writing
