"""
数据库使用示例

展示如何使用 aiNovel 数据库层进行 CRUD 操作
"""
from ainovel.db import (
    init_database,
    get_database,
    Novel,
    NovelStatus,
    novel_crud,
    volume_crud,
    chapter_crud,
)


def main():
    """主函数：演示数据库操作"""
    # 1. 初始化数据库
    print("=== 初始化数据库 ===")
    db = init_database("sqlite:///example.db", echo=False)
    db.create_all_tables()
    print("数据库初始化完成\n")

    # 2. 创建小说
    print("=== 创建小说 ===")
    with db.session_scope() as session:
        novel = novel_crud.create(
            session,
            title="仙侠传奇",
            description="一个关于修仙的故事",
            author="AI 作者",
            status=NovelStatus.ONGOING,
        )
        print(f"创建小说: {novel}\n")

    # 3. 创建分卷
    print("=== 创建分卷 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        volume1 = volume_crud.create(
            session,
            novel_id=novel.id,
            title="第一卷：凡人起步",
            order=1,
            description="主角从凡人开始修仙的故事",
        )
        volume2 = volume_crud.create(
            session,
            novel_id=novel.id,
            title="第二卷：踏入仙门",
            order=2,
            description="主角加入仙门，开始系统修炼",
        )
        print(f"创建分卷: {volume1}")
        print(f"创建分卷: {volume2}\n")

    # 4. 创建章节
    print("=== 创建章节 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        volumes = volume_crud.get_by_novel_id(session, novel.id)
        volume1 = volumes[0]

        chapter1 = chapter_crud.create(
            session,
            volume_id=volume1.id,
            title="第一章：少年林峰",
            order=1,
            content="在青云镇，有一个名叫林峰的少年，他从小立志要成为修仙者...",
        )
        chapter1.update_word_count()

        chapter2 = chapter_crud.create(
            session,
            volume_id=volume1.id,
            title="第二章：奇遇",
            order=2,
            content="某天，林峰在山中采药时，意外发现了一个古老的洞府...",
        )
        chapter2.update_word_count()

        print(f"创建章节: {chapter1}")
        print(f"创建章节: {chapter2}\n")

    # 5. 查询数据
    print("=== 查询数据 ===")
    with db.session_scope() as session:
        # 查询所有小说
        novels = novel_crud.get_all(session)
        print(f"所有小说数量: {len(novels)}")

        # 查询特定小说
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        print(f"查询小说: {novel.title}, 状态: {novel.status.value}")

        # 查询分卷
        volumes = volume_crud.get_by_novel_id(session, novel.id)
        print(f"分卷数量: {len(volumes)}")

        # 查询章节
        chapters = chapter_crud.get_by_volume_id(session, volumes[0].id)
        print(f"第一卷章节数量: {len(chapters)}")
        for chapter in chapters:
            print(f"  - {chapter.title}, 字数: {chapter.word_count}\n")

    # 6. 更新数据
    print("=== 更新数据 ===")
    with db.session_scope() as session:
        novel = novel_crud.get_by_title(session, "仙侠传奇")
        novel_crud.update(session, novel.id, status=NovelStatus.COMPLETED)
        print(f"小说状态已更新为: {NovelStatus.COMPLETED.value}\n")

    # 7. 搜索章节
    print("=== 搜索章节 ===")
    with db.session_scope() as session:
        results = chapter_crud.search_by_content(session, "林峰")
        print(f"包含'林峰'的章节数量: {len(results)}")
        for chapter in results:
            print(f"  - {chapter.title}\n")

    print("=== 示例完成 ===")


if __name__ == "__main__":
    main()
