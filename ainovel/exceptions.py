"""
业务异常类

定义aiNovel系统的业务层异常，提供更精确的错误语义
"""


class AiNovelError(Exception):
    """aiNovel基础异常类"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# ========== 数据访问异常 ==========


class DataNotFoundError(AiNovelError):
    """数据未找到异常"""

    pass


class NovelNotFoundError(DataNotFoundError):
    """小说不存在"""

    def __init__(self, novel_id: int):
        super().__init__(
            f"小说不存在",
            details={"novel_id": novel_id},
        )
        self.novel_id = novel_id


class VolumeNotFoundError(DataNotFoundError):
    """分卷不存在"""

    def __init__(self, volume_id: int):
        super().__init__(
            f"分卷不存在",
            details={"volume_id": volume_id},
        )
        self.volume_id = volume_id


class ChapterNotFoundError(DataNotFoundError):
    """章节不存在"""

    def __init__(self, chapter_id: int):
        super().__init__(
            f"章节不存在",
            details={"chapter_id": chapter_id},
        )
        self.chapter_id = chapter_id


class CharacterNotFoundError(DataNotFoundError):
    """角色不存在"""

    def __init__(self, character_id: int = None, character_name: str = None):
        if character_name:
            super().__init__(
                f"角色不存在",
                details={"character_name": character_name},
            )
        else:
            super().__init__(
                f"角色不存在",
                details={"character_id": character_id},
            )
        self.character_id = character_id
        self.character_name = character_name


class WorldDataNotFoundError(DataNotFoundError):
    """世界观数据不存在"""

    def __init__(self, world_data_id: int):
        super().__init__(
            f"世界观数据不存在",
            details={"world_data_id": world_data_id},
        )
        self.world_data_id = world_data_id


# ========== 业务逻辑异常 ==========


class InvalidWorkflowStateError(AiNovelError):
    """工作流状态错误"""

    def __init__(self, current_state: str, required_state: str):
        super().__init__(
            f"工作流状态错误，无法执行操作",
            details={
                "current_state": current_state,
                "required_state": required_state,
            },
        )
        self.current_state = current_state
        self.required_state = required_state


class InsufficientDataError(AiNovelError):
    """数据不足，无法执行操作"""

    def __init__(self, message: str, missing_data: str):
        super().__init__(
            message,
            details={"missing_data": missing_data},
        )
        self.missing_data = missing_data


class DuplicateDataError(AiNovelError):
    """数据重复"""

    def __init__(self, entity_type: str, identifier: str):
        super().__init__(
            f"{entity_type}已存在",
            details={"identifier": identifier},
        )
        self.entity_type = entity_type
        self.identifier = identifier


# ========== 数据验证异常 ==========


class ValidationError(AiNovelError):
    """数据验证失败"""

    def __init__(self, field: str, message: str):
        super().__init__(
            f"字段验证失败: {field}",
            details={"field": field, "validation_message": message},
        )
        self.field = field
        self.validation_message = message


class InvalidFormatError(AiNovelError):
    """数据格式错误"""

    def __init__(self, data_type: str, message: str):
        super().__init__(
            f"{data_type}格式错误: {message}",
            details={"data_type": data_type},
        )
        self.data_type = data_type


class JSONParseError(InvalidFormatError):
    """JSON解析失败"""

    def __init__(self, content: str, error: str):
        super().__init__(
            "JSON",
            f"无法解析JSON: {error}",
        )
        self.content = content[:200]  # 只保留前200字符
        self.error = error


# ========== 生成相关异常 ==========


class GenerationError(AiNovelError):
    """内容生成失败"""

    pass


class OutlineGenerationError(GenerationError):
    """大纲生成失败"""

    def __init__(self, novel_id: int, reason: str):
        super().__init__(
            f"大纲生成失败: {reason}",
            details={"novel_id": novel_id},
        )
        self.novel_id = novel_id
        self.reason = reason


class ChapterGenerationError(GenerationError):
    """章节生成失败"""

    def __init__(self, chapter_id: int, reason: str):
        super().__init__(
            f"章节生成失败: {reason}",
            details={"chapter_id": chapter_id},
        )
        self.chapter_id = chapter_id
        self.reason = reason


class DetailOutlineGenerationError(GenerationError):
    """细纲生成失败"""

    def __init__(self, chapter_id: int, reason: str):
        super().__init__(
            f"细纲生成失败: {reason}",
            details={"chapter_id": chapter_id},
        )
        self.chapter_id = chapter_id
        self.reason = reason


# ========== 配置异常 ==========


class ConfigurationError(AiNovelError):
    """配置错误"""

    pass


class MissingConfigError(ConfigurationError):
    """缺少配置项"""

    def __init__(self, config_key: str):
        super().__init__(
            f"缺少必需的配置项: {config_key}",
            details={"config_key": config_key},
        )
        self.config_key = config_key


class InvalidConfigError(ConfigurationError):
    """配置值无效"""

    def __init__(self, config_key: str, value: str, reason: str):
        super().__init__(
            f"配置项 {config_key} 的值无效: {reason}",
            details={"config_key": config_key, "value": value},
        )
        self.config_key = config_key
        self.value = value
        self.reason = reason
