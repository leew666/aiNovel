# 深挖疑问2：是否需要流式输出

## 疑问描述
Web 界面是否需要支持流式输出（实时显示生成进度）？影响接口设计。

## 查找过程
1. 检查 BaseLLMClient 是否支持流式输出
2. 分析用户体验需求（章节生成耗时）
3. 评估实现复杂度

## 发现的证据

### BaseLLMClient 接口分析（from base.py:34-67）
当前接口：
```python
def generate(self, messages, temperature, max_tokens, **kwargs) -> Dict[str, Any]:
    # 返回完整结果（非流式）
    return {
        "content": str,
        "usage": {...},
        "cost": float,
        "model": str,
    }
```

**结论**: 当前 BaseLLMClient 仅支持同步调用，不支持流式输出。

### 用户体验需求分析
- **Step 1-2（思路/世界观）**: 生成时间短（<10s），不需要流式
- **Step 3（大纲）**: 中等耗时（10-30s），建议显示"生成中..."
- **Step 4（细纲）**: 批量生成时耗时长（>1min），建议显示进度条
- **Step 5（章节内容）**: 单章节耗时长（30-60s），**强烈建议流式输出**

### 技术方案对比

#### 方案A：不支持流式（当前可行）
- 优势：实现简单，复用现有接口
- 劣势：用户体验差（长时间等待）
- 解决方案：显示"生成中..."提示 + HTMX 轮询状态

#### 方案B：支持流式（阶段2）
- 优势：用户体验好，实时反馈
- 劣势：需要修改 BaseLLMClient，增加 WebSocket 支持
- 实现：FastAPI SSE（Server-Sent Events）或 WebSocket

## 结论与建议

### 当前阶段（阶段1 Web界面）
**不实现流式输出**，理由：
1. BaseLLMClient 不支持，修改会影响已有代码
2. 可以用"加载中"动画 + HTMX 替代
3. 符合渐进式开发原则

### 实现方案
1. 前端：显示加载动画（CSS spinner）
2. 后端：使用 HTMX `hx-post` + `hx-indicator`
3. 可选：长任务使用后台任务（FastAPI BackgroundTasks）

### 预留扩展
- 在路由设计中预留 `/stream/` 接口
- 文档注释标注"阶段2支持流式"

### 风险点
- ⚠️ 用户可能在长时间等待时关闭页面（解决：加后台任务 + 轮询）
