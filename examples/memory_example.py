"""
记忆管理层使用示例

展示如何使用 CharacterDatabase 和 WorldDatabase 管理角色和世界观数据
"""
from ainovel.db import init_database, get_database, novel_crud
from ainovel.memory import (
    MBTIType,
    WorldDataType,
    CharacterDatabase,
    WorldDatabase,
)


def main():
    """主函数：演示记忆管理操作"""
    # 1. 初始化数据库
    print("=== 初始化数据库 ===")
    db = init_database("sqlite:///example_memory.db", echo=False)
    db.create_all_tables()
    print("数据库初始化完成\n")

    # 2. 创建小说
    print("=== 创建小说 ===")
    with db.session_scope() as session:
        novel = novel_crud.create(session, title="仙侠传奇", author="AI 作者")
        print(f"创建小说: {novel.title}\n")

    # 3. 使用 CharacterDatabase 创建角色
    print("=== 创建角色 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        char_db = CharacterDatabase(session)

        # 创建主角
        protagonist = char_db.create_character(
            novel_id=novel.id,
            name="林峰",
            mbti=MBTIType.INTJ,
            background="青云镇普通少年，立志成为修仙者",
            personality_traits={"勇敢": 8, "智慧": 9, "谨慎": 7, "善良": 8},
        )
        print(f"创建角色: {protagonist.name}")
        print(f"  MBTI: {protagonist.mbti.value} - {protagonist.get_mbti_description()}")
        print(f"  性格特征: {protagonist.personality_traits}\n")

        # 创建师父
        master = char_db.create_character(
            novel_id=novel.id,
            name="云中子",
            mbti=MBTIType.ISTJ,
            background="青云宗掌门，修为高深",
            personality_traits={"勇敢": 10, "智慧": 10, "谨慎": 9, "严格": 9},
        )
        print(f"创建角色: {master.name}\n")

    # 4. 添加角色记忆
    print("=== 添加角色记忆 ===")
    with db.session_scope() as session:
        char_db = CharacterDatabase(session)
        protagonist = char_db.get_character_by_name(novel.id, "林峰")

        char_db.add_memory(
            character_id=protagonist.id,
            event="初遇师父",
            content="在青云山遇见了云中子师父，从此踏上修仙之路",
            volume_id=1,
            chapter_id=1,
            importance="high",
        )

        char_db.add_memory(
            character_id=protagonist.id,
            event="学会御剑术",
            content="经过三个月苦练，终于掌握了基础御剑术",
            volume_id=1,
            chapter_id=5,
            importance="medium",
        )

        memories = char_db.get_character_memories(protagonist.id)
        print(f"{protagonist.name}的记忆数量: {len(memories)}")
        for memory in memories:
            print(f"  - {memory['event']}: {memory['content']}\n")

    # 5. 添加角色关系
    print("=== 添加角色关系 ===")
    with db.session_scope() as session:
        char_db = CharacterDatabase(session)
        protagonist = char_db.get_character_by_name(novel.id, "林峰")

        char_db.add_relationship(
            character_id=protagonist.id,
            target_character_name="云中子",
            relation_type="师徒",
            intimacy=8,
            first_met_chapter=1,
            notes="我的师父，教我修炼",
        )

        relationships = char_db.get_character_relationships(protagonist.id)
        print(f"{protagonist.name}的关系网络:")
        for name, relation in relationships.items():
            print(f"  - {name}: {relation['relation_type']}, 亲密度 {relation['intimacy']}/10\n")

    # 6. 使用 WorldDatabase 创建世界观数据
    print("=== 创建世界观数据 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        world_db = WorldDatabase(session)

        # 创建地点
        location = world_db.create_location(
            novel_id=novel.id,
            name="青云山",
            description="青云宗所在的灵山，山顶常年云雾缭绕",
            coordinates="东经120°，北纬30°",
            climate="四季如春",
            population=5000,
            notable_features="山顶有天然剑阵，可用于修炼剑道",
        )
        print(f"创建地点: {location.name}")
        print(f"  描述: {location.description}")
        print(f"  属性: {location.properties}\n")

        # 创建组织
        organization = world_db.create_organization(
            novel_id=novel.id,
            name="青云宗",
            description="正道第一大宗门，以剑道闻名天下",
            leader="云中子",
            members_count=5000,
            power_level="一流",
            territory="青云山及周边百里",
        )
        print(f"创建组织: {organization.name}")
        print(f"  领导者: {organization.properties['leader']}")
        print(f"  实力等级: {organization.properties['power_level']}\n")

        # 创建物品
        item = world_db.create_item(
            novel_id=novel.id,
            name="紫霄剑",
            description="上古神剑，削铁如泥",
            rarity="传说",
            power_level=10,
            owner="林峰",
            abilities="可斩断虚空，御剑飞行速度提升300%",
        )
        print(f"创建物品: {item.name}")
        print(f"  稀有度: {item.properties['rarity']}")
        print(f"  威力: {item.properties['power_level']}/10\n")

        # 创建规则
        rule = world_db.create_rule(
            novel_id=novel.id,
            name="修炼等级体系",
            description="本世界的修炼体系分为：练气、筑基、金丹、元婴、化神、炼虚、合体、大乘、渡劫",
            category="修炼系统",
            limitations="每提升一个大境界需要渡劫，失败则身死道消",
        )
        print(f"创建规则: {rule.name}")
        print(f"  分类: {rule.properties['category']}\n")

    # 7. 查询世界观数据
    print("=== 查询世界观数据 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        world_db = WorldDatabase(session)

        # 按类型查询
        locations = world_db.list_locations(novel.id)
        print(f"地点数量: {len(locations)}")

        organizations = world_db.list_organizations(novel.id)
        print(f"组织数量: {len(organizations)}")

        items = world_db.list_items(novel.id)
        print(f"物品数量: {len(items)}")

        rules = world_db.list_rules(novel.id)
        print(f"规则数量: {len(rules)}\n")

    # 8. 搜索数据
    print("=== 搜索数据 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        char_db = CharacterDatabase(session)
        world_db = WorldDatabase(session)

        # 搜索角色
        characters = char_db.search_characters(novel.id, "林")
        print(f"包含'林'的角色: {[c.name for c in characters]}")

        # 搜索世界观数据
        results = world_db.search(novel.id, "青云")
        print(f"包含'青云'的世界观数据: {[r.name for r in results]}\n")

    # 9. 按 MBTI 查询角色
    print("=== 按 MBTI 查询角色 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        char_db = CharacterDatabase(session)

        intj_characters = char_db.list_characters_by_mbti(novel.id, MBTIType.INTJ)
        print(f"INTJ 类型的角色: {[c.name for c in intj_characters]}\n")

    print("=== 示例完成 ===")


if __name__ == "__main__":
    main()
