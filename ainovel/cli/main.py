"""
CLI 命令行接口

提供命令行方式操作aiNovel系统
"""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from loguru import logger

from ainovel.db import init_database
from ainovel.db.crud import novel_crud, volume_crud, chapter_crud
from ainovel.llm.factory import LLMFactory
from ainovel.workflow import WorkflowOrchestrator
from ainovel.memory import CharacterDatabase, WorldDatabase

console = Console()


def get_db():
    """获取数据库实例"""
    db_path = Path("data/ainovel.db")
    db_path.parent.mkdir(exist_ok=True)
    return init_database(f"sqlite:///{db_path}")


def get_orchestrator(session):
    """获取工作流编排器"""
    llm_client = LLMFactory.create_from_env()
    character_db = CharacterDatabase(session)
    world_db = WorldDatabase(session)
    return WorkflowOrchestrator(llm_client, character_db, world_db)


@click.group()
@click.version_option(version="0.1.0", prog_name="ainovel")
def cli():
    """
    AI小说创作系统 - 命令行工具

    支持300万字长篇小说自动化创作，具备防剧透机制和强大的人物一致性保障。
    """
    pass


@cli.command()
@click.argument("title")
@click.option("--author", default="AI创作", help="作者名称")
@click.option("--genre", default="玄幻", help="小说类型（如玄幻、都市、科幻）")
@click.option("--description", default="", help="小说简介")
def create_project(title: str, author: str, genre: str, description: str):
    """
    创建新的小说项目

    示例：ainovel create-project "修仙废材逆袭" --author "张三" --genre "玄幻"
    """
    try:
        db = get_db()
        db.create_all_tables()

        with db.session_scope() as session:
            # 检查是否已存在
            existing = novel_crud.get_by_title(session, title)
            if existing:
                console.print(f"[red]错误：小说 '{title}' 已存在（ID={existing.id}）[/red]")
                return

            # 创建新项目
            novel = novel_crud.create(
                session,
                title=title,
                author=author,
                genre=genre,
                description=description or f"一部{genre}题材的长篇小说",
            )

            console.print(Panel.fit(
                f"[green]✓[/green] 项目创建成功！\n\n"
                f"[cyan]项目ID:[/cyan] {novel.id}\n"
                f"[cyan]标题:[/cyan] {novel.title}\n"
                f"[cyan]作者:[/cyan] {novel.author}\n"
                f"[cyan]类型:[/cyan] {novel.genre}\n"
                f"[cyan]状态:[/cyan] {novel.workflow_status.value}",
                title="新建项目",
                border_style="green"
            ))

            console.print(f"\n[yellow]下一步:[/yellow] 运行 [bold]ainovel step1 {novel.id}[/bold] 开始创作")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("创建项目失败")


