"""
小说类型与情节数据模块

来源：KB4_Reference_Data_v5.0，包含题材、核心情节流派、热门设定与背景分类。
数据结构：主题材 → 可选情节标签（多选），供创作流程注入上下文。
"""
from typing import TypedDict


class PlotTag(TypedDict):
    id: str          # 唯一标识，用于存储和检索
    name: str        # 显示名称
    desc: str        # 简短定义
    core_appeal: str # 核心爽点
    heat: int        # 2024-2025 市场热度（1-5星）


class GenreInfo(TypedDict):
    id: str
    name: str
    desc: str
    core_appeal: str
    heat: int
    recommended_plots: list[str]  # 推荐搭配的 plot id 列表


# ============ 3.2 常见核心情节与流派 ============

PLOT_TAGS: dict[str, PlotTag] = {
    "rebirth": {
        "id": "rebirth",
        "name": "重生文",
        "desc": "主角死亡后回到过去，获得重来一次机会",
        "core_appeal": "复仇爽、弥补遗憾、先知优势",
        "heat": 5,
    },
    "transmigration": {
        "id": "transmigration",
        "name": "穿越文",
        "desc": "主角灵魂穿越到另一个时空或另一个人身上",
        "core_appeal": "现代知识碾压、文化差异笑点",
        "heat": 4,
    },
    "book_transmigration": {
        "id": "book_transmigration",
        "name": "穿书文",
        "desc": "主角穿越到自己读过的小说世界里",
        "core_appeal": "剧情先知、改变命运",
        "heat": 5,
    },
    "system": {
        "id": "system",
        "name": "系统文",
        "desc": "主角获得类似游戏系统的金手指",
        "core_appeal": "获得爽、成长爽、任务完成爽",
        "heat": 5,
    },
    "unlimited_flow": {
        "id": "unlimited_flow",
        "name": "无限流",
        "desc": "主角被卷入不同副本世界中求生",
        "core_appeal": "通关爽、获得道具爽",
        "heat": 5,
    },
    "revenge": {
        "id": "revenge",
        "name": "复仇文",
        "desc": "以主角向仇人复仇为主线",
        "core_appeal": "复仇爽、打脸爽",
        "heat": 5,
    },
    "levelup": {
        "id": "levelup",
        "name": "升级流",
        "desc": "主角通过打怪、修炼不断提升实力",
        "core_appeal": "成长爽、突破爽",
        "heat": 4,
    },
    # ============ 3.3 热门设定与"梗" ============
    "face_slap": {
        "id": "face_slap",
        "name": "打脸爽文",
        "desc": "主角展示实力让曾经看不起自己的人震惊后悔",
        "core_appeal": "打脸爽",
        "heat": 5,
    },
    "grovel": {
        "id": "grovel",
        "name": "追妻火葬场",
        "desc": "男主伤害女主后幡然醒悟拼命追回",
        "core_appeal": "情感爽、复仇爽",
        "heat": 5,
    },
    "secret_identity": {
        "id": "secret_identity",
        "name": "马甲文",
        "desc": "主角拥有多重不为人知的强大身份",
        "core_appeal": "打脸爽、装逼爽",
        "heat": 5,
    },
    "true_false_daughter": {
        "id": "true_false_daughter",
        "name": "真假千金",
        "desc": "围绕身份被互换的两位女性角色展开",
        "core_appeal": "身份揭露、打脸爽",
        "heat": 5,
    },
    "deification": {
        "id": "deification",
        "name": "被神化文",
        "desc": "主角普通行为被周围人过度解读为绝世高人",
        "core_appeal": "装逼爽、误会爽",
        "heat": 4,
    },
    "crazy_lit": {
        "id": "crazy_lit",
        "name": "发疯文学",
        "desc": "主角打破常规，用极其直接解气的方式应对冲突",
        "core_appeal": "打脸爽、复仇爽",
        "heat": 5,
    },
    "angst": {
        "id": "angst",
        "name": "虐文",
        "desc": "情节曲折，情感痛苦，让读者感受虐心体验",
        "core_appeal": "虐心、痛苦、遗憾",
        "heat": 3,
    },
    "cp_focus": {
        "id": "cp_focus",
        "name": "CP塑造",
        "desc": "以塑造人物配对互动和情感发展为核心",
        "core_appeal": "情感爽、互动爽",
        "heat": 5,
    },
    "group_favorite": {
        "id": "group_favorite",
        "name": "团宠",
        "desc": "主角被多人宠爱、保护",
        "core_appeal": "被爱爽、护短爽",
        "heat": 5,
    },
    "underdog": {
        "id": "underdog",
        "name": "屌丝逆袭",
        "desc": "出身平凡的主角最终逆风翻盘走向巅峰",
        "core_appeal": "打脸爽、认可爽",
        "heat": 5,
    },
    "trash_to_treasure": {
        "id": "trash_to_treasure",
        "name": "废柴流",
        "desc": "开局被人看不起的废柴，后期展现惊人天赋",
        "core_appeal": "打脸爽、成长爽",
        "heat": 4,
    },
    # ============ 3.4 背景与职业分类 ============
    "farming": {
        "id": "farming",
        "name": "种田文",
        "desc": "主角通过种地、经商、搞基建发家致富",
        "core_appeal": "成长爽、财富爽",
        "heat": 4,
    },
    "palace_intrigue": {
        "id": "palace_intrigue",
        "name": "宫斗/宅斗",
        "desc": "皇宫或大家族中的权力地位人际斗争",
        "core_appeal": "权谋胜利、打脸爽",
        "heat": 4,
    },
    "apocalypse": {
        "id": "apocalypse",
        "name": "末世文",
        "desc": "世界末日背景，丧尸爆发或天灾降临",
        "core_appeal": "生存爽、物资爽",
        "heat": 4,
    },
    "entertainment": {
        "id": "entertainment",
        "name": "娱乐圈文",
        "desc": "围绕演艺圈明星、经纪人展开",
        "core_appeal": "事业爽、打脸爽",
        "heat": 5,
    },
    "ceo": {
        "id": "ceo",
        "name": "总裁文",
        "desc": "霸道总裁与普通女主角的爱情故事",
        "core_appeal": "情感爽、财富爽",
        "heat": 4,
    },
    "supernatural": {
        "id": "supernatural",
        "name": "灵异文",
        "desc": "包含鬼怪、灵异事件等元素",
        "core_appeal": "悬疑爽、解谜爽",
        "heat": 3,
    },
    "business_war": {
        "id": "business_war",
        "name": "商战文",
        "desc": "以现代商业竞争、公司斗争为主要情节",
        "core_appeal": "智斗爽、财富爽",
        "heat": 3,
    },
    "esports": {
        "id": "esports",
        "name": "电竞文",
        "desc": "以电子竞技为背景",
        "core_appeal": "竞技爽、团队爽",
        "heat": 4,
    },
    "academic": {
        "id": "academic",
        "name": "学霸文",
        "desc": "主角在学业上碾压同龄人",
        "core_appeal": "知识碾压、打脸爽",
        "heat": 4,
    },
}


