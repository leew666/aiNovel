# aiNovel 竞品分析报告

> 分析日期: 2026-02-24

## 分析项目列表

1. [oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui)
2. [SillyTavern/SillyTavern](https://github.com/SillyTavern/SillyTavern)
3. [KoboldAI/KoboldAI-Client](https://github.com/KoboldAI/KoboldAI-Client)
4. [YILING0013/AI_NovelGenerator](https://github.com/YILING0013/AI_NovelGenerator)
5. [BlinkDL/AI-Writer](https://github.com/BlinkDL/AI-Writer)
6. [THUDM/LongWriter](https://github.com/THUDM/LongWriter)
7. [MaoXiaoYuZ/Long-Novel-GPT](https://github.com/MaoXiaoYuZ/Long-Novel-GPT)
8. [raestrada/storycraftr](https://github.com/raestrada/storycraftr)
9. [302ai/302_novel_writing](https://github.com/302ai/302_novel_writing)

---

## 逐项分析

### 1. oobabooga/text-generation-webui
**定位**: 本地LLM通用推理前端

**亮点功能**:
- 多后端支持（llama.cpp / ExLlamaV3 / Transformers / TensorRT-LLM），一套UI切换
- OpenAI兼容API，支持tool-calling，可作为本地模型的API网关
- 消息分支/版本导航：可在任意节点分叉对话，类似git分支
- Notebook模式：自由续写，不受对话轮次限制
- 扩展系统：TTS、语音输入、翻译等插件生态

**对aiNovel参考价值**: ⭐⭐ 低
消息分支/版本导航设计值得参考，用于章节草稿的多版本管理。

---

### 2. SillyTavern/SillyTavern
**定位**: 角色扮演/互动叙事前端，3年活跃开发，300+贡献者

**亮点功能**:
- **WorldInfo（Lorebook）系统**：关键词触发式世界观注入，按需加载背景知识，不占满上下文
- **角色卡（Character Card）**：标准化角色描述格式，可导入导出共享
- Visual Novel模式：对话+立绘的视觉小说界面
- 多LLM后端统一接入（OpenAI/Claude/KoboldAI/NovelAI等）
- 第三方扩展系统 + TTS + 图像生成集成
- 移动端友好布局

**对aiNovel参考价值**: ⭐⭐⭐⭐⭐ 极高
Lorebook/WorldInfo的按需注入机制是解决长篇小说上下文窗口限制的成熟方案。角色卡标准化格式也值得借鉴。

---

### 3. KoboldAI/KoboldAI-Client
**定位**: AI辅助写作前端，支持小说/冒险/聊天三种模式

**亮点功能**:
- **Author's Note（作者注记）**：在上下文特定位置插入写作指令，实时引导AI风格和走向
- **Memory字段**：持久化背景信息，独立于对话历史
- 三模式切换：Novel / Adventure / Chatbot
- 支持Google Colab免费运行

**对aiNovel参考价值**: ⭐⭐⭐ 中
Author's Note机制（在prompt特定位置插入动态指令）可用于章节生成时动态注入"本章写作风格要求"。

---

### 4. YILING0013/AI_NovelGenerator
**定位**: 与aiNovel最相似的中文长篇小说生成器（已停止维护，2025/9/24）

**亮点功能**:
- **向量检索引擎（RAG）**：用embedding做长程上下文一致性维护
- **伏笔管理系统**：`plot_arcs.txt` 追踪剧情要点和伏笔
- **角色状态追踪**：`character_state.txt` 记录角色当前状态
- **定稿流程**：草稿→定稿时自动更新全局摘要+角色状态+向量库
- 一致性审校：检测剧情矛盾与逻辑冲突
- 支持Ollama本地模型

**对aiNovel参考价值**: ⭐⭐⭐⭐ 高
RAG向量检索 + 伏笔管理 + 定稿时状态同步这套组合是aiNovel目前缺少的。`plot_arcs.txt`伏笔追踪机制可直接参考实现。

---

### 5. BlinkDL/AI-Writer
**定位**: 基于RWKV模型的中文网文生成器（2022年项目，已过时）

**亮点功能**:
- 专门针对中文网文训练的RWKV模型（玄幻/言情分类模型）
- 特殊采样方法改善小模型生成质量

**对aiNovel参考价值**: ⭐ 极低
技术已过时，使用本地小模型，与aiNovel基于商业API的路线不同。

---

### 6. THUDM/LongWriter
**定位**: 清华大学研究项目，解决LLM单次输出超长文本（10000字+）的能力问题

**亮点功能**:
- **AgentWrite技术**：将长文本任务分解为子任务，逐段生成后拼接，突破模型单次输出长度限制
- 训练了专门的LongWriter-glm4-9b和LongWriter-llama3.1-8b模型
- 支持单次生成10000字以上连贯文本
- 提供LongBench-Write评测基准

**对aiNovel参考价值**: ⭐⭐⭐ 中
AgentWrite的分段生成+拼接思路与aiNovel的章节生成逻辑相通，其分段规划的prompt设计值得参考。该项目是学术研究，需自行部署模型。

---

### 7. MaoXiaoYuZ/Long-Novel-GPT
**定位**: 基于LLM+RAG的长篇小说Agent，支持百万字生成

**亮点功能**:
- **多线程并行生成**：50+线程同时创作不同章节，速度极快
- **导入现有小说改写**：拆书→提取剧情纲要→按用户意见修改
- **大纲-章节-正文三层扩写**：自上而下渐进式生成
- 实时显示API调用费用
- Docker一键部署
- 支持文心Novel/豆包等国产模型

**对aiNovel参考价值**: ⭐⭐⭐⭐ 高
多线程并行生成和导入现有小说改写是aiNovel明显缺少的功能。

---

### 8. raestrada/storycraftr
**定位**: CLI驱动的AI书籍创作助手，支持多语言

**亮点功能**:
- **behavior.txt行为文件**：用自然语言描述AI写作风格和约束，项目级别的写作规范
- LangChain集成：支持OpenAI/OpenRouter/Ollama多provider
- 本地Embedding（BAAI/bge-large-en-v1.5）
- 多语言支持（primary + alternate languages）

**对aiNovel参考价值**: ⭐⭐⭐ 中
behavior.txt写作规范文件的设计很优雅，相当于项目级别的写作风格配置。

---

### 9. 302ai/302_novel_writing
**定位**: Next.js全栈小说写作Web应用，UI最精良

**亮点功能**:
- **AI封面生成**：小说封面可AI生成或本地上传
- **侧边栏辅助+中央编辑器布局**：人工+AI混合编辑
- 多语言界面（中/英/日）
- 深色模式
- 技术栈：Next.js 14 + TypeScript + Jotai

**对aiNovel参考价值**: ⭐⭐⭐ 中
侧边栏辅助+中央编辑器的布局是目前最好的写作UI范式，aiNovel的Web界面可参考。

---

## 类似项目推荐

| 项目 | 特点 |
|------|------|
| [jackaduma/Recurrent-LLM](https://github.com/jackaduma/Recurrent-LLM) | RecurrentGPT论文实现，循环机制生成任意长度文本 |
| NovelAI | 商业产品，Lorebook系统最成熟，是SillyTavern WorldInfo的原型 |
| Sudowrite | 商业产品，Wormhole跳跃续写+Beat Sheet故事结构工具 |
| novelcrafter | 商业产品，Codex知识库管理世界观/角色/地点 |

---

## 对aiNovel的功能建议（优先级排序）

| 优先级 | 功能 | 参考来源 |
|--------|------|----------|
| 1 | Lorebook关键词触发式上下文注入 | SillyTavern |
| 2 | 多线程并行章节生成 | Long-Novel-GPT |
| 3 | RAG向量检索 + 伏笔追踪（plot_arcs） | AI_NovelGenerator |
| 4 | 导入现有小说改写功能 | Long-Novel-GPT |
| 5 | Author's Note动态写作指令注入 | KoboldAI |
| 6 | 侧边栏+编辑器Web界面布局 | 302ai |
