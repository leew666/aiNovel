"""
流程编排器使用示例

演示完整的6步创作流程
"""
from ainovel.db import init_database
from ainovel.db import novel_crud
from ainovel.llm import LLMFactory
from ainovel.memory import CharacterDatabase, WorldDatabase
from ainovel.workflow import WorkflowOrchestrator


def main():
    """运行示例"""
    # 1. 初始化数据库
    print("=" * 60)
    print("初始化数据库...")
    db = init_database("sqlite:///test_workflow.db")

    # 创建所有表
    from ainovel.db.base import Base
    from ainovel.db.novel import Novel
    from ainovel.db.volume import Volume
    from ainovel.db.chapter import Chapter
    from ainovel.memory.character import Character
    from ainovel.memory.world_data import WorldData

    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        # 2. 创建小说
        print("\n" + "=" * 60)
        print("步骤0：创建小说...")
        novel = novel_crud.create(
            session,
            title="修仙传奇",
            description="我想写一个修仙题材的小说，主角是一个天赋异禀的少年，从小宗门开始修炼，最终成为天下第一",
            author="AI作者",
        )
        print(f"✓ 创建小说: {novel.title} (ID: {novel.id})")
        print(f"  初始想法: {novel.description}")

        # 3. 初始化LLM客户端和服务
        print("\n" + "=" * 60)
        print("初始化LLM客户端...")
        llm_client = LLMFactory.create_from_env()
        character_db = CharacterDatabase(session)
        world_db = WorldDatabase(session)

        # 4. 创建流程编排器
        orchestrator = WorkflowOrchestrator(llm_client, character_db, world_db)
        print("✓ 流程编排器已就绪")

        # 5. 步骤1：生成创作思路
        print("\n" + "=" * 60)
        print("步骤1：生成创作思路...")
        result_1 = orchestrator.step_1_planning(session, novel.id)
        print(f"✓ 创作思路生成成功!")
        print(f"  题材: {result_1['planning'].get('genre')}")
        print(f"  主题: {result_1['planning'].get('theme')}")
        print(f"  基调: {result_1['planning'].get('tone')}")
        print(f"  核心冲突: {result_1['planning'].get('core_conflict')}")
        print(f"  工作流状态: {result_1['workflow_status']}")
        print(f"  Token使用: {result_1['usage']}")
        print(f"  成本: ${result_1['cost']:.4f}")

        # 可选：用户编辑创作思路
        # planning_edited = json.dumps(result_1['planning'], ensure_ascii=False, indent=2)
        # orchestrator.step_1_update(session, novel.id, planning_edited)

        # 6. 步骤2：生成世界背景和角色
        print("\n" + "=" * 60)
        print("步骤2：生成世界背景和角色...")
        result_2 = orchestrator.step_2_world_building(session, novel.id)
        print(f"✓ 世界观和角色生成成功!")
        print(f"  创建世界观数据: {result_2['stats']['world_data_created']} 条")
        print(f"  创建角色: {result_2['stats']['characters_created']} 个")
        print(f"  工作流状态: {result_2['workflow_status']}")

        # 7. 步骤3：生成大纲
        print("\n" + "=" * 60)
        print("步骤3：生成作品大纲...")
        result_3 = orchestrator.step_3_outline(session, novel.id)
        print(f"✓ 大纲生成成功!")
        print(f"  创建分卷: {result_3['stats']['volumes_created']} 个")
        print(f"  创建章节: {result_3['stats']['chapters_created']} 个")
        print(f"  工作流状态: {result_3['workflow_status']}")

        # 8. 步骤4：生成详细细纲（为所有章节）
        print("\n" + "=" * 60)
        print("步骤4：批量生成详细细纲...")
        result_4 = orchestrator.step_4_batch_detail_outline(session, novel.id)
        print(f"✓ 细纲生成成功!")
        print(f"  总章节数: {result_4['total_chapters']}")
        successful = [r for r in result_4['results'] if r['success']]
        print(f"  成功生成: {len(successful)} 个")
        print(f"  工作流状态: {result_4['workflow_status']}")

        # 9. 步骤5：生成第一章内容
        print("\n" + "=" * 60)
        print("步骤5：生成第一章内容...")
        # 获取第一章
        first_volume = novel.volumes[0]
        first_chapter = first_volume.chapters[0]

        result_5 = orchestrator.step_5_writing(
            session,
            first_chapter.id,
            style_guide="采用网络玄幻小说风格，节奏紧凑，描写细腻",
        )
        print(f"✓ 章节生成成功!")
        print(f"  章节: {first_chapter.title}")
        print(f"  字数: {result_5['stats']['word_count']}")
        print(f"  工作流状态: {result_5['workflow_status']}")

        # 10. 标记完成
        print("\n" + "=" * 60)
        print("标记小说创作完成...")
        final_result = orchestrator.mark_completed(session, novel.id)
        print(f"✓ {final_result['message']}")
        print(f"  最终状态: {final_result['workflow_status']}")

        # 11. 显示最终统计
        print("\n" + "=" * 60)
        print("创作流程统计:")
        print(f"  小说标题: {novel.title}")
        print(f"  分卷数: {len(novel.volumes)}")
        total_chapters = sum(len(v.chapters) for v in novel.volumes)
        print(f"  章节数: {total_chapters}")
        total_words = sum(c.word_count for v in novel.volumes for c in v.chapters)
        print(f"  总字数: {total_words}")
        print("=" * 60)


if __name__ == "__main__":
    main()
