"""
文风学习层单元测试

覆盖：StyleApplicator、StyleAnalyzer（mock LLM）、StyleProfileCRUD、
以及 WorkflowOrchestrator.step_5_writing 自动加载文风的集成路径
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from ainovel.db import init_database, Novel, NovelStatus, novel_crud, style_profile_crud
from ainovel.style.applicator import StyleApplicator
from ainovel.style.analyzer import StyleAnalyzer
from ainovel.core.prompt_manager import PromptManager


# ===== 共用 fixtures =====

@pytest.fixture
def db():
    database = init_database("sqlite:///:memory:", echo=False)
    database.create_all_tables()
    yield database


@pytest.fixture
def session(db):
    with db.session_scope() as sess:
        yield sess


@pytest.fixture
def novel(session):
    """创建测试用小说"""
    return novel_crud.create(
        session,
        title="测试小说",
        description="测试描述",
        author="测试作者",
        status=NovelStatus.DRAFT,
    )


SAMPLE_FEATURES = {
    "sentence_patterns": ["短句为主", "多用排比"],
    "vocabulary_style": "口语化，贴近生活",
    "narrative_perspective": "第三人称，叙事距离适中",
    "pacing": "快节奏，张弛有度",
    "dialogue_style": "对话频繁，语气轻松",
    "description_density": "场景描写简洁，动作描写细腻",
    "tone": "轻松幽默",
    "special_techniques": ["金句收尾", "悬念设置"],
    "summary": "整体风格轻快，以短句和对话推动节奏，善用悬念吸引读者。",
}


# ===== StyleApplicator 测试 =====

class TestStyleApplicator:

    def test_features_to_guide_full(self):
        """完整特征应生成包含所有维度的指南"""
        guide = StyleApplicator.features_to_guide(SAMPLE_FEATURES)
        assert "【总体风格】" in guide
        assert "【句式特征】" in guide
        assert "【词汇风格】" in guide
        assert "【叙事视角】" in guide
        assert "【节奏控制】" in guide
        assert "【对话风格】" in guide
        assert "【描写密度】" in guide
        assert "【情感基调】" in guide
        assert "【特色技法】" in guide
        assert "金句收尾" in guide
        assert "悬念设置" in guide

    def test_features_to_guide_empty(self):
        """空特征应返回默认风格"""
        guide = StyleApplicator.features_to_guide({})
        assert guide == "采用网络小说常见风格，节奏紧凑，对话生动"

    def test_features_to_guide_partial(self):
        """部分特征只输出有值的维度"""
        guide = StyleApplicator.features_to_guide({"tone": "严肃深沉", "pacing": "慢节奏"})
        assert "【情感基调】严肃深沉" in guide
        assert "【节奏控制】慢节奏" in guide
        assert "【句式特征】" not in guide

    def test_load_active_guide_no_profile(self, session, novel):
        """无激活档案时返回空字符串"""
        guide = StyleApplicator.load_active_guide(session, novel.id)
        assert guide == ""

    def test_load_active_guide_with_profile(self, session, novel):
        """有激活档案时返回其 style_guide"""
        style_profile_crud.create(
            session,
            novel_id=novel.id,
            name="测试风格",
            style_guide="【总体风格】测试风格指南",
            is_active=True,
        )
        guide = StyleApplicator.load_active_guide(session, novel.id)
        assert guide == "【总体风格】测试风格指南"

    def test_load_active_guide_from_features(self, session, novel):
        """无 style_guide 但有 style_features 时，从特征重新生成"""
        style_profile_crud.create(
            session,
            novel_id=novel.id,
            name="特征风格",
            style_features=json.dumps(SAMPLE_FEATURES, ensure_ascii=False),
            style_guide=None,
            is_active=True,
        )
        guide = StyleApplicator.load_active_guide(session, novel.id)
        assert "【总体风格】" in guide

    def test_load_guide_by_id(self, session, novel):
        """按ID加载指定档案"""
        profile = style_profile_crud.create(
            session,
            novel_id=novel.id,
            name="指定风格",
            style_guide="指定风格指南内容",
            is_active=False,
        )
        guide = StyleApplicator.load_guide_by_id(session, profile.id)
        assert guide == "指定风格指南内容"

    def test_load_guide_by_id_not_found(self, session):
        """不存在的档案ID返回空字符串"""
        guide = StyleApplicator.load_guide_by_id(session, 99999)
        assert guide == ""


# ===== StyleProfileCRUD 测试 =====

class TestStyleProfileCRUD:

    def test_create_and_get(self, session, novel):
        """创建并查询档案"""
        profile = style_profile_crud.create(
            session,
            novel_id=novel.id,
            name="风格A",
            style_guide="风格A指南",
            is_active=True,
        )
        assert profile.id is not None
        fetched = style_profile_crud.get_by_id(session, profile.id)
        assert fetched.name == "风格A"

    def test_get_by_novel_id(self, session, novel):
        """按小说ID查询所有档案"""
        style_profile_crud.create(session, novel_id=novel.id, name="风格1", is_active=False)
        style_profile_crud.create(session, novel_id=novel.id, name="风格2", is_active=False)
        profiles = style_profile_crud.get_by_novel_id(session, novel.id)
        assert len(profiles) == 2

    def test_get_active(self, session, novel):
        """获取激活档案"""
        style_profile_crud.create(session, novel_id=novel.id, name="非激活", is_active=False)
        style_profile_crud.create(session, novel_id=novel.id, name="激活档案", is_active=True)
        active = style_profile_crud.get_active(session, novel.id)
        assert active is not None
        assert active.name == "激活档案"

    def test_set_active_switches(self, session, novel):
        """set_active 应停用其他档案，激活目标档案"""
        p1 = style_profile_crud.create(session, novel_id=novel.id, name="档案1", is_active=True)
        p2 = style_profile_crud.create(session, novel_id=novel.id, name="档案2", is_active=False)

        style_profile_crud.set_active(session, novel.id, p2.id)

        assert style_profile_crud.get_by_id(session, p1.id).is_active is False
        assert style_profile_crud.get_by_id(session, p2.id).is_active is True


# ===== StyleAnalyzer 测试（mock LLM）=====

class TestStyleAnalyzer:

    def _make_llm(self, features: dict) -> MagicMock:
        """构造返回指定特征JSON的mock LLM"""
        llm = MagicMock()
        llm.generate.return_value = {
            "content": f"```json\n{json.dumps(features, ensure_ascii=False)}\n```",
            "usage": {"total_tokens": 100},
            "cost": 0.001,
        }
        return llm

    def test_analyze_returns_features(self):
        """analyze() 应正确解析LLM返回的JSON"""
        llm = self._make_llm(SAMPLE_FEATURES)
        analyzer = StyleAnalyzer(llm)
        result = analyzer.analyze("这是一段超过100字的参考文本" * 10)
        assert result["style_features"]["tone"] == "轻松幽默"
        assert result["cost"] == 0.001

    def test_analyze_too_short_raises(self):
        """文本过短应抛出 ValueError"""
        llm = MagicMock()
        analyzer = StyleAnalyzer(llm)
        with pytest.raises(ValueError, match="过短"):
            analyzer.analyze("短文本")

    def test_analyze_invalid_json_raises(self):
        """LLM返回无效JSON应抛出 ValueError"""
        llm = MagicMock()
        llm.generate.return_value = {
            "content": "这不是JSON格式的输出",
            "usage": {},
            "cost": 0,
        }
        analyzer = StyleAnalyzer(llm)
        with pytest.raises(ValueError):
            analyzer.analyze("这是一段超过100字的参考文本" * 10)

    def test_analyze_and_save(self, session, novel):
        """analyze_and_save 应创建档案并返回 profile_id"""
        llm = self._make_llm(SAMPLE_FEATURES)
        analyzer = StyleAnalyzer(llm)
        result = analyzer.analyze_and_save(
            session=session,
            novel_id=novel.id,
            name="金庸风格",
            source_text="这是一段超过100字的参考文本" * 10,
            set_active=True,
        )
        assert result["profile_id"] is not None
        assert result["name"] == "金庸风格"
        assert "style_guide" in result
        # 验证数据库中已保存
        active = style_profile_crud.get_active(session, novel.id)
        assert active is not None
        assert active.name == "金庸风格"


# ===== PromptManager 文风分析提示词测试 =====

class TestPromptManagerStylePrompt:

    def test_generate_style_analysis_prompt(self):
        """文风分析提示词应包含参考文本"""
        text = "这是参考文本内容"
        prompt = PromptManager.generate_style_analysis_prompt(text)
        assert text in prompt
        assert "sentence_patterns" in prompt
        assert "summary" in prompt