# ============ 3.1 主要题材与宏观分类 ============

GENRES: dict[str, GenreInfo] = {
    "romance": {
        "id": "romance",
        "name": "言情",
        "desc": "以男女主角情感拉扯为核心",
        "core_appeal": "情感爽、认可爽、护短爽",
        "heat": 5,
        "recommended_plots": ["rebirth", "secret_identity", "group_favorite", "cp_focus", "grovel", "true_false_daughter"],
    },
    "xuanhuan": {
        "id": "xuanhuan",
        "name": "玄幻",
        "desc": "包含东方幻想元素，如修炼、法术等",
        "core_appeal": "成长爽、打脸爽、装逼爽",
        "heat": 4,
        "recommended_plots": ["system", "trash_to_treasure", "face_slap", "levelup", "underdog", "rebirth"],
    },
    "xianxia": {
        "id": "xianxia",
        "name": "仙侠",
        "desc": "以修仙、成仙为主题的幻想小说",
        "core_appeal": "成长爽、获得爽、复仇爽",
        "heat": 4,
        "recommended_plots": ["rebirth", "revenge", "levelup", "system", "trash_to_treasure", "face_slap"],
    },
    "suspense": {
        "id": "suspense",
        "name": "悬疑",
        "desc": "充满谜题、信息差和紧张氛围",
        "core_appeal": "真相揭露、智斗胜利",
        "heat": 5,
        "recommended_plots": ["unlimited_flow", "deification", "crazy_lit", "supernatural", "revenge"],
    },
    "scifi": {
        "id": "scifi",
        "name": "科幻",
        "desc": "包含未来科技、星际社会等元素",
        "core_appeal": "科技碾压、文明对抗",
        "heat": 3,
        "recommended_plots": ["system", "levelup", "farming", "unlimited_flow", "apocalypse"],
    },
    "urban": {
        "id": "urban",
        "name": "都市",
        "desc": "故事背景在现代城市，常与异能、商战结合",
        "core_appeal": "装逼爽、打脸爽、财富爽",
        "heat": 5,
        "recommended_plots": ["rebirth", "secret_identity", "face_slap", "ceo", "entertainment", "business_war", "underdog"],
    },
    "history": {
        "id": "history",
        "name": "历史",
        "desc": "以历史时期为背景",
        "core_appeal": "权谋胜利、改变历史",
        "heat": 3,
        "recommended_plots": ["transmigration", "rebirth", "palace_intrigue", "farming", "revenge"],
    },
    "historical_romance": {
        "id": "historical_romance",
        "name": "古言",
        "desc": "背景设定在古代的言情小说",
        "core_appeal": "情感爽、宫斗胜利",
        "heat": 4,
        "recommended_plots": ["rebirth", "palace_intrigue", "group_favorite", "cp_focus", "true_false_daughter", "transmigration"],
    },
    "no_cp": {
        "id": "no_cp",
        "name": "无CP",
        "desc": "没有固定恋爱关系或感情线",
        "core_appeal": "成长爽、事业爽",
        "heat": 4,
        "recommended_plots": ["unlimited_flow", "levelup", "system", "deification", "crazy_lit", "face_slap"],
    },
}


