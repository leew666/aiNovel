"""
生成核心层使用示例

演示如何使用OutlineGenerator和ChapterGenerator生成小说内容
"""
import os
from ainovel.db import init_database, get_database
from ainovel.db import novel_crud, volume_crud, chapter_crud
from ainovel.memory import CharacterDatabase, WorldDatabase, MBTIType
from ainovel.llm import LLMFactory, LLMConfig
from ainovel.core import OutlineGenerator, ChapterGenerator


def main():
    """主函数"""
    print("=== 生成核心层使用示例 ===\n")

    # 1. 初始化数据库
    print("1. 初始化数据库...")
    db = init_database("sqlite:///novel_generator_example.db")

    # 创建所有表
    from ainovel.db.base import Base

    Base.metadata.create_all(db.engine)

    # 2. 配置LLM客户端（需要设置环境变量）
    print("2. 配置LLM客户端...")
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告: 未设置OPENAI_API_KEY环境变量，将使用Mock模式")
        print("   请设置环境变量后再运行以使用真实LLM\n")
        # 使用Mock客户端进行演示
        from unittest.mock import Mock

        llm_client = Mock()
        llm_client.generate.return_value = {
            "content": """```json
{
  "volumes": [
    {
      "title": "第一卷：新手村",
      "description": "主角踏入修仙之路，开始崭新的冒险",
      "order": 1,
      "chapters": [
        {
          "title": "第一章：觉醒",
          "order": 1,
          "summary": "主角张三在一次意外中发现自己拥有特殊天赋，被青云宗长老发现并带回宗门。",
          "key_events": ["灵根测试", "拜师仪式", "领取法器"],
          "characters_involved": ["张三"]
        },
        {
          "title": "第二章：初入宗门",
          "order": 2,
          "summary": "张三初入青云宗，认识了同门师兄弟李四，开始了修炼生涯。",
          "key_events": ["结识李四", "分配住所", "开始修炼"],
          "characters_involved": ["张三", "李四"]
        }
      ]
    }
  ]
}
```""",
            "usage": {"input_tokens": 500, "output_tokens": 300, "total_tokens": 800},
            "cost": 0.02,
        }
    else:
        config = LLMConfig.from_env()
        llm_client = LLMFactory.create_client(config)

    with db.session_scope() as session:
        # 3. 创建小说
        print("3. 创建小说...")
        novel = novel_crud.create(
            session,
            title="修仙传奇",
            description="一个关于修仙者的传奇故事",
            author="示例作者",
        )
        print(f"   ✓ 创建小说: {novel.title} (ID: {novel.id})\n")

        # 4. 创建角色
        print("4. 创建角色...")
        char_db = CharacterDatabase(session)

        zhang_san = char_db.create_character(
            novel_id=novel.id,
            name="张三",
            mbti=MBTIType.INTJ,
            background="天生拥有特殊灵根，渴望探索修仙世界的真相",
            personality_traits={"勇气": 9, "智慧": 8, "谨慎": 7},
        )
        print(f"   ✓ 创建角色: {zhang_san.name} ({zhang_san.mbti})")

        li_si = char_db.create_character(
            novel_id=novel.id,
            name="李四",
            mbti=MBTIType.ENFP,
            background="乐观开朗的商人之子，善于交际",
            personality_traits={"魅力": 9, "社交": 8, "财富": 7},
        )
        print(f"   ✓ 创建角色: {li_si.name} ({li_si.mbti})\n")

        # 5. 创建世界观
        print("5. 创建世界观...")
        world_db = WorldDatabase(session)

        world_db.create_rule(
            novel_id=novel.id,
            name="修仙体系",
            description="修仙者的境界划分，从低到高分为：炼气、筑基、金丹、元婴、化神",
            category="设定",
        )
        print("   ✓ 创建规则: 修仙体系")

        world_db.create_location(
            novel_id=novel.id,
            name="青云宗",
            description="主角所在的修仙宗门，位于青云山上，是大陆十大宗门之一",
            notable_features="拥有悠久历史，藏书楼收藏大量功法",
        )
        print("   ✓ 创建地点: 青云宗\n")

        # 6. 生成大纲
        print("6. 生成小说大纲...")
        outline_generator = OutlineGenerator(llm_client, session)

        try:
            result = outline_generator.generate_and_save(novel.id)

            print(f"   ✓ 大纲生成成功!")
            print(f"   - 创建分卷数: {result['stats']['volumes_created']}")
            print(f"   - 创建章节数: {result['stats']['chapters_created']}")
            print(f"   - Token使用: {result['usage']['total_tokens']}")
            print(f"   - 成本: ${result['cost']:.4f}\n")

        except Exception as e:
            print(f"   ✗ 大纲生成失败: {e}\n")
            return

        # 7. 生成第一章内容
        print("7. 生成第一章内容...")

        # Mock章节生成响应（真实使用时会调用LLM）
        if isinstance(llm_client, Mock):
            llm_client.generate.return_value = {
                "content": """
第一章 觉醒

清晨的阳光透过窗棂洒在张三的脸上，他缓缓睁开双眼。

今天是他十六岁生辰，也是村子里一年一度的灵根测试之日。青云宗的长老会来到村子，为年满十六岁的少年测试灵根资质，有缘者可随长老前往青云宗修炼。

"张三！还不起床？"母亲的声音从院子里传来。

张三翻身坐起，整理好衣衫走出房门。院子里，母亲已经准备好了早饭。

"今天可是大日子，吃饱了才有力气。"母亲笑着说。

张三心中有些忐忑，虽然他一直梦想着成为修仙者，但真到了这一天，反而有些紧张了。

吃过早饭，村子中央的广场上已经聚集了不少人。一位白发苍苍的老者端坐在高台上，正是青云宗的长老。

"下一个，张三。"

张三深吸一口气，走上前去......
""",
                "usage": {"input_tokens": 800, "output_tokens": 500, "total_tokens": 1300},
                "cost": 0.03,
            }

        # 获取第一个分卷的第一章
        volumes = volume_crud.get_by_novel_id(session, novel.id)
        if volumes:
            chapters = chapter_crud.get_by_volume_id(session, volumes[0].id)
            if chapters:
                chapter_generator = ChapterGenerator(llm_client, session)

                try:
                    result = chapter_generator.generate_and_save(
                        chapters[0].id,
                        word_count_min=2000,
                        word_count_max=3000,
                    )

                    print(f"   ✓ 章节生成成功!")
                    print(f"   - 章节ID: {result['stats']['chapter_id']}")
                    print(f"   - 字数: {result['stats']['word_count']}")
                    print(f"   - Token使用: {result['usage']['total_tokens']}")
                    print(f"   - 成本: ${result['cost']:.4f}\n")

                    # 显示前200字
                    print("   内容预览:")
                    print(f"   {result['content'][:200]}...\n")

                except Exception as e:
                    print(f"   ✗ 章节生成失败: {e}\n")

        print("=== 示例完成 ===")
        print(f"\n数据库文件: novel_generator_example.db")
        print("你可以使用SQLite工具查看生成的数据")


if __name__ == "__main__":
    main()
