# LLM接入层开发 - 初步上下文分析

## 任务目标
实现aiNovel项目的LLM接入层，作为核心代码开发的第一步。

## 项目结构分析

### 当前状态
- **技术栈**: Python 3.10+, SQLAlchemy, OpenAI/Anthropic/DashScope SDK
- **项目路径**: `/Users/lee/Documents/github/me/aiNovel`
- **核心模块**:
  - `ainovel/llm/` - LLM接入层（当前为空，仅有`__init__.py`）
  - `ainovel/workflow/` - 6步流程编排
  - `ainovel/core/` - 生成核心
  - `ainovel/memory/` - 记忆管理
  - `ainovel/db/` - 数据持久化

### 依赖库（from pyproject.toml）
- **LLM SDK**:
  - `openai>=1.0.0` (OpenAI官方SDK)
  - `anthropic>=0.8.0` (Claude官方SDK)
  - `dashscope>=1.14.0` (阿里通义千问SDK)
- **工具库**:
  - `pydantic>=2.0.0` (数据验证)
  - `tenacity>=8.2.0` (重试机制)
  - `httpx>=0.25.0` (HTTP客户端)
  - `loguru>=0.7.0` (日志)
  - `tiktoken>=0.5.0` (Token计数)

### 已识别的相似案例
目前项目中没有既有的LLM接入实现，需要从零开始设计。

## 关键需求分析（from README.md）

### 功能需求
1. **多平台支持**: OpenAI/Claude/通义千问/文心一言（阶段1仅需前3个）
2. **成本监控**: 内置Token计数和成本估算
3. **分卷隔离**: 支持传入不同的上下文（全局设定 vs 当前卷设定）
4. **长文本生成**: 需要支持大纲、细纲、章节等不同长度的生成

### 架构约束
- 遵循SOLID原则（依赖倒置、接口隔离）
- 遵循DRY原则（复用重试、Token计数等逻辑）
- 必须使用抽象基类，便于后续扩展新平台

## 设计方向

### 核心类设计（初步）
1. **BaseLLMClient** (抽象基类)
   - 定义统一接口：`generate()`, `count_tokens()`, `estimate_cost()`
   - 内置重试机制（使用tenacity）
   - 内置日志（使用loguru）

2. **OpenAIClient** (实现类)
   - 封装OpenAI SDK
   - 支持gpt-4o, gpt-4o-mini等模型

3. **ClaudeClient** (实现类)
   - 封装Anthropic SDK
   - 支持claude-3-5-sonnet等模型

4. **QwenClient** (实现类)
   - 封装DashScope SDK
   - 支持qwen-max, qwen-turbo等模型

5. **LLMFactory** (工厂类)
   - 根据配置创建对应客户端
   - 管理API密钥

### 配置管理
- 使用Pydantic定义配置模型
- 支持从环境变量加载（`.env`文件）
- 支持运行时切换模型

### 错误处理
- API限流 → tenacity自动重试（指数退避）
- 网络错误 → 重试3次
- Token超限 → 抛出明确异常，由上层处理
- API密钥错误 → 启动时检查，快速失败

## 观察报告

### 信息充足之处
- ✅ 技术栈明确（三大LLM SDK已在依赖中）
- ✅ 工具库完备（pydantic, tenacity, loguru已配置）
- ✅ 架构方向清晰（分卷隔离、成本监控）

### 信息不足之处（关键疑问）
1. **优先级高**:
   - ❓ 各平台的Token计费规则是否需要精确统计？（影响成本监控设计）
   - ❓ 是否需要支持流式输出？（影响接口设计）
   - ❓ 错误重试次数和策略的具体配置？（影响tenacity配置）

2. **优先级中**:
   - ❓ 是否需要支持多轮对话？（影响上下文管理）
   - ❓ 日志级别和存储策略？（影响loguru配置）

3. **优先级低**:
   - ❓ 是否需要缓存机制？（影响性能优化）

### 建议深入方向
1. 查找是否有成本监控的具体实现方案（搜索文档或代码）
2. 确认流式输出的必要性（对用户体验的影响）
3. 查看`.env.example`确认配置项设计

## 下一步行动
1. 读取`.env.example`确认配置项
2. 针对关键疑问进行深挖（优先级高的3个问题）
3. 进入充分性检查阶段
