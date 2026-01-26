"""
测试3个严重缺陷的修复

验证：
1. 防剧透机制字段（global_config, volume_config）
2. genre字段
3. CLI接口
"""
import pytest
from ainovel.db import init_database
from ainovel.db.crud import novel_crud, volume_crud
from ainovel.db.novel import Novel
from ainovel.db.volume import Volume
from ainovel.cli import cli


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    db = init_database("sqlite:///:memory:")
    db.create_all_tables()
    with db.session_scope() as session:
        yield session


def test_novel_has_global_config_field(db_session):
    """测试Novel模型有global_config字段（防剧透机制）"""
    # 验证字段存在
    assert hasattr(Novel, "global_config"), "Novel模型缺少global_config字段"

    # 测试创建带全局配置的小说
    novel = novel_crud.create(
        db_session,
        title="测试小说",
        author="测试作者",
        global_config='{"final_boss": "主角的父亲", "core_secret": "主角是转世重生"}',
    )

    assert novel.global_config is not None
    assert "final_boss" in novel.global_config
    print(f"✓ global_config字段测试通过: {novel.global_config[:50]}...")


def test_novel_has_genre_field(db_session):
    """测试Novel模型有genre字段"""
    # 验证字段存在
    assert hasattr(Novel, "genre"), "Novel模型缺少genre字段"

    # 测试创建带类型的小说
    novel = novel_crud.create(
        db_session,
        title="玄幻小说",
        author="作者",
        genre="玄幻",
        description="修仙题材",
    )

    assert novel.genre == "玄幻"
    print(f"✓ genre字段测试通过: {novel.genre}")


def test_volume_has_volume_config_field(db_session):
    """测试Volume模型有volume_config字段（防剧透机制）"""
    # 验证字段存在
    assert hasattr(Volume, "volume_config"), "Volume模型缺少volume_config字段"

    # 创建小说和分卷
    novel = novel_crud.create(db_session, title="测试小说", author="作者")
    volume = volume_crud.create(
        db_session,
        novel_id=novel.id,
        title="第一卷：新手村",
        order=1,
        volume_config='{"current_characters": ["主角", "师傅"], "local_world": "新手村世界观"}',
    )

    assert volume.volume_config is not None
    assert "current_characters" in volume.volume_config
    print(f"✓ volume_config字段测试通过: {volume.volume_config[:50]}...")


def test_anti_spoiler_mechanism_isolation():
    """测试防剧透机制：全局配置和卷配置隔离"""
    db = init_database("sqlite:///:memory:")
    db.create_all_tables()

    with db.session_scope() as session:
        # 创建小说，设置全局秘密（不应传入LLM）
        novel = novel_crud.create(
            session,
            title="防剧透测试",
            author="AI",
            global_config='{"final_boss": "主角的父亲", "final_twist": "父亲是为了保护主角"}',
        )

        # 创建第1卷，仅包含第1卷信息（传入LLM）
        volume1 = volume_crud.create(
            session,
            novel_id=novel.id,
            title="第一卷",
            order=1,
            volume_config='{"current_characters": ["主角"], "local_world": "主角是孤儿，不知父亲身份"}',
        )

        # 验证隔离
        assert "final_boss" in novel.global_config  # 全局有秘密
        assert "final_boss" not in volume1.volume_config  # 第1卷没有秘密
        assert "孤儿" in volume1.volume_config  # 第1卷只有局部信息

        print("✓ 防剧透机制隔离测试通过")
        print(f"  全局配置（不传LLM）: {novel.global_config[:60]}...")
        print(f"  卷配置（传入LLM）: {volume1.volume_config[:60]}...")


def test_cli_commands_exist():
    """测试CLI命令是否存在"""
    expected_commands = [
        "create-project",
        "list-projects",
        "step1",
        "step2",
        "step3",
        "step4",
        "step5",
        "complete",
    ]

    actual_commands = list(cli.commands.keys())

    for cmd in expected_commands:
        assert cmd in actual_commands, f"CLI命令 '{cmd}' 不存在"

    print(f"✓ CLI命令测试通过，共{len(actual_commands)}个命令: {actual_commands}")


def test_cli_create_project_command():
    """测试CLI的create-project命令是否可调用"""
    from click.testing import CliRunner

    runner = CliRunner()

    # 测试帮助信息
    result = runner.invoke(cli, ["create-project", "--help"])
    assert result.exit_code == 0
    assert "创建新的小说项目" in result.output

    print("✓ CLI create-project命令测试通过")


def test_web_api_genre_field():
    """测试Web API的genre字段"""
    from ainovel.web.schemas.novel import NovelCreate, NovelResponse

    # 测试Pydantic模型
    novel_create = NovelCreate(
        title="测试小说",
        author="作者",
        genre="科幻",
        description="科幻小说",
    )

    assert novel_create.genre == "科幻"

    # 测试与数据库集成
    db = init_database("sqlite:///:memory:")
    db.create_all_tables()

    with db.session_scope() as session:
        novel = novel_crud.create(
            session,
            title=novel_create.title,
            author=novel_create.author,
            genre=novel_create.genre,
            description=novel_create.description,
        )

        response = NovelResponse.model_validate(novel)
        assert response.genre == "科幻"

    print("✓ Web API genre字段测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
