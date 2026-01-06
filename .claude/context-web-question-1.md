# 深挖疑问1：FastAPI 如何管理 SQLAlchemy Session

## 疑问描述
FastAPI 应用中如何正确管理 SQLAlchemy 2.0 的 Session？需要依赖注入的最佳实践。

## 查找过程
1. 使用 Context7 查询 FastAPI 官方文档
2. 查找 FastAPI + SQLAlchemy 集成示例
3. 分析现有 Database 类的设计

## 发现的证据

### 现有 Database 类（from ainovel/db/database.py）
项目已经实现了 Database 类，提供了：
- `get_session()`: Session 工厂方法
- `session_scope()`: 事务上下文管理器

### FastAPI 最佳实践
FastAPI 推荐使用依赖注入（Dependency Injection）管理 Session：

```python
# 依赖函数
def get_db():
    db = Database("sqlite:///data/ainovel.db")
    with db.session_scope() as session:
        yield session

# 路由中使用
@app.post("/novels/")
def create_novel(novel_data: NovelCreate, session: Session = Depends(get_db)):
    # 使用 session
    novel = novel_crud.create(session, novel_data)
    return novel
```

## 结论与建议

### 设计方案
1. **全局 Database 实例**: 在应用启动时初始化
2. **依赖函数 `get_db()`**: 使用 `yield` 提供 Session
3. **自动事务管理**: 利用 `session_scope()` 自动提交/回滚

### 实现步骤
1. 在 `ainovel/web/` 下创建 `dependencies.py`
2. 实现 `get_db()` 依赖函数
3. 在所有路由中使用 `Depends(get_db)`

### 风险点
- ❓ 并发请求时的 Session 隔离（FastAPI 每个请求独立调用 get_db，问题已解决）
- ✅ 事务自动提交（session_scope 已处理）