@cli.command()
@click.option("--limit", default=10, help="显示数量")
def list_projects(limit: int):
    """
    列出所有小说项目

    示例：ainovel list-projects --limit 20
    """
    try:
        db = get_db()

        with db.session_scope() as session:
            novels = novel_crud.get_all(session, limit=limit)

            if not novels:
                console.print("[yellow]暂无项目，使用 'ainovel create-project <标题>' 创建[/yellow]")
                return

            table = Table(title="小说项目列表", show_header=True, header_style="bold cyan")
            table.add_column("ID", style="dim", width=6)
            table.add_column("标题", min_width=20)
            table.add_column("作者", width=12)
            table.add_column("类型", width=10)
            table.add_column("状态", width=15)
            table.add_column("步骤", width=8)

            for novel in novels:
                table.add_row(
                    str(novel.id),
                    novel.title,
                    novel.author or "-",
                    novel.genre or "-",
                    novel.workflow_status.value,
                    f"{novel.current_step}/5"
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("列出项目失败")


@cli.command()
@click.argument("novel_id", type=int)
@click.option("--idea", prompt="请输入创作想法", help="初始创作想法")
def step1(novel_id: int, idea: str):
    """
    步骤1：生成创作思路

    示例：ainovel step1 1 --idea "一个被退婚的废材少年，偶然获得神秘戒指"
    """
    try:
        db = get_db()

        with db.session_scope() as session:
            orchestrator = get_orchestrator(session)

            console.print(f"[cyan]正在为小说 ID={novel_id} 生成创作思路...[/cyan]")

            result = orchestrator.step_1_planning(
                session=session,
                novel_id=novel_id,
                initial_idea=idea
            )

            console.print(Panel.fit(
                f"[green]✓[/green] 步骤1完成！\n\n"
                f"[cyan]题材:[/cyan] {result['planning']['genre']}\n"
                f"[cyan]主题:[/cyan] {result['planning']['theme']}\n"
                f"[cyan]预计长度:[/cyan] {result['planning']['estimated_length']['volumes']}卷\n"
                f"[cyan]Token使用:[/cyan] {result['usage']['total_tokens']}\n"
                f"[cyan]成本:[/cyan] ${result['cost']:.4f}",
                title="创作思路",
                border_style="green"
            ))

            console.print(f"\n[yellow]下一步:[/yellow] 运行 [bold]ainovel step2 {novel_id}[/bold] 生成世界观和角色")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("步骤1失败")


@cli.command()
@click.argument("novel_id", type=int)
def step2(novel_id: int):
    """
    步骤2：生成世界观和角色

    示例：ainovel step2 1
    """
    try:
        db = get_db()

        with db.session_scope() as session:
            orchestrator = get_orchestrator(session)

            console.print(f"[cyan]正在为小说 ID={novel_id} 生成世界观和角色...[/cyan]")

            result = orchestrator.step_2_world_building(session=session, novel_id=novel_id)

            console.print(Panel.fit(
                f"[green]✓[/green] 步骤2完成！\n\n"
                f"[cyan]创建角色:[/cyan] {result['stats']['characters_created']}个\n"
                f"[cyan]创建世界观:[/cyan] {result['stats']['world_data_created']}条\n"
                f"[cyan]Token使用:[/cyan] {result['usage']['total_tokens']}\n"
                f"[cyan]成本:[/cyan] ${result['cost']:.4f}",
                title="世界观和角色",
                border_style="green"
            ))

            console.print(f"\n[yellow]下一步:[/yellow] 运行 [bold]ainovel step3 {novel_id}[/bold] 生成大纲")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("步骤2失败")


@cli.command()
@click.argument("novel_id", type=int)
def step3(novel_id: int):
    """
    步骤3：生成作品大纲

    示例：ainovel step3 1
    """
    try:
        db = get_db()

        with db.session_scope() as session:
            orchestrator = get_orchestrator(session)

            console.print(f"[cyan]正在为小说 ID={novel_id} 生成大纲...[/cyan]")

            result = orchestrator.step_3_outline(session=session, novel_id=novel_id)

            console.print(Panel.fit(
                f"[green]✓[/green] 步骤3完成！\n\n"
                f"[cyan]创建分卷:[/cyan] {result['stats']['volumes_created']}个\n"
                f"[cyan]创建章节:[/cyan] {result['stats']['chapters_created']}个\n"
                f"[cyan]Token使用:[/cyan] {result['usage']['total_tokens']}\n"
                f"[cyan]成本:[/cyan] ${result['cost']:.4f}",
                title="作品大纲",
                border_style="green"
            ))

            console.print(f"\n[yellow]下一步:[/yellow] 运行 [bold]ainovel step4 {novel_id}[/bold] 生成细纲")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("步骤3失败")


@cli.command()
@click.argument("novel_id", type=int)
@click.option("--batch", is_flag=True, help="批量生成所有章节的细纲")
def step4(novel_id: int, batch: bool):
    """
    步骤4：生成详细细纲

    示例：ainovel step4 1 --batch
    """
    try:
        db = get_db()

        with db.session_scope() as session:
            orchestrator = get_orchestrator(session)

            if batch:
                console.print(f"[cyan]正在为小说 ID={novel_id} 批量生成细纲...[/cyan]")
                result = orchestrator.step_4_batch_detail_outline(session=session, novel_id=novel_id)

                success_count = sum(1 for r in result['results'] if r['success'])
                console.print(Panel.fit(
                    f"[green]✓[/green] 步骤4完成！\n\n"
                    f"[cyan]总章节:[/cyan] {result['total_chapters']}个\n"
                    f"[cyan]成功:[/cyan] {success_count}个\n"
                    f"[cyan]失败:[/cyan] {result['total_chapters'] - success_count}个",
                    title="批量生成细纲",
                    border_style="green"
                ))
            else:
                console.print(f"[yellow]提示：使用 --batch 参数可批量生成所有章节细纲[/yellow]")

            console.print(f"\n[yellow]下一步:[/yellow] 运行 [bold]ainovel step5 {novel_id}[/bold] 生成章节内容")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("步骤4失败")


@cli.command()
@click.argument("novel_id", type=int)
@click.option("--chapters", default="1", help="章节范围，如 1 或 1-10")
def step5(novel_id: int, chapters: str):
    """
    步骤5：生成章节内容

    示例：ainovel step5 1 --chapters 1-10
    """
    try:
        db = get_db()

        with db.session_scope() as session:
            novel = novel_crud.get_by_id(session, novel_id)
            if not novel:
                console.print(f"[red]错误：小说 ID={novel_id} 不存在[/red]")
                return

            # 解析章节范围
            if "-" in chapters:
                start, end = map(int, chapters.split("-"))
                chapter_range = range(start, end + 1)
            else:
                chapter_range = [int(chapters)]

            # 获取所有章节
            all_chapters = []
            for volume in novel.volumes:
                all_chapters.extend(volume.chapters)

            orchestrator = get_orchestrator(session)

            console.print(f"[cyan]正在生成章节内容...[/cyan]")

            for idx in chapter_range:
                if idx > len(all_chapters):
                    console.print(f"[yellow]警告：章节 {idx} 不存在，跳过[/yellow]")
                    continue

                chapter = all_chapters[idx - 1]
                console.print(f"[cyan]生成第 {idx} 章: {chapter.title}[/cyan]")

                result = orchestrator.step_5_writing(
                    session=session,
                    chapter_id=chapter.id
                )

                console.print(f"[green]✓[/green] 字数: {result['word_count']} | Token: {result['usage']['total_tokens']} | 成本: ${result['cost']:.4f}")

            console.print(f"\n[green]✓[/green] 章节生成完成！")
            console.print(f"\n[yellow]下一步:[/yellow] 运行 [bold]ainovel complete {novel_id}[/bold] 标记完成")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("步骤5失败")


@cli.command()
@click.argument("novel_id", type=int)
def complete(novel_id: int):
    """
    标记小说创作完成

    示例：ainovel complete 1
    """
    try:
        db = get_db()

        with db.session_scope() as session:
            orchestrator = get_orchestrator(session)

            result = orchestrator.mark_completed(session=session, novel_id=novel_id)

            console.print(Panel.fit(
                f"[green]✓[/green] 小说创作流程已完成！\n\n"
                f"[cyan]项目ID:[/cyan] {result['novel_id']}\n"
                f"[cyan]状态:[/cyan] {result['workflow_status']}",
                title="创作完成",
                border_style="green"
            ))

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("标记完成失败")


if __name__ == "__main__":
    cli()
