# 测试指南 - http_mcp_client

本文档介绍两种测试方式，你可以选择适合自己的方式。

---

## 方案对比

| 特性 | 方案一：手动测试 | 方案二：pytest |
|------|-----------------|----------------|
| 安装依赖 | `pip install -e .` | `pip install -e ".[dev]"` |
| 是否需要真实 API | 部分测试需要 | ❌ 完全不需要（用 Mock） |
| 运行速度 | 中等 | 飞快（<1秒） |
| 适合 CI/CD | ❌ 不太适合 | ✅ 非常适合 |
| 代码覆盖率 | 需要手动统计 | ✅ 自动生成报告 |
| 学习曲线 | 低 | 中等 |

---

## 准备工作（两种方案都需要）

```bash
# 进入项目目录
cd e:/mcp_test/http_mcp_client/python_client

# 开发模式安装包（-e 表示可编辑模式，修改代码后无需重装）
pip install -e .
```

---

## 方案一：手动测试

适合：快速验证、不想学习 pytest、临时调试

### 测试文件位置
`test_manual.py`（项目根目录）

### 运行方式

```bash
python test_manual.py
```

### 测试内容说明

| 测试编号 | 测试名称 | 说明 |
|---------|---------|------|
| 1 | 版本号测试 | 检查 `__version__` 是否为 `"0.1.0"` |
| 2 | 导入测试 | 检查能否正常导入包 |
| 3 | 初始化测试 | 创建服务器实例，检查属性设置 |
| 4 | 工具列表测试 | 检查是否返回 3 个工具 |
| 5 | 文件读取测试 | 创建临时文件，测试 base64 编码 |
| 6 | 错误处理测试 | 测试文件不存在时的异常 |
| 7 | 环境变量测试 | 检查能否读取环境变量 |
| 8 | 创建任务测试 | 说明：需要真实 API，默认跳过 |

### 预期输出

```
==================================================
开始手动测试 http_mcp_client
==================================================

==================================================
测试 1: 检查版本号
版本号: 0.1.0
✓ 版本号正确

==================================================
测试 2: 检查导入
成功导入 VideoEnhancementMCPServer: <class 'http_mcp_client.server.VideoEnhancementMCPServer'>
✓ 导入成功

...（省略中间输出）...

==================================================
测试结果: 7 通过, 0 失败
==================================================
```

### 如何添加新测试

在 `test_manual.py` 中添加函数：

```python
def test_your_feature():
    """测试描述"""
    print("=" * 50)
    print("测试 X: 测试描述")
    
    # 你的测试代码
    result = some_function()
    assert result == expected_value
    
    print("✓ 测试通过\n")
```

然后在 `run_all_tests()` 中添加：

```python
tests = [
    ("版本号测试", test_version),
    # ... 其他测试
    ("你的功能测试", test_your_feature),  # 添加这一行
]
```

---

## 方案二：pytest 测试（推荐）

适合：正式项目、自动化测试、团队协作

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

这会自动安装：pytest、pytest-asyncio、ruff、build、twine

### 测试文件位置
`tests/test_server.py`

### 常用命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_server.py -v

# 运行特定测试类
pytest tests/test_server.py::TestBasic -v

# 运行单个测试
pytest tests/test_server.py::TestBasic::test_version -v

# 生成覆盖率报告
pytest tests/ -v --cov=http_mcp_client --cov-report=html
```

### 测试结构说明

```
tests/
├── __init__.py              # 空文件，标记为 Python 包
└── test_server.py           # 测试代码
    ├── Fixtures (server, temp_video_file)
    ├── TestBasic            # 基础测试
    ├── TestListTools        # 工具列表测试
    ├── TestFileOperations   # 文件操作测试
    ├── TestHttpApi          # HTTP API 测试（使用 Mock）
    ├── TestCallTool         # 工具调用测试
    └── TestIntegration      # 集成测试（需要真实 API）
```

### 什么是 Mock？

Mock 是**假的对象**，用来模拟真实行为，**不需要真实的 HTTP 服务器**。

**示例**：测试 `_create_task` 时，我们不会真的发送 HTTP 请求，而是：

```python
# 创建一个假的响应
mock_response = MagicMock()
mock_response.json.return_value = {
    "code": 0,
    "data": {"task_id": "task-123", "status": "pending"}
}

# 把服务器的 post 方法替换成假的
server._client.post = AsyncMock(return_value=mock_response)

# 现在调用 _create_task 会返回假数据，不会真的发请求
result = await server._create_task(...)
```

### 如何添加新测试

**步骤 1**：在合适的 class 中添加测试方法

```python
class TestYourFeature:
    """你的功能测试"""
    
    @pytest.mark.asyncio  # 如果是异步函数
    async def test_something(self, server):
        """测试描述"""
        # 准备 mock
        server._client.post = AsyncMock(return_value=mock_response)
        
        # 执行测试
        result = await server.your_method()
        
        # 验证结果
        assert result["success"] is True
```

**步骤 2**：运行新测试

```bash
pytest tests/test_server.py::TestYourFeature::test_something -v
```

---

## 常见问题

### Q: 为什么有些测试在手动测试里跳过？

A: 测试 8（创建任务）需要真实的 API 服务器。如果你有：

```bash
# 设置环境变量
set HTTP_API_BASE_URL=http://your-api-server.com
set HTTP_API_KEY=your-api-key

# 然后运行
python test_manual.py
```

### Q: pytest 提示 "No module named 'http_mcp_client'"？

A: 确保已开发安装：

```bash
pip install -e .
```

### Q: 如何只运行不需要网络的测试？

A: pytest 的测试都使用 Mock，**全部不需要网络**。如果想排除集成测试：

```bash
pytest tests/ -v -m "not integration"
```

### Q: 测试失败了怎么办？

A: 使用 `-v` 和 `--tb=short` 查看详细错误：

```bash
pytest tests/ -v --tb=short
```

---

## 快速参考卡

### 手动测试
```bash
pip install -e .
python test_manual.py
```

### pytest 测试
```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### 查看覆盖率
```bash
pytest tests/ -v --cov=http_mcp_client
```

---

## 下一步建议

1. **新手**：先跑手动测试，理解代码结构
2. **进阶**：学习 pytest，使用 Mock 测试
3. **发布前**：确保所有 pytest 通过
4. **CI/CD**：使用 `pytest tests/ -v` 自动化测试
