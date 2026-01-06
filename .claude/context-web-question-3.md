# 深挖疑问3：数据库 Session 管理策略

## 疑问描述
FastAPI 中 SQLAlchemy 2.0 Session 的具体管理策略，确保线程安全和事务正确性。

## 查找过程
1. 查询 Context7 FastAPI 官方文档
2. 分析现有 Database 类的实现
3. 确认最佳实践

## 发现的证据

### FastAPI 官方推荐（from Context7）
```python
def get_session():
    with Session(engine) as session:
        yield session

# 使用 Annotated 简化类型注解
SessionDep = Annotated[Session, Depends(get_session)]

@app.post("/items/")
def create_item(session: SessionDep):
    # FastAPI 自动注入 session
    pass
```

### 现有 Database 类（ainovel/db/database.py）
```python
class Database:
    def session_scope(self):
        """事务上下文管理器"""
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
```

## 设计方案

### 全局 Database 实例管理
```python
# ainovel/web/dependencies.py
from typing import Annotated, Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from ainovel.db.database import Database

# 全局单例（应用启动时初始化）
_db_instance: Database | None = None

def get_database() -> Database:
    """获取全局 Database 实例"""
    global _db_instance
    if _db_instance is None:
        from ainovel.web.config import settings
        _db_instance = Database(settings.DATABASE_URL)
    return _db_instance

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入：提供数据库 Session

    使用 yield 确保请求结束后自动关闭 Session
    """
    db = get_database()
    with db.session_scope() as session:
        yield session

# 类型别名（简化路由签名）
SessionDep = Annotated[Session, Depends(get_db)]
```

### 路由中使用
```python
@app.post("/novels/", response_model=NovelResponse)
def create_novel(
    novel_data: NovelCreate,
    session: SessionDep,  # 自动注入
):
    novel = novel_crud.create(session, novel_data)
    return novel
```

## 关键优势
1. **自动事务管理**: `session_scope()` 自动 commit/rollback
2. **线程安全**: 每个请求独立 Session
3. **资源自动释放**: `yield` 确保 finally 块执行
4. **类型提示完善**: `SessionDep` 提供 IDE 支持

## 结论
使用 FastAPI Depends + Database.session_scope() 的组合方案，无需修改现有代码。
