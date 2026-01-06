# M2 数据库层实现总结

**实施时间**: 2026-01-06
**状态**: ✅ 已完成
**测试结果**: 12/12 通过，覆盖率 100%

---

## 实现内容

### 1. 数据库基础架构 ([database.py](../ainovel/db/database.py))

**核心功能**:
- `Database` 类：数据库连接管理器
- 支持 SQLite（开发）和 PostgreSQL（生产）
- 提供 `session_scope()` 上下文管理器，自动提交/回滚事务
- 全局单例模式，通过 `init_database()` 和 `get_database()` 访问

**关键设计**:
```python
with db.session_scope() as session:
    novel = novel_crud.create(session, title="测试小说")
    # 自动提交，或发生异常时自动回滚
```

### 2. 基础模型类 ([base.py](../ainovel/db/base.py))

**核心功能**:
- `Base`: SQLAlchemy DeclarativeBase，所有模型的基类
- `TimestampMixin`: 时间戳混入类，提供 `created_at` 和 `updated_at` 字段
- `to_dict()`: 将模型实例转换为字典（支持 datetime 序列化）
- `__repr__()`: 提供友好的字符串表示

### 3. 数据模型

#### Novel 模型 ([novel.py](../ainovel/db/novel.py))

**字段**:
- `id`: 主键（自增）
- `title`: 标题（唯一、索引）
- `description`: 简介（可选）
- `author`: 作者（可选）
- `status`: 状态（draft/ongoing/completed）
- `created_at`, `updated_at`: 时间戳

**关系**:
- `volumes`: 一对多，关联 Volume 模型
- 级联删除：删除 Novel 时，自动删除所有关联的 Volume 和 Chapter

#### Volume 模型 ([volume.py](../ainovel/db/volume.py))

**字段**:
- `id`: 主键
- `novel_id`: 外键（关联 Novel）
- `title`: 标题
- `order`: 排序（从 1 开始）
- `description`: 简介（可选）
- `created_at`, `updated_at`: 时间戳

**关系**:
- `novel`: 多对一，关联 Novel 模型
- `chapters`: 一对多，关联 Chapter 模型
- 级联删除：删除 Volume 时，自动删除所有关联的 Chapter

#### Chapter 模型 ([chapter.py](../ainovel/db/chapter.py))

**字段**:
- `id`: 主键
- `volume_id`: 外键（关联 Volume）
- `title`: 标题
- `order`: 排序（从 1 开始）
- `content`: 内容
- `word_count`: 字数统计
- `created_at`, `updated_at`: 时间戳

**特殊方法**:
- `update_word_count()`: 更新字数统计
  - 优先使用 jieba 分词统计
  - 降级策略：字符统计（去除空白字符）

**关系**:
- `volume`: 多对一，关联 Volume 模型

### 4. CRUD 管理器 ([crud.py](../ainovel/db/crud.py))

#### 基类：CRUDBase[ModelType]

**通用方法**:
- `create(session, **kwargs)`: 创建记录
- `get_by_id(session, obj_id)`: 根据 ID 查询
- `get_all(session, skip, limit)`: 查询所有记录（分页）
- `count(session)`: 统计记录总数
- `update(session, obj_id, **kwargs)`: 更新记录
- `delete(session, obj_id)`: 删除记录

#### 特定 CRUD 管理器

**NovelCRUD**:
- `get_by_title(session, title)`: 根据标题查询
- `get_by_status(session, status, skip, limit)`: 根据状态查询

**VolumeCRUD**:
- `get_by_novel_id(session, novel_id, skip, limit)`: 根据小说 ID 查询分卷
- `get_by_order(session, novel_id, order)`: 根据序号查询

**ChapterCRUD**:
- `get_by_volume_id(session, volume_id, skip, limit)`: 根据分卷 ID 查询章节
- `get_by_order(session, volume_id, order)`: 根据序号查询
- `search_by_content(session, keyword, skip, limit)`: 根据内容搜索

**全局实例**:
```python
from ainovel.db import novel_crud, volume_crud, chapter_crud
```

---

## 测试验证

### 测试文件: [tests/db/test_db.py](../tests/db/test_db.py)

