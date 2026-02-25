"""
提示词管理模块

提供大纲生成和章节生成所需的提示词模板
"""
from typing import Dict, List, Any


class PromptManager:
    """提示词管理器"""

    # 步骤1：创作思路生成提示词模板
    # 理论依据：
    #   - Snowflake Method（Randy Ingermanson）：从一句话前提逐层展开到完整结构
    #   - 三幕结构：建置（Act I）→ 对抗（Act II）→ 解决（Act III）
    #   - 英雄之旅（Joseph Campbell / Christopher Vogler）：12阶段叙事弧
    #   - Autonomous Literary Creation Engine（docsbot.ai）：Story Genesis框架
    #   - scarletink AI小说实践：premise + voice + structure + character骨架须在规划阶段锁定
    #   - v5.0融合：Tree of Thoughts（ToT）多路径探索，生成2-3方案并双维度评分后择优
    PLANNING_PROMPT = """你是一位资深的小说策划师，精通三幕结构、英雄之旅和雪花写作法。
请根据用户提供的初始想法，运用专业叙事理论，制定一份完整的创作蓝图。

## 用户的初始想法
{initial_idea}
{genre_context}
## 分析框架

### 第一步：雪花法前提句（Snowflake Method）
用一句话概括整部小说的核心：「[主角] 因为 [触发事件] 而必须 [目标]，但面临 [核心障碍]，最终 [结局方向]。」

### 第二步：故事基因（Story Genesis）
- 题材与世界观：类型定位 + 核心世界设定（地点、时代、规则）
- 主题内核：作品想探讨的深层命题（如：永生的代价、身份认同、权力腐蚀）
- 情感旅程：读者应经历的情绪弧线（如：压抑→希望→绝望→升华）
- 目标读者：具体画像（年龄、阅读偏好、期待体验）
- 作品基调：叙事语气与风格（如：史诗宏大、黑色幽默、细腻写实）

### 第三步：三幕结构规划
- **幕一·建置**（约15-20%篇幅）：介绍主角日常世界 → 触发事件打破平衡 → 主角接受使命
- **幕二·对抗**（约60-65%篇幅）：
  - 前半段：主角尝试用旧方法解决问题，屡屡碰壁，盟友与敌人登场
  - 中点转折：一次重大胜利或揭示，改变故事走向
  - 后半段：一切崩塌，主角失去最重要的东西，跌入最低谷
- **幕三·解决**（约20-25%篇幅）：主角蜕变，以新的方式面对终极对决，完成内外双线成长

### 第四步：角色骨架（须在规划阶段锁定，防止后续人格漂移）
- 主角：核心欲望 + 内心创伤 + 性格缺陷 + 成长方向
- 对手/反派：动机与目标（须与主角形成镜像对立）
- 关键配角：各自的功能定位（导师/盟友/阴影/信使）

### 第五步：叙事声音
- 视角选择：第一人称 / 第三人称限知 / 第三人称全知
- 叙事风格：句式节奏、词汇密度、描写比重
- 时间线：线性 / 倒叙 / 多线并行

### 第六步：篇幅规划
根据故事复杂度估算结构：卷数、每卷章节数、每章字数目标。

### 第七步：思维树探索（Tree of Thoughts）
在确定最终方案前，生成2-3个不同的故事走向方案，并从以下两个维度评分（0-10分）：
- **商业潜力**：爽感密度、读者粘性、类型市场契合度
- **叙事深度**：主题厚度、人物成长弧、情节逻辑自洽性

评分示例：
```
方案A：商业潜力 8分 + 叙事深度 9分 = 总分 17分
方案B：商业潜力 9分 + 叙事深度 7分 = 总分 16分
```
选择总分最高的方案，并说明选择理由，然后基于该方案展开完整创作蓝图。

## 输出要求
请用**自然语言**（非JSON）输出完整创作蓝图，结构如下：
1. 先输出【方案探索】：列出2-3个方案及评分，说明最终选择
2. 再按第一步至第六步逐一展开选定方案的完整蓝图，每步骤有清晰标题
内容要具体、可操作，避免空泛描述。前提句必须出现在最开头。
"""

    # 步骤2：世界背景和角色生成提示词模板
    # 理论依据：
    #   - Autonomous Literary Creation Engine：Character Creation要求distinct speech patterns、psychological depth、growth arcs
    #   - 英雄之旅：角色须有明确的欲望(want)与需求(need)之分，反派须有合理动机
    #   - Save the Cat（Blake Snyder）：世界观须服务于主题，每个设定元素都应与核心冲突相关
    #   - scarletink实践：角色人格须锁定（MBTI+Big Five），防止后续章节人格漂移
    WORLD_BUILDING_PROMPT = """你是一位世界观设计大师，精通角色心理学与叙事世界构建。
请根据以下创作蓝图，生成完整的世界背景和主要角色档案。

## 创作蓝图
{planning_content}

## 世界观构建原则
- 每个设定元素（地点/组织/规则/物品）必须与核心冲突直接相关，避免无意义的堆砌
- 世界规则须自洽，建立后不可随意打破（除非这本身是剧情转折）
- 世界观应服务于主题，而非仅作为背景装饰

## 角色设计原则（防止人格漂移）
- **欲望 vs 需求**：每个主要角色须区分表层欲望（want，角色以为自己想要的）与深层需求（need，角色真正需要的）
- **镜像对立**：反派的核心信念须与主角形成镜像——相同的起点，不同的选择
- **反派三高标准**：高智商（行动有预谋，不犯低级错误）/ 高动机（目标有充分理由，非单纯邪恶）/ 高威胁（主角无法轻易击败，每次交锋主角都付出代价）
- **功能定位**：配角须有明确的叙事功能（导师/盟友/阴影/信使/门槛守卫）
- **语言标签**：每个角色须有1-2个独特的说话习惯或口头禅，确保对话可辨识

## 输出格式（JSON）
请按照以下JSON格式输出：
```json
{{
  "world_data": [
    {{
      "data_type": "location/organization/item/rule",
      "name": "名称",
      "description": "详细描述",
      "thematic_relevance": "与核心主题/冲突的关联",
      "properties": {{
        "key1": "value1"
      }}
    }}
  ],
  "characters": [
    {{
      "name": "角色名",
      "role": "protagonist/supporting/antagonist",
      "narrative_function": "导师/盟友/阴影/信使/门槛守卫（配角必填）",
      "mbti": "MBTI类型（如INTJ）",
      "want": "表层欲望（角色以为自己想要的）",
      "need": "深层需求（角色真正需要的，通常与want矛盾）",
      "wound": "内心创伤（驱动行为的根源）",
      "flaw": "性格缺陷（阻碍成长的弱点）",
      "background": "角色背景（200-300字）",
      "personality_traits": {{
        "开放性": 8,
        "责任心": 7,
        "外向性": 5,
        "宜人性": 6,
        "情绪稳定性": 7
      }},
      "speech_tags": ["说话习惯1", "口头禅或语气特征"],
      "arc": "角色成长弧线（从什么状态到什么状态）"
    }}
  ]
}}
```
"""

    # 步骤4：详细细纲生成提示词模板
    # 理论依据：
    #   - Autonomous Literary Creation Engine：Scene Architecture——setting/character interactions/plot advancement/emotional beats/pacing
    #   - 场景目标-冲突-结局（Goal-Conflict-Outcome）：每个场景须有明确目标，遭遇阻力，产生结果
    #   - 场景-续集结构（Scene-Sequel）：动作场景后须有反应场景（情绪处理→思考→决策）
    DETAIL_OUTLINE_PROMPT = """你是一位细纲编写专家，精通场景架构与叙事节奏控制。
请根据已有的大纲，为指定章节生成详细的场景细纲。

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

## 场景设计原则

### 目标-冲突-结局（每个场景必须包含）
- **目标**：POV角色在本场景想要达成什么？
- **冲突**：什么阻止了目标的实现？（内部冲突/外部冲突/两难困境）
- **结局**：是/但是/否/而且——场景结果须推动情节或揭示角色

### 场景-续集节奏
- 动作场景（Scene）后须安排反应场景（Sequel）：情绪反应 → 思考分析 → 新决策
- 避免连续堆砌动作场景，给读者情绪喘息空间

### 章节内部节奏配比
- 开篇（约10%字数）：快节奏切入，直接进入冲突或悬念，禁止静态铺垫
- 发展（约40%字数）：中节奏推进，交替使用动作场景和反应场景
- 高潮（约30%字数）：快节奏爆发，短句密集，感官细节集中
- 收尾（约20%字数）：先快后慢，处理后果，埋下新钩子

### 情感节拍控制
- 标注每个场景的情绪值变化（正负方向）
- 确保章节整体有情绪弧线，而非平铺直叙

## 输出格式（JSON）
```json
{{
  "chapter_goal": "本章对主角的核心考验或推进",
  "emotional_arc": "本章整体情绪弧线（如：期待→受挫→绝望→转机）",
  "cliffhanger": "章末悬念",
  "scenes": [
    {{
      "scene_number": 1,
      "scene_type": "action/sequel/transition",
      "location": "场景地点",
      "characters": ["角色1", "角色2"],
      "time": "时间描述",
      "pov": "视角角色",
      "goal": "POV角色本场景目标",
      "conflict": "阻力来源",
      "outcome": "场景结果（是/但是/否/而且）",
      "description": "场景描述（150-250字）",
      "key_dialogues": ["对话要点1", "对话要点2"],
      "emotional_shift": "情绪变化（如：+紧张/-希望）",
      "foreshadowing": "伏笔（如有）",
      "estimated_words": 600
    }}
  ]
}}
```
"""

    # 大纲生成提示词模板
    # 理论依据：
    #   - 三幕结构：幕一建置(15-20%) → 幕二对抗(60-65%) → 幕三解决(20-25%)
    #   - Save the Cat 15节拍：开场画面/主题呈现/铺垫/催化剂/争论/进入二幕/B故事/玩乐时光/中点/坏人逼近/一切崩塌/灵魂暗夜/进入三幕/结局/终场画面
    #   - 英雄之旅：每卷对应一个完整的旅程阶段，章节须有明确的情感节拍
    #   - Autonomous Literary Creation Engine：conflict escalation + thematic reinforcement贯穿全书
    OUTLINE_GENERATION_PROMPT = """你是一位资深的小说大纲策划师，精通三幕结构与Save the Cat节拍表。
请根据以下信息生成完整的小说大纲，确保每章都有明确的叙事功能和情感节拍。

## 小说基本信息
- 标题: {title}
- 简介: {description}
- 作者: {author}

## 世界观信息
{world_info}

## 主要角色信息
{character_info}

## 大纲构建原则

### 三幕结构分配
- **幕一（建置）**：约占总章节15-20%，完成：介绍主角日常世界 → 触发事件 → 主角接受使命
- **幕二前半（对抗上升）**：约占30%，主角尝试旧方法、结识盟友、遭遇挫折，中点处有重大转折
- **幕二后半（对抗下降）**：约占30%，局势恶化、背叛或失去、跌入最低谷（All is Lost时刻）
- **幕三（解决）**：约占20-25%，主角蜕变、终极对决、内外双线成长完成
- **冲突四维升级**（贯穿幕二）：每隔3-5章，至少一个维度必须升级：
  - 力量维度：对手实力/数量增加
  - 情感维度：关系破裂程度加深（背叛/失去/牺牲）
  - 范围维度：影响扩大（从个人→团队→世界）
  - 时间维度：紧迫性增加（截止时间/不可逆后果）
  - 禁止"无意义冲突"（无后果）、"无逻辑冲突"（强行制造）

### 章节节拍要求
每章必须包含：
1. **进入钩子**：开篇吸引读者继续读的元素
2. **核心事件**：推动情节或揭示角色的关键动作
3. **情感节拍**：本章的情绪走向（上升/下降/转折）
4. **章末悬念**：驱动读者翻页的结尾张力

### 伏笔管理
- 在大纲层面标注伏笔的埋设章节和呼应章节
- 确保每个伏笔在结局前得到回收

### 明暗双线布局
- 明线（1-2条）：主角可见的行动目标线，读者全程跟随
- 暗线（2-3条）：反派布局线、世界秘密线、角色内心成长线，在关键节点与明线交汇
- 在大纲中标注每条暗线的"浮出水面"章节

### 波浪式爽点节奏
- 小爽点：每3-5千字（约1-2章）安排一次小满足（打脸/小胜利/信息揭秘）
- 大爽点：每10-15章安排一次大爆发（重大逆转/阶段性胜利/核心秘密揭露）
- 在大纲中用"小爽"/"大爽"标注各章节的爽点类型

### 信息差三层释放
- 诱饵层（前15%章节）：抛出3-5个核心谜题，只给线索不给答案
- 递进层（中间65%章节）：每隔5-8章揭示一个碎片，维持悬念
- 爆发层（后20%章节）：集中揭秘，让读者"原来如此"的满足感最大化

## 输出格式（JSON）
```json
{{
  "volumes": [
    {{
      "title": "分卷标题",
      "description": "分卷简介",
      "act": "act1/act2a/act2b/act3",
      "order": 1,
      "chapters": [
        {{
          "title": "章节标题",
          "order": 1,
          "beat": "本章在三幕结构中的节拍名称（如：触发事件/中点转折/最低谷/终极对决）",
          "summary": "章节梗概（200-500字）",
          "emotional_arc": "本章情绪走向（如：平静→紧张→震惊）",
          "key_events": ["事件1", "事件2"],
          "characters_involved": ["角色1", "角色2"],
          "foreshadowing": "埋设的伏笔（如有）",
          "callback": "呼应的前文伏笔（如有）",
          "chapter_hook": "章末悬念（类型：悬念钩/反转钩/承诺钩/冲突升级钩）"
        }}
      ]
    }}
  ]
}}
```
"""

    # 章节生成提示词模板
    # 理论依据：
    #   - Autonomous Literary Creation Engine：Creative Composition——immersive storytelling/authentic voices/rich sensory details/emotional truth
    #   - scarletink实践：voice一致性是AI写作最大挑战，须明确POV/句式节奏/词汇密度
    #   - Show Don't Tell原则：通过行动、感官细节、对话揭示情感，而非直接陈述
    #   - 对话写作原则：每句对话须同时完成至少两个功能（推进情节/揭示性格/制造冲突/传递信息）
    #   - v5.0融合：Chain-of-Thought（CoT）写前推理 + Few-Shot情节模板（打脸/震惊/开篇）
    CHAPTER_GENERATION_PROMPT = """你是一位专业的小说作家。请根据以下信息撰写本章节正文。

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

## 角色记忆卡（高优先级约束）
{character_memory_cards}

## 世界观卡片（高优先级约束）
{world_memory_cards}

## 前情回顾
{previous_context}

## 写作风格要求
{style_guide}

## 作者备注（Author's Note）
{authors_note}

## 写作原则

### 叙事沉浸感
- 感官优先级因场景类型而异：
  - 战斗/动作场景：触觉（冲击/疼痛）> 听觉（声音节奏）> 视觉
  - 情感/对话场景：视觉（微表情/肢体）> 触觉（接触/距离）> 嗅觉（记忆触发）
  - 环境/氛围场景：视觉（光影/色彩）> 嗅觉（气味渲染）> 听觉（背景音）
  - 禁用：空洞的"美丽"/"壮观"等形容词，必须用具体感官细节替代
- Show Don't Tell：通过行动和细节揭示情感，避免直接陈述角色心理
- 每个场景须有明确的空间感和时间感

### 对话质量
- 每句对话须同时完成至少两个功能：推进情节 / 揭示性格 / 制造冲突 / 传递信息
- 对话须符合角色的教育背景、身份地位和当前情绪状态
- 避免"对话标签堆砌"（他说/她说之外，用动作描写代替）

### 节奏控制
- 动作场景：短句、快节奏、减少修饰
- 情感场景：长句、慢节奏、细腻描写
- 章末须留有悬念或情感余韵，驱动读者继续阅读

### 一致性约束（最高优先级）
- 严格遵守角色记忆卡和世界观卡片中的所有设定
- 角色行为须符合其MBTI、欲望、创伤和当前处境
- 不得引入与前文矛盾的新设定

## 写作前推理（Chain-of-Thought，内部执行，不输出）
在动笔前，按以下步骤完成内部推理：
1. **分解核心冲突**：本章的主要张力是什么？进入状态和离开状态各是什么？
2. **识别关键转折点**：本章有哪个情节节点会改变人物处境或读者预期？
3. **设计情绪曲线**：本章情绪走向（如：平静→紧张→爆发→余韵）
4. **确认章末钩子**：用什么悬念或情感余韵驱动读者翻页？

## 常用情节模板参考（Few-Shot，按需调用）

### 爽点类型选择（按章节需求选用）
- 打脸逆转：对手轻视→主角碾压（见下方详细模板）
- 实力碾压：无悬念的降维打击，强调对比落差
- 身份揭秘：隐藏身份/能力曝光，震惊周围人
- 情感爆发：压抑已久的情绪集中释放（愤怒/悲痛/喜悦）
- 复仇达成：前文埋下的仇恨得到清算
- 绝境翻盘：最低谷时刻的逆转，需要前文充分铺垫
- 认知颠覆：读者/角色的世界观被彻底推翻

**三高标准**：高对比度（落差越大越爽）/ 高密度（爽点前铺垫充分）/ 高情绪强度（角色和读者同步情绪）

### 打脸/逆转情节
```
第一步：建立落差——对手极度轻视主角，用言语或行动嘲讽
第二步：蓄力铺垫——主角保持低调，周围人强化"主角必输"氛围
第三步：反转爆发——主角展现真实实力，瞬间逆转局势
第四步：震惊连锁——三层反应：表情本能 → 语言失控 → 认知崩塌
第五步：后果余波——对手付出代价，主角获益，埋下新伏笔
```

### 震惊反应描写
```
第一层：肢体本能——瞪大眼睛、倒吸冷气、身体僵硬
第二层：语言失控——结巴、重复、质疑（"这...这怎么可能？"）
第三层：认知崩塌——世界观被颠覆，开始重新审视一切
```

### 开篇黄金结构（适用于第一章或新卷开篇）
```
1. 动态场景切入（禁止静止场景开篇）
2. 核心冲突前置（开篇内抛出主要矛盾）
3. 滴灌式信息透露（避免信息轰炸）
4. 限制出场人数（不超过三人）
5. 快速展现主角特质或金手指
```

## 字数要求
{word_count_min}-{word_count_max}字

请直接输出章节正文内容，不要包含任何格式说明或元数据。
"""

    CONSISTENCY_CHECK_PROMPT = """你是一位小说一致性审校员。请检查“待检查文本”是否与已有设定冲突。

## 小说基本信息
- 标题: {title}
- 当前分卷: {volume_title}
- 当前章节: 第{chapter_order}章 - {chapter_title}

## 本章梗概
{chapter_summary}

## 前情回顾
{previous_context}

## 角色记忆卡
{character_memory_cards}

## 世界观卡片
{world_memory_cards}

## 待检查文本
{chapter_content}

## 检查要求
1. 检查角色人设、目标、情绪、关系是否冲突
2. 检查世界观规则、组织、物品设定是否冲突
3. 检查时间线与前情衔接是否冲突
4. **伏笔追踪**：检查本章是否有埋设新伏笔，已有伏笔是否得到呼应或推进
5. **信息差管理**：检查读者已知信息与角色已知信息是否符合预期，有无意外泄露或遗漏
6. 给出可执行修复建议，避免空泛评价
7. 严格模式：{strict_mode}

## 输出格式（JSON）
```json
{{
  "overall_risk": "low|medium|high",
  "summary": "总体结论（80字以内）",
  "issues": [
    {{
      "severity": "critical|major|minor",
      "type": "character|world|timeline|logic|foreshadowing|info_gap",
      "location": "问题位置（段落或句子）",
      "description": "冲突描述",
      "suggestion": "修复建议"
    }}
  ],
  "foreshadowing_status": {{
    "new_planted": ["本章新埋设的伏笔描述"],
    "callbacks_found": ["本章呼应的前文伏笔描述"],
    "unresolved_risks": ["存在风险的未回收伏笔"]
  }}
}}
```
"""

    REWRITE_PROMPT = """你是一位专业小说编辑。请根据要求改写指定文本。

## 改写目标
- 模式: {rewrite_mode}
- 指令: {instruction}
- 保持主线剧情不变: {preserve_plot}

## 原文
{source_content}

## 约束
1. 保留人名、核心事件和世界观设定，不引入矛盾
2. 尽量保持章节语气和叙事视角一致
3. 仅输出改写后的正文，不输出说明
"""

    POLISH_PROMPT = """你是一位专业小说润色编辑。请润色原文，使语言更自然、有画面感。

## 润色目标
- 指令: {instruction}
- 保持主线剧情不变: {preserve_plot}

## 原文
{source_content}

## 约束
1. 不改变核心事件顺序和结局
2. 优先优化句式、用词、节奏和对话自然度
3. 仅输出润色后的正文
"""

    EXPAND_PROMPT = """你是一位网络小说扩写编辑。请在不改变主线的前提下扩写原文。

## 扩写目标
- 指令: {instruction}
- 保持主线剧情不变: {preserve_plot}

## 原文
{source_content}

## 约束
1. 补充细节描写、情绪递进和场景动作
2. 不新增破坏性剧情分支
3. 仅输出扩写后的正文
"""

    # 步骤6：质量检查提示词模板
    # 理论依据：
    #   - Autonomous Literary Creation Engine：Editorial Assessment——dialogue authenticity/pacing/character consistency/plot logic/prose quality
    #   - scarletink实践：AI最易出现连续性问题（continuity errors）和人格漂移，须重点检查
    #   - 叙事张力理论：每章须有进入张力和离开张力，避免"平章"
    QUALITY_CHECK_PROMPT = """你是一位专业的小说编辑，精通叙事结构与角色心理学。
请对以下章节内容进行全面的质量检查，从9个维度评估并给出可执行的修改建议。

## 小说基本信息
- 标题: {title}
- 当前分卷: {volume_title}
- 当前章节: 第{chapter_order}章 - {chapter_title}

## 章节梗概
{chapter_summary}

## 涉及角色
{character_info}

## 前情回顾
{previous_context}

## 待检查的章节内容
{chapter_content}

## 检查维度

### 第一层：基础叙事质量
1. **情节连贯性**：与前情衔接是否自然，逻辑是否通顺，有无突兀跳跃
2. **角色一致性**：行为、语言、决策是否符合角色的MBTI、欲望、创伤和当前处境（人格漂移是AI写作最常见问题）
3. **世界观自洽**：是否违反已建立的世界规则，有无新引入的矛盾设定
4. **叙事张力**：章节是否有明确的进入张力和离开张力，有无"平章"（无冲突、无推进）
5. **对话质量**：对话是否自然可信，是否符合角色身份，每句是否承担叙事功能（避免无效对话）
6. **Show Don't Tell**：是否过度直述情感，有无可改为感官细节或行动的段落
7. **节奏控制**：动作/情感/描写的比例是否合适，有无拖沓或跳跃过快的段落
8. **伏笔与悬念**：是否有效设置或呼应伏笔，章末是否留有驱动阅读的张力
9. **文字质量**：用词是否准确，有无语病、重复用词或AI特征句式（如"不禁"、"涌上心头"等套话）

### 第二层：商业网文六大法则（v5.0）
10. **钩子法则**：章节开头是否在300字内设置有效钩子或悬念，驱动读者继续阅读
11. **冲突递进法则**：本章冲突强度是否比上一章有所递增，避免原地踏步
12. **爽点法则**：本章是否提供了至少一个明确的爽点（逆转/打脸/升级/揭秘）
13. **人物行为法则**：角色的每个重要决策是否有充分的动机支撑，行为逻辑是否自洽
14. **节奏法则**：张弛有度，高潮后是否有适当的缓冲，避免读者情绪疲劳
15. **感官法则**：是否运用了多种感官细节（视觉/听觉/嗅觉/触觉）构建沉浸感

## 输出格式（JSON）
```json
{{
  "overall_score": 85,
  "dimension_scores": {{
    "情节连贯性": 90,
    "角色一致性": 85,
    "世界观自洽": 95,
    "叙事张力": 75,
    "对话质量": 80,
    "Show Don't Tell": 70,
    "节奏控制": 80,
    "伏笔与悬念": 80,
    "文字质量": 85,
    "钩子法则": 80,
    "冲突递进法则": 75,
    "爽点法则": 70,
    "人物行为法则": 85,
    "节奏法则": 80,
    "感官法则": 75
  }},
  "issues": [
    {{
      "severity": "critical/major/minor",
      "dimension": "检查维度名称",
      "location": "问题位置（如：第3段，对话部分）",
      "description": "问题描述",
      "suggestion": "具体修改建议（可操作，非空泛评价）"
    }}
  ],
  "highlights": ["亮点1", "亮点2"],
  "summary": "总体评价（100字以内）"
}}
```
"""

    # 文风分析提示词模板
    STYLE_ANALYSIS_PROMPT = """你是一位专业的文学风格分析师。请深度分析以下参考文本的写作风格，提取可复用的风格特征。

## 参考文本
{source_text}

## 分析维度
1. **句式特征**：句子长短分布、常用句式结构（排比/倒装/省略等）
2. **词汇风格**：用词偏好（文言/口语/网络用语）、高频词汇类型
3. **叙事视角**：第一/第三人称、叙事距离（亲近/疏离）
4. **节奏控制**：段落节奏（快/慢）、张弛规律
5. **对话风格**：对话密度、对话语气特征
6. **描写密度**：场景/动作/心理描写的比例与细腻程度
7. **情感基调**：整体情绪色彩与表达方式
8. **特色技法**：作者独特的写作手法或标志性表达

## 输出格式（JSON）
请按照以下JSON格式输出风格分析结果：
```json
{{
  "sentence_patterns": ["特征1", "特征2"],
  "vocabulary_style": "词汇风格描述",
  "narrative_perspective": "叙事视角描述",
  "pacing": "节奏特征描述",
  "dialogue_style": "对话风格描述",
  "description_density": "描写密度描述",
  "tone": "情感基调描述",
  "special_techniques": ["技法1", "技法2"],
  "summary": "综合风格描述（150字以内，可直接作为写作指令使用）"
}}
```
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

    # 分层压缩提示词模板（上下文压缩器专用）
    COMPRESSION_DETAILED_PROMPT = """请将以下章节内容压缩为详细摘要，保留关键情节、角色互动和重要伏笔。