# ============ 冲突检测规则 ============
# 某些组合存在逻辑冲突，创作时应提示用户

CONFLICT_RULES: list[tuple[str, str, str]] = [
    # (genre_id 或 plot_id, genre_id 或 plot_id, 冲突说明)
    ("no_cp", "ceo", "无CP与总裁文冲突：总裁文核心是感情线"),
    ("no_cp", "cp_focus", "无CP与CP塑造冲突"),
    ("no_cp", "grovel", "无CP与追妻火葬场冲突"),
    ("farming", "unlimited_flow", "种田文（慢节奏）与无限流（快节奏）节奏冲突"),
    ("angst", "face_slap", "虐文与打脸爽文情绪方向相反"),
]


def get_all_genres() -> list[GenreInfo]:
    """返回所有题材列表，按热度降序"""
    return sorted(GENRES.values(), key=lambda g: g["heat"], reverse=True)


def get_plots_for_genre(genre_id: str) -> list[PlotTag]:
    """
    根据题材 ID 返回推荐情节标签列表。
    先返回推荐搭配，再补充其余情节，保证完整可选。
    """
    genre = GENRES.get(genre_id)
    recommended_ids = genre["recommended_plots"] if genre else []

    # 推荐的排在前面
    recommended = [PLOT_TAGS[pid] for pid in recommended_ids if pid in PLOT_TAGS]
    others = [p for pid, p in PLOT_TAGS.items() if pid not in recommended_ids]

    return recommended + others


def get_all_plots() -> list[PlotTag]:
    """返回所有情节标签，按热度降序"""
    return sorted(PLOT_TAGS.values(), key=lambda p: p["heat"], reverse=True)


def check_conflicts(selected_ids: list[str]) -> list[str]:
    """
    检测选中的 genre/plot 组合是否存在冲突。
    返回冲突说明列表，空列表表示无冲突。
    """
    id_set = set(selected_ids)
    warnings = []
    for a, b, msg in CONFLICT_RULES:
        if a in id_set and b in id_set:
            warnings.append(msg)
    return warnings


def build_genre_context(genre_id: str, plot_ids: list[str]) -> str:
    """
    将题材和情节标签组合成可注入 prompt 的上下文字符串。
    供 PromptManager 使用。
    """
    genre = GENRES.get(genre_id)
    genre_line = f"主题材：{genre['name']}（{genre['desc']}）" if genre else ""

    plot_lines = []
    for pid in plot_ids:
        p = PLOT_TAGS.get(pid)
        if p:
            plot_lines.append(f"  - {p['name']}：{p['desc']}，核心爽点：{p['core_appeal']}")

    plots_block = "核心情节流派：\n" + "\n".join(plot_lines) if plot_lines else ""

    conflicts = check_conflicts([genre_id] + plot_ids)
    conflict_block = "⚠️ 注意类型冲突：" + "；".join(conflicts) if conflicts else ""

    parts = [x for x in [genre_line, plots_block, conflict_block] if x]
    return "\n".join(parts)
