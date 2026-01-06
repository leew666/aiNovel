"""
提示词管理模块

提供大纲生成和章节生成所需的提示词模板
"""
from typing import Dict, List, Any


class PromptManager:
    """提示词管理器"""

    # 步骤1：创作思路生成提示词模板
    PLANNING_PROMPT = """你是一位资深的小说策划师。请根据用户提供的模糊想法，帮助他们制定详细的创作思路和计划。

## 用户的初始想法
{initial_idea}

## 要求
1. 分析用户想法的核心要素（题材、主题、风格）
2. 提出明确的创作目标和受众定位
3. 规划故事的核心冲突和发展方向
4. 估算作品篇幅和结构
5. 识别潜在的挑战和解决方案

## 输出格式（JSON）
请按照以下JSON格式输出创作计划：
```json
{{
  "genre": "题材类型（如：玄幻、科幻、都市、历史等）",
  "theme": "核心主题（如：成长、复仇、探索等）",
  "target_audience": "目标读者群体",
  "tone": "作品基调（如：轻松幽默、严肃深沉、热血激昂等）",
  "core_conflict": "核心矛盾冲突描述",
  "story_arc": "故事发展方向（3-5个主要阶段）",
  "estimated_length": {{
    "volumes": 3,
    "chapters_per_volume": 10,
    "words_per_chapter": 3000
  }},
  "key_features": ["特色1", "特色2", "特色3"],
  "challenges": ["挑战1: 解决方案1", "挑战2: 解决方案2"]
}}
```
"""

    # 步骤2：世界背景和角色生成提示词模板
    WORLD_BUILDING_PROMPT = """你是一位世界观设计大师。请根据以下创作思路，生成完整的世界背景和主要角色。

## 创作思路
{planning_content}

## 要求
1. 设计符合题材的世界观设定（地点、组织、规则、物品）
2. 创建主角：性格鲜明，符合故事需求
3. 创建配角：至少2-3个重要配角，各具特色
4. 创建反派：目标明确，动机合理
5. 确保角色之间有足够的互动和冲突空间
6. 世界观设定要自洽，不要有明显逻辑漏洞

## 输出格式（JSON）
请按照以下JSON格式输出：
```json
{{
  "world_data": [
    {{
      "data_type": "location/organization/item/rule",
      "name": "名称",
      "description": "详细描述",
      "properties": {{
        "key1": "value1",
        "key2": "value2"
      }}
    }}
  ],
  "characters": [
    {{
      "name": "角色名",
      "role": "protagonist/supporting/antagonist",
      "mbti": "MBTI类型（如INTJ）",
      "background": "角色背景（200-300字）",
      "personality_traits": {{
        "开放性": 8,
        "责任心": 7,
        "外向性": 5,
        "宜人性": 6,
        "情绪稳定性": 7
      }},
      "goals": "角色目标",
      "conflicts": "内心矛盾或外部冲突"
    }}
  ]
}}
```
"""

    # 步骤4：详细细纲生成提示词模板
    DETAIL_OUTLINE_PROMPT = """你是一位细纲编写专家。请根据已有的大纲，为指定章节生成详细的细纲。

## 小说基本信息
- 标题: {title}
- 当前分卷: {volume_title}
- 当前章节: 第{chapter_order}章 - {chapter_title}

## 章节梗概（来自大纲）
{chapter_summary}

## 本章重点事件
{key_events}

## 涉及角色
{character_info}

## 世界观背景
{world_info}

## 前情回顾
{previous_context}

## 要求
1. 将章节梗概扩展为详细的场景分解
2. 每个场景包含：地点、人物、事件、对话要点
3. 标注情节转折点和伏笔
4. 确保场景之间的逻辑连贯
5. 预估每个场景的字数分配

## 输出格式（JSON）
请按照以下JSON格式输出细纲：
```json
{{
  "scenes": [
    {{
      "scene_number": 1,
      "location": "场景地点",
      "characters": ["角色1", "角色2"],
      "time": "时间描述（如：清晨、午后、深夜）",
      "description": "场景描述（100-200字）",
      "key_dialogues": ["重要对话1", "重要对话2"],
      "plot_points": ["情节要点1", "情节要点2"],
      "foreshadowing": "伏笔（如有）",
      "estimated_words": 500
    }}
  ],
  "chapter_goal": "本章的核心目标",
  "emotional_tone": "情感基调",
  "cliffhanger": "章末悬念（如有）"
}}
```
"""

    # 大纲生成提示词模板
    OUTLINE_GENERATION_PROMPT = """你是一位资深的小说大纲策划师。请根据以下信息生成详细的小说大纲。

## 小说基本信息
- 标题: {title}
- 简介: {description}
- 作者: {author}

## 世界观信息
{world_info}

## 主要角色信息
{character_info}

## 要求
1. 生成一个完整的小说大纲，包括多个分卷（Volume）
2. 每个分卷应包含多个章节（Chapter）
3. 大纲需要合理安排剧情发展，确保故事连贯性
4. 充分利用世界观设定和角色背景
5. 确保角色行为符合其性格特征和MBTI类型

## 输出格式（JSON）
请按照以下JSON格式输出大纲：
```json
{{
  "volumes": [
    {{
      "title": "分卷标题",
      "description": "分卷简介",
      "order": 1,
      "chapters": [
        {{
          "title": "章节标题",
          "order": 1,
          "summary": "章节梗概（200-500字）",
          "key_events": ["事件1", "事件2"],
          "characters_involved": ["角色1", "角色2"]
        }}
      ]
    }}
  ]
}}
```
"""

    # 章节生成提示词模板
    CHAPTER_GENERATION_PROMPT = """你是一位专业的网络小说作家。请根据以下信息撰写本章节的内容。

## 小说基本信息
- 标题: {title}
- 当前分卷: {volume_title}
- 当前章节: 第{chapter_order}章 - {chapter_title}

## 章节梗概
{chapter_summary}

## 本章重点事件
{key_events}

## 涉及角色
{character_info}

## 世界观背景
{world_info}

## 前情回顾
{previous_context}

## 写作风格要求
{style_guide}

## 要求
1. 字数要求: {word_count_min}-{word_count_max}字
2. 确保剧情与大纲一致
3. 角色行为符合性格设定
4. 描写生动细腻，对话自然
5. 保持与前文的连贯性
6. 注意伏笔和铺垫

请直接输出章节正文内容，不要包含任何格式说明或元数据。
"""

    # 前情回顾生成提示词模板
    CONTEXT_SUMMARY_PROMPT = """请将以下章节内容压缩为简短的摘要，保留关键情节和重要信息。

## 章节内容
{content}

## 要求
- 摘要长度: 100-200字
- 保留关键事件和角色互动
- 突出重要伏笔和转折点
- 使用第三人称叙述

请直接输出摘要内容。
"""

    @staticmethod
    def format_world_info(world_data_list: List[Dict[str, Any]]) -> str:
        """
        格式化世界观信息

        Args:
            world_data_list: 世界观数据列表

        Returns:
            格式化后的世界观信息字符串
        """
        if not world_data_list:
            return "暂无世界观设定"

        sections = []
        for data in world_data_list:
            data_type = data.get("data_type", "未知类型")
            title = data.get("title", "无标题")
            content = data.get("content", "")
            sections.append(f"### {data_type} - {title}\n{content}")

        return "\n\n".join(sections)

    @staticmethod
    def format_character_info(character_list: List[Dict[str, Any]]) -> str:
        """
        格式化角色信息

        Args:
            character_list: 角色数据列表

        Returns:
            格式化后的角色信息字符串
        """
        if not character_list:
            return "暂无角色设定"

        sections = []
        for char in character_list:
            name = char.get("name", "未命名")
            mbti = char.get("mbti", "未知")
            background = char.get("background", "")
            personality_traits = char.get("personality_traits", {})

            traits_str = ", ".join(
                [f"{k}: {v}/10" for k, v in personality_traits.items()]
            )

            section = f"""### {name} ({mbti})
**背景**: {background}
**性格特征**: {traits_str if traits_str else "未设定"}"""

            # 添加记忆信息（如果有）
            memories = char.get("memories", [])
            if memories:
                important_memories = [
                    m["content"] for m in memories if m.get("importance") == "high"
                ]
                if important_memories:
                    section += f"\n**重要经历**: {'; '.join(important_memories[:3])}"

            sections.append(section)

        return "\n\n".join(sections)

    @classmethod
    def generate_outline_prompt(
        cls,
        title: str,
        description: str,
        author: str,
        world_data_list: List[Dict[str, Any]],
        character_list: List[Dict[str, Any]],
    ) -> str:
        """
        生成大纲生成提示词

        Args:
            title: 小说标题
            description: 小说简介
            author: 作者
            world_data_list: 世界观数据列表
            character_list: 角色列表

        Returns:
            完整的提示词
        """
        return cls.OUTLINE_GENERATION_PROMPT.format(
            title=title,
            description=description,
            author=author,
            world_info=cls.format_world_info(world_data_list),
            character_info=cls.format_character_info(character_list),
        )

    @classmethod
    def generate_chapter_prompt(
        cls,
        title: str,
        volume_title: str,
        chapter_order: int,
        chapter_title: str,
        chapter_summary: str,
        key_events: List[str],
        character_list: List[Dict[str, Any]],
        world_data_list: List[Dict[str, Any]],
        previous_context: str,
        style_guide: str = "",
        word_count_min: int = 2000,
        word_count_max: int = 3000,
    ) -> str:
        """
        生成章节生成提示词

        Args:
            title: 小说标题
            volume_title: 分卷标题
            chapter_order: 章节序号
            chapter_title: 章节标题
            chapter_summary: 章节梗概
            key_events: 关键事件列表
            character_list: 涉及角色列表
            world_data_list: 世界观数据列表
            previous_context: 前情回顾
            style_guide: 写作风格指南
            word_count_min: 最小字数
            word_count_max: 最大字数

        Returns:
            完整的提示词
        """
        key_events_str = "\n".join([f"- {event}" for event in key_events])

        return cls.CHAPTER_GENERATION_PROMPT.format(
            title=title,
            volume_title=volume_title,
            chapter_order=chapter_order,
            chapter_title=chapter_title,
            chapter_summary=chapter_summary,
            key_events=key_events_str,
            character_info=cls.format_character_info(character_list),
            world_info=cls.format_world_info(world_data_list),
            previous_context=previous_context or "本章为开篇，无前情",
            style_guide=style_guide or "采用网络小说常见风格，节奏紧凑，对话生动",
            word_count_min=word_count_min,
            word_count_max=word_count_max,
        )

    @classmethod
    def generate_context_summary_prompt(cls, content: str) -> str:
        """
        生成前情回顾提示词

        Args:
            content: 章节内容

        Returns:
            完整的提示词
        """
        return cls.CONTEXT_SUMMARY_PROMPT.format(content=content)

    @classmethod
    def generate_planning_prompt(cls, initial_idea: str) -> str:
        """
        生成创作思路提示词

        Args:
            initial_idea: 用户的初始想法

        Returns:
            完整的提示词
        """
        return cls.PLANNING_PROMPT.format(initial_idea=initial_idea)

    @classmethod
    def generate_world_building_prompt(cls, planning_content: str) -> str:
        """
        生成世界背景和角色提示词

        Args:
            planning_content: 创作思路内容（JSON字符串）

        Returns:
            完整的提示词
        """
        return cls.WORLD_BUILDING_PROMPT.format(planning_content=planning_content)

    @classmethod
    def generate_detail_outline_prompt(
        cls,
        title: str,
        volume_title: str,
        chapter_order: int,
        chapter_title: str,
        chapter_summary: str,
        key_events: List[str],
        character_list: List[Dict[str, Any]],
        world_data_list: List[Dict[str, Any]],
        previous_context: str,
    ) -> str:
        """
        生成详细细纲提示词

        Args:
            title: 小说标题
            volume_title: 分卷标题
            chapter_order: 章节序号
            chapter_title: 章节标题
            chapter_summary: 章节梗概
            key_events: 关键事件列表
            character_list: 涉及角色列表
            world_data_list: 世界观数据列表
            previous_context: 前情回顾

        Returns:
            完整的提示词
        """
        key_events_str = "\n".join([f"- {event}" for event in key_events])

        return cls.DETAIL_OUTLINE_PROMPT.format(
            title=title,
            volume_title=volume_title,
            chapter_order=chapter_order,
            chapter_title=chapter_title,
            chapter_summary=chapter_summary,
            key_events=key_events_str,
            character_info=cls.format_character_info(character_list),
            world_info=cls.format_world_info(world_data_list),
            previous_context=previous_context or "本章为开篇，无前情",
        )
