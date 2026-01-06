# AI小说创作系统 (aiNovel)

> 基于商业LLM API的长篇小说自动化创作系统,支持300万字分卷创作,具备防剧透机制和强大的人物一致性保障

## 📖 项目简介

aiNovel是一个专为长篇网络小说创作设计的AI辅助系统,采用创新的**分卷隔离架构**,解决了传统AI创作中的剧透问题和长文本一致性难题。

### 核心特性

- ✅ **300万字长篇创作**: 支持10卷×30万字的超长篇小说生成
- ✅ **防剧透机制**: 双层设定架构,全局秘密不传入LLM,避免前期剧透
- ✅ **6步创作流程**: 思路讨论 → 背景生成 → 大纲 → 细纲 → 章节创作 → 质量检查
- ✅ **分卷管理**: 每卷独立世界观范围,支持换地图/换剧情
- ✅ **人物一致性**: MBTI人格系统 + 角色记忆库 + 8维度质量检查
- ✅ **文风学习**: 支持上传参考作品,学习并模仿写作风格(阶段3)
- ✅ **多平台LLM**: 支持OpenAI/Claude/通义千问/文心一言
- ✅ **成本可控**: 内置成本监控,300万字预计成本¥100-150

## 🏗️ 架构设计

```
Web界面层 → 6步流程编排层 → 长文本生成核心 → 文风学习层
         ↓
    记忆管理层 → LLM接入层 → 数据持久化层
```

**核心创新: 分卷架构防剧透**

- **全局设定**(global_config): 完整世界观+最终boss+核心秘密(仅系统记录,**不传入LLM**)
- **当前卷设定**(volume_config): 仅包含当前卷的世界观+登场角色(传入LLM)

## 🚀 快速开始

### 环境要求

- Python 3.10+
- OpenAI/Claude/通义千问 API密钥(至少一个)

### 安装

```bash
# 克隆仓库
git clone <repository_url>
cd aiNovel

# 安装依赖(推荐使用uv或pip)
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑.env文件,填入你的API密钥
```

### 基础使用(CLI模式 - 阶段1)

```bash
# 创建新项目
ainovel create-project "修仙废材逆袭"

# Step1: 思路讨论
ainovel step1 --idea "一个被退婚的废材少年,偶然获得神秘戒指"

# Step2: 生成世界观和角色
ainovel step2 --confirm

# Step3: 生成大纲
ainovel step3

# Step4: 生成细纲
ainovel step4

# Step5: 生成章节
ainovel step5 --chapters 1-10

# Step6: 质量检查
ainovel step6 --chapter 1
```

## 📋 开发路线图

### ✅ 阶段1: 核心基础 (当前阶段)
- [x] 项目结构初始化
- [ ] LLM接入层(BaseLLMClient + OpenAIClient)
- [ ] 数据库层(SQLAlchemy + 分卷架构)
- [ ] 6步创作流程(CLI模式)
- [ ] 记忆系统(CharacterDatabase + WorldDatabase)

### 🔄 阶段2: Web界面+长文本支持
- [ ] FastAPI + HTMX Web界面
- [ ] 上下文压缩器(3000字→300字)
- [ ] 近20章全文缓存
- [ ] 增强一致性检查
- [ ] 多平台LLM支持

### ⏳ 阶段3: 文风学习+高级功能
- [ ] 文风提取与向量化
- [ ] 风格迁移提示词生成
- [ ] 用户反馈机制
- [ ] 批量生成优化
- [ ] EPUB/PDF导出

## 📁 项目结构

```
aiNovel/
├── ainovel/
│   ├── llm/           # LLM接入层
│   ├── workflow/      # 6步流程编排
│   ├── core/          # 生成核心
│   ├── style/         # 文风学习
│   ├── memory/        # 记忆管理
│   ├── db/            # 数据持久化
│   ├── utils/         # 工具库
│   ├── cli/           # CLI接口
│   └── web/           # Web界面(阶段2)
├── tests/             # 测试
├── docs/              # 文档
└── data/              # 数据目录
```

## 💰 成本预估

**300万字长篇小说(10卷,1000章)**:
- gpt-4o-mini: ~$15-20
- 混合策略(大纲gpt-4o + 章节qwen): ~¥150-200
- 通义千问qwen-max: ~¥100-150(推荐)

## 🤝 贡献指南

遵循项目开发准则(见`Claude.md`和`AGENTS.md`):
- KISS(简单至上) + YAGNI(精益求精)
- SOLID设计原则 + DRY(杜绝重复)
- 所有注释使用简体中文
- UTF-8编码(无BOM)

## 📄 许可证

MIT License

## 📞 联系方式

- Issue: [GitHub Issues](项目Issue地址)
- 文档: [详细文档](docs/)
- 规划: [实施方案](/.claude/plans/inherited-twirling-sutton.md)