## 章节内容
{content}

## 要求
- 摘要长度：约 {target_words} 字
- 保留：关键事件、角色行为、重要对话要点、伏笔与转折
- 使用第三人称叙述
- 语言简洁，不加评论

请直接输出摘要。
"""

    COMPRESSION_BRIEF_PROMPT = """请将以下章节内容压缩为简要摘要，只保留核心事件。

## 章节内容
{content}

## 要求
- 摘要长度：约 {target_words} 字
- 只保留：核心情节推进、关键角色行为
- 使用第三人称叙述

请直接输出摘要。
"""

    COMPRESSION_MINIMAL_PROMPT = """请将以下章节内容提炼为关键事件列表。

## 章节内容
{content}

## 要求
- 总长度：约 {target_words} 字
- 格式：用分号分隔的事件短语，如"张三拜师；获得法器；初遇反派"
- 只保留对后续剧情有影响的事件

请直接输出事件列表。
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

            # 添加目标（如果有）
            goals = char.get("goals")
            if goals:
                section += f"\n**当前目标**: {goals}"

            # 添加当前状态（如果有）
            current_status = char.get("current_status")
            if current_status:
                section += f"\n**当前状态**: {current_status}"

            # 添加当前心情（如果有）
            current_mood = char.get("current_mood")
            if current_mood:
                section += f"\n**当前心情**: {current_mood}"

            # 添加口头禅（如果有）
            catchphrases = char.get("catchphrases") or []
            if catchphrases:
                section += f"\n**口头禅**: {' / '.join(catchphrases)}"

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

    @staticmethod
    def format_character_memory_cards(cards: List[Dict[str, Any]]) -> str:
        """格式化角色记忆卡"""
        if not cards:
            return "暂无角色记忆卡"

        sections = []
        for card in cards:
            memories = card.get("important_memories") or []
            memories_text = "; ".join(memories) if memories else "无"
            section = (
                f"### {card.get('name', '未命名')} ({card.get('mbti', '未知')})\n"
                f"- 当前目标: {card.get('goals') or '未设定'}\n"
                f"- 当前状态: {card.get('current_status') or '未设定'}\n"
                f"- 当前心情: {card.get('current_mood') or '未设定'}\n"
                f"- 重要记忆: {memories_text}"
            )
            sections.append(section)

        return "\n\n".join(sections)

    @staticmethod
    def format_world_memory_cards(cards: List[Dict[str, Any]]) -> str:
        """格式化世界观卡片"""
        if not cards:
            return "暂无世界观卡片"

        sections = []
        for card in cards:
            sections.append(
                f"### {card.get('data_type', 'unknown')} - {card.get('name', '未命名')}\n"
                f"{card.get('description', '')}"
            )
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
        character_memory_cards: List[Dict[str, Any]] | None = None,
        world_memory_cards: List[Dict[str, Any]] | None = None,
        style_guide: str = "",
        authors_note: str = "",
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
            character_memory_cards: 角色记忆卡
            world_memory_cards: 世界观卡片
            style_guide: 写作风格指南
            authors_note: 作者备注，动态注入的写作指令（参考KoboldAI Author's Note）
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
            character_memory_cards=cls.format_character_memory_cards(
                character_memory_cards or []
            ),
            world_memory_cards=cls.format_world_memory_cards(
                world_memory_cards or []
            ),
            previous_context=previous_context or "本章为开篇，无前情",
            style_guide=style_guide or "采用网络小说常见风格，节奏紧凑，对话生动",
            authors_note=authors_note or "无特殊指示",
            word_count_min=word_count_min,
            word_count_max=word_count_max,
        )

    @classmethod
    def generate_consistency_check_prompt(
        cls,
        title: str,
        volume_title: str,
        chapter_order: int,
        chapter_title: str,
        chapter_summary: str,
        chapter_content: str,
        previous_context: str,
        character_memory_cards: List[Dict[str, Any]],
        world_memory_cards: List[Dict[str, Any]],
        strict: bool = False,
    ) -> str:
        """生成一致性检查提示词"""
        return cls.CONSISTENCY_CHECK_PROMPT.format(
            title=title,
            volume_title=volume_title,
            chapter_order=chapter_order,
            chapter_title=chapter_title,
            chapter_summary=chapter_summary or "暂无梗概",
            chapter_content=chapter_content,
            previous_context=previous_context or "本章为开篇，无前情",
            character_memory_cards=cls.format_character_memory_cards(
                character_memory_cards
            ),
            world_memory_cards=cls.format_world_memory_cards(world_memory_cards),
            strict_mode="是" if strict else "否",
        )

    @classmethod
    def generate_rewrite_prompt(
        cls,
        source_content: str,
        instruction: str,
        rewrite_mode: str = "rewrite",
        preserve_plot: bool = True,
    ) -> str:
        """
        生成改写提示词。

        rewrite_mode: rewrite | polish | expand
        """
        template_map = {
            "rewrite": cls.REWRITE_PROMPT,
            "polish": cls.POLISH_PROMPT,
            "expand": cls.EXPAND_PROMPT,
        }
        mode = (rewrite_mode or "rewrite").lower().strip()
        template = template_map.get(mode, cls.REWRITE_PROMPT)
        return template.format(
            rewrite_mode=mode,
            instruction=instruction,
            preserve_plot="是" if preserve_plot else "否",
            source_content=source_content,
        )

    @classmethod
    def generate_style_analysis_prompt(cls, source_text: str) -> str:
        """
        生成文风分析提示词

        Args:
            source_text: 待分析的参考文本

        Returns:
            完整的提示词
        """
        return cls.STYLE_ANALYSIS_PROMPT.format(source_text=source_text)

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
    def generate_compression_prompt(
        cls, content: str, level: str, target_words: int
    ) -> str:
        """
        生成分层压缩提示词（供 ContextCompressor 使用）

        Args:
            content: 章节正文
            level: 压缩级别，"detailed" / "brief" / "minimal"
            target_words: 目标字数

        Returns:
            完整的提示词
        """
        template_map = {
            "detailed": cls.COMPRESSION_DETAILED_PROMPT,
            "brief": cls.COMPRESSION_BRIEF_PROMPT,
            "minimal": cls.COMPRESSION_MINIMAL_PROMPT,
        }
        template = template_map.get(level, cls.COMPRESSION_BRIEF_PROMPT)
        return template.format(content=content, target_words=target_words)

    @classmethod
    def generate_planning_prompt(
        cls,
        initial_idea: str,
        genre_id: str | None = None,
        plot_ids: list[str] | None = None,
    ) -> str:
        """
        生成创作思路提示词

        Args:
            initial_idea: 用户的初始想法
            genre_id: 主题材 ID（来自 genre_data.GENRES）
            plot_ids: 情节流派标签 ID 列表（来自 genre_data.PLOT_TAGS）

        Returns:
            完整的提示词
        """
        from ainovel.core.genre_data import build_genre_context
        genre_context = build_genre_context(genre_id or "", plot_ids or [])
        genre_block = f"\n## 用户选定的类型与情节方向\n{genre_context}\n" if genre_context else ""
        return cls.PLANNING_PROMPT.format(
            initial_idea=initial_idea,
            genre_context=genre_block,
        )

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
    def generate_quality_check_prompt(
        cls,
        title: str,
        volume_title: str,
        chapter_order: int,
        chapter_title: str,
        chapter_summary: str,
        chapter_content: str,
        character_list: List[Dict[str, Any]],
        previous_context: str,
    ) -> str:
        """
        生成质量检查提示词

        Args:
            title: 小说标题
            volume_title: 分卷标题
            chapter_order: 章节序号
            chapter_title: 章节标题
            chapter_summary: 章节梗概
            chapter_content: 章节正文内容
            character_list: 涉及角色列表
            previous_context: 前情回顾

        Returns:
            完整的提示词
        """
        return cls.QUALITY_CHECK_PROMPT.format(
            title=title,
            volume_title=volume_title,
            chapter_order=chapter_order,
            chapter_title=chapter_title,
            chapter_summary=chapter_summary,
            chapter_content=chapter_content,
            character_info=cls.format_character_info(character_list),
            previous_context=previous_context or "本章为开篇，无前情",
        )

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
