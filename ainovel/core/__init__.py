"""
生成核心层

提供提示词管理、大纲生成、章节生成和上下文压缩功能
"""
from ainovel.core.prompt_manager import PromptManager
from ainovel.core.outline_generator import OutlineGenerator
from ainovel.core.chapter_generator import ChapterGenerator
from ainovel.core.context_compressor import ContextCompressor, CompressionLevel

__all__ = [
    "PromptManager",
    "OutlineGenerator",
    "ChapterGenerator",
    "ContextCompressor",
    "CompressionLevel",
]
