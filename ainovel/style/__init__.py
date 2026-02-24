"""
文风学习层

提供文风分析（StyleAnalyzer）和文风应用（StyleApplicator）能力：
- StyleAnalyzer：接收参考文本，调用 LLM 提取结构化风格特征并持久化
- StyleApplicator：将风格特征格式化为写作指令，注入章节生成提示词
"""
from ainovel.style.analyzer import StyleAnalyzer
from ainovel.style.applicator import StyleApplicator

__all__ = ["StyleAnalyzer", "StyleApplicator"]
