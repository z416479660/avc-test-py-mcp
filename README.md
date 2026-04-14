# avc-test-py-mcp (Python)

[![PyPI version](https://badge.fury.io/py/avc-test-py-mcp.svg)](https://pypi.org/project/avc-test-py-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 MCP 协议的视频增强服务，作为 MCP Client-Server 与 FastAPI HTTP Server 交互。

## 功能

提供以下 MCP Tools：
- `create_task` - 创建视频增强任务（支持 URL 或本地文件上传）
- `get_task_status` - 查询任务状态
- `enhance_video_sync` - 同步增强视频（阻塞等待）

## 安装

### 从 PyPI 安装（推荐）

```bash
# 使用 pip 安装
pip install avc-test-py-mcp

# 或使用 uv 安装
uv pip install avc-test-py-mcp
```

### 从源码安装

```bash
git clone https://github.com/yourusername/avc-test-py-mcp.git
cd python_client

# 使用 uv 安装（推荐）
uv pip install -e ".[dev]"

# 或使用 pip 安装
pip install -e ".[dev]"
```

## 使用方法

### 1. 命令行启动

```bash
# 直接运行（安装后）
avc-test-py-mcp --base-url https://mcp.luluhero.com --api-key your-api-key

# 或使用环境变量
export HTTP_API_BASE_URL=https://mcp.luluhero.com
export HTTP_API_KEY=your-api-key
avc-test-py-mcp
```

### 2. 在 Claude Desktop 中配置

编辑 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "video-enhancement": {
      "command": "avc-test-py-mcp",
      "args": [
        "--base-url",
        "https://mcp.luluhero.com",
        "--api-key",
        "your-api-key"
      ]
    }
  }
}
```

### 3. 使用 uv run 运行（开发模式）

```bash
uv run avc-test-py-mcp --base-url https://mcp.luluhero.com --api-key your-api-key
```

## 提供的 Tools

### create_task

创建视频增强任务（异步）。

**参数：**
- `video_source` (string, required): 视频 URL 或本地文件路径
- `type` (string, optional): 上传类型，默认 "url"
  - 可选值: `"url"` - 网络视频URL, `"local"` - 本地文件路径
- `resolution` (string, optional): 目标分辨率，默认 720p
  - 可选值: 480p, 540p, 720p, 1080p, 2k

**使用示例：**

```python
# URL 方式
{
  "video_source": "https://example.com/video.mp4",
  "type": "url",
  "resolution": "1080p"
}

# 本地文件方式
{
  "video_source": "/path/to/local/video.mp4",
  "type": "local",
  "resolution": "1080p"
}
```

**返回值：**
```json
{
  "success": true,
  "task_id": "xxx",
  "status": "wait"
}
```

### get_task_status

查询任务状态。

**参数：**
- `task_id` (string, required): 任务ID

**使用示例：**
```python
{
  "task_id": "task-123-abc"
}
```

**返回值：**
```json
{
  "success": true,
  "task_id": "xxx",
  "status": "completed",
  "progress": 100,
  "video_url": "https://...",
  "error_message": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:01:00Z"
}
```

### enhance_video_sync

同步增强视频（阻塞等待完成）。

**参数：**
- `video_source` (string, required): 视频 URL 或本地文件路径
- `type` (string, optional): 上传类型，默认 "url"
  - 可选值: `"url"` - 网络视频URL, `"local"` - 本地文件路径
- `resolution` (string, optional): 目标分辨率，默认 720p
- `poll_interval` (number, optional): 轮询间隔（秒），默认 5
- `timeout` (number, optional): 超时时间（秒），默认 600

**使用示例：**
```python
{
  "video_source": "https://example.com/video.mp4",
  "type": "url",
  "resolution": "1080p",
  "poll_interval": 5,
  "timeout": 600
}
```

**返回值：**
```json
{
  "success": true,
  "task_id": "xxx",
  "status": "completed",
  "progress": 100,
  "video_url": "https://..."
}
```

## 文件上传说明

当 `type` 设置为 `"local"` 时，MCP Server 会：
1. 读取本地文件
2. 将文件转为 base64 编码
3. 上传到视频增强服务

**限制：**
- 最大文件大小：100MB

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HTTP_API_BASE_URL` | FastAPI HTTP Server 地址 | `https://mcp.luluhero.com` |
| `HTTP_API_KEY` | API 认证密钥 | 无 |

## 开发

```bash
# 克隆仓库
git clone https://github.com/yourusername/avc-test-py-mcp.git
cd python_client

# 安装开发依赖
uv pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
ruff format .
ruff check --fix .
```

## 发布到 PyPI

```bash
# 安装构建工具
uv pip install build twine

# 构建分发包
python -m build

# 上传到 PyPI（测试）
python -m twine upload --repository testpypi dist/*

# 上传到 PyPI（正式）
python -m twine upload dist/*
```

## License

MIT License - 详见 [LICENSE](LICENSE) 文件