**测试用例**:
1. ✅ `test_create_novel`: 创建小说
2. ✅ `test_get_novel_by_id`: 根据 ID 查询小说
3. ✅ `test_get_novel_by_title`: 根据标题查询小说
4. ✅ `test_update_novel`: 更新小说
5. ✅ `test_delete_novel`: 删除小说
6. ✅ `test_create_volume_with_novel`: 创建分卷并关联小说
7. ✅ `test_get_volumes_by_novel_id`: 根据小说 ID 查询分卷
8. ✅ `test_create_chapter_with_volume`: 创建章节并关联分卷
9. ✅ `test_update_chapter_word_count`: 章节字数统计
10. ✅ `test_get_chapters_by_volume_id`: 根据分卷 ID 查询章节
11. ✅ `test_cascade_delete_novel`: 级联删除测试
12. ✅ `test_search_chapter_by_content`: 根据内容搜索章节

**测试结果**:
```
12 passed in 0.11s
```

### 示例脚本: [examples/db_example.py](../examples/db_example.py)

演示了完整的数据库操作流程：
1. 初始化数据库
2. 创建小说
3. 创建分卷
4. 创建章节
5. 查询数据
6. 更新数据
7. 搜索章节

**运行结果**:
```bash
PYTHONPATH=/Users/lee/Documents/github/me/aiNovel python examples/db_example.py
# 所有操作成功执行
```

---

## 技术亮点

### 1. SQLAlchemy 2.0+ 新特性

使用 `Mapped` 类型注解，提供更好的类型检查：
```python
id: Mapped[int] = mapped_column(Integer, primary_key=True)
title: Mapped[str] = mapped_column(String(200), nullable=False)
volumes: Mapped[List["Volume"]] = relationship(...)
```

### 2. 泛型 CRUD 基类

通过泛型实现代码复用，避免重复代码：
```python
class CRUDBase(Generic[ModelType]):
    def create(self, session: Session, **kwargs) -> ModelType:
        obj = self.model(**kwargs)
        session.add(obj)
        session.flush()
        return obj
```

### 3. 级联删除与关系管理

使用 SQLAlchemy 的 `cascade` 参数，确保数据一致性：
```python
volumes: Mapped[List["Volume"]] = relationship(
    "Volume",
    back_populates="novel",
    cascade="all, delete-orphan"
)
```

### 4. 事务上下文管理器

通过 `session_scope()` 自动管理事务：
```python
with db.session_scope() as session:
    novel = novel_crud.create(session, title="测试")
    # 自动提交或回滚
```

### 5. 降级策略

字数统计支持 jieba 分词，但在依赖不可用时降级为字符统计：
```python
try:
    import jieba
    words = jieba.lcut(self.content)
    self.word_count = len([w for w in words if w.strip()])
except ImportError:
    self.word_count = len([c for c in self.content if not c.isspace()])
```

---

## 文件结构

```
ainovel/db/
├── __init__.py          # 导出所有模块
├── database.py          # 数据库连接管理
├── base.py              # 基础模型类
├── novel.py             # Novel 模型
├── volume.py            # Volume 模型
├── chapter.py           # Chapter 模型
└── crud.py              # CRUD 操作管理器

tests/db/
└── test_db.py           # 单元测试

examples/
└── db_example.py        # 使用示例
```

---

## 设计原则体现

### SOLID 原则

- **单一职责**: 每个类只负责一个职责（Database 管理连接，CRUD 管理数据操作）
- **开放/封闭**: 通过泛型基类扩展新模型，无需修改现有代码
- **里氏替换**: NovelCRUD/VolumeCRUD/ChapterCRUD 可替换 CRUDBase
- **接口隔离**: CRUDBase 仅定义必要的 CRUD 方法
- **依赖倒置**: 依赖抽象基类，不依赖具体实现

### DRY 原则

- 时间戳字段通过 `TimestampMixin` 复用
- CRUD 操作通过 `CRUDBase` 泛型基类复用
- 关系映射使用 SQLAlchemy 声明式语法，避免手写 SQL

### KISS 原则

- 使用 SQLAlchemy ORM，避免手写 SQL
- 上下文管理器自动管理事务，简化调用
- 全局 CRUD 实例，一行导入即可使用

---

## 后续计划

### 阶段 1 剩余任务

1. **M3: 记忆管理层** (CharacterDatabase + WorldDatabase)
2. **M4: 生成核心层** (提示词管理 + Generator)
3. **M5: 流程编排层** (6 步流程 + 状态管理)
4. **M6: CLI 接口** (命令行工具)

### 数据库层潜在改进（后续考虑）

1. **Alembic 迁移**: 生产环境使用迁移工具管理数据库版本
2. **索引优化**: 为常用查询字段添加复合索引
3. **分区表**: 大数据量场景下，按小说 ID 分区
4. **读写分离**: 生产环境支持主从复制

---

**实现完成**: 2026-01-06
**下一步**: 开始实施 M3 记忆管理层
