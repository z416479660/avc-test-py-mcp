"""
Pytest 测试文件 - 使用 mock 测试，不需要真实 API

使用方法:
    1. 确保已开发安装: pip install -e ".[dev]"
    2. 运行测试: pytest tests/ -v
    3. 查看覆盖率: pytest tests/ -v --cov=http_mcp_client
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from http_mcp_client import __version__
from http_mcp_client.server import VideoEnhancementMCPServer


# ============================================================================
#  Fixtures（测试夹具，用于复用测试对象）
# ============================================================================

@pytest.fixture
def server():
    """创建一个测试用的服务器实例"""
    return VideoEnhancementMCPServer(
        base_url="http://localhost:8000",
        api_key="test_api_key"
    )


@pytest.fixture
def temp_video_file(tmp_path):
    """创建一个临时视频文件用于测试"""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video content")
    return video_file


# ============================================================================
#  基础测试
# ============================================================================

class TestBasic:
    """基础功能测试"""

    def test_version(self):
        """测试版本号正确"""
        assert __version__ == "0.1.4"

    def test_server_init(self, server):
        """测试服务器初始化"""
        assert server.base_url == "http://localhost:8000"
        assert server.api_key == "test_api_key"
        assert server._client is not None


# ============================================================================
#  工具列表测试
# ============================================================================

class TestListTools:
    """测试工具列表功能"""

    @pytest.mark.asyncio
    async def test_list_tools_returns_list(self, server):
        """测试返回工具列表"""
        tools = await server.list_tools()
        assert isinstance(tools, list)
        assert len(tools) == 3

    @pytest.mark.asyncio
    async def test_list_tools_has_correct_names(self, server):
        """测试工具名称正确"""
        tools = await server.list_tools()
        tool_names = [t.name for t in tools]

        assert "create_task" in tool_names
        assert "get_task_status" in tool_names
        assert "enhance_video_sync" in tool_names


# ============================================================================
#  文件操作测试
# ============================================================================

class TestFileOperations:
    """测试文件操作功能"""

    def test_check_local_file_success(self, server, temp_video_file):
        """测试成功检查本地文件"""
        file_path, file_name = server._check_local_file(str(temp_video_file))

        assert file_name == "test_video.mp4"
        assert Path(file_path).exists()

    def test_check_local_file_not_found(self, server):
        """测试文件不存在时抛出错误"""
        with pytest.raises(FileNotFoundError) as exc_info:
            server._check_local_file("/nonexistent/path/video.mp4")

        assert "文件不存在" in str(exc_info.value)


# ============================================================================
#  HTTP API 测试（使用 Mock）
# ============================================================================

class TestHttpApi:
    """测试 HTTP API 调用（使用 mock）"""

    @pytest.mark.asyncio
    async def test_get_tos_signature(self, server):
        """测试获取 TOS 签名"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "url": "https://bucket.tos-cn-beijing.volces.com/uid/Video/1745203200_test.mp4",
                "policy": "fake_policy",
                "signature": "fake_signature",
            }
        }
        mock_response.raise_for_status = MagicMock()
        server._client.post = AsyncMock(return_value=mock_response)

        result = await server._get_tos_signature("test.mp4")

        assert result["url"].endswith("1745203200_test.mp4")
        assert result["policy"] == "fake_policy"

    @pytest.mark.asyncio
    async def test_upload_to_tos(self, server, temp_video_file):
        """测试上传文件到 TOS"""
        signature_data = {
            "url": "https://bucket.tos-cn-beijing.volces.com/uid/Video/1745203200_test.mp4",
            "policy": "fake_policy",
            "signature": "fake_signature",
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 204
            await server._upload_to_tos(str(temp_video_file), signature_data.copy())
            mock_post.assert_awaited_once()

    def test_parse_file_id(self, server):
        """测试从 URL 解析 file_id"""
        url = "https://bucket.tos-cn-beijing.volces.com/uid/Video/1745203200_test.mp4"
        file_id = server._parse_file_id(url)
        assert file_id == "1745203200_test.mp4"

    @pytest.mark.asyncio
    async def test_create_task_with_local(self, server, temp_video_file):
        """测试使用本地文件创建任务（TOS 直传）"""
        # Mock 获取签名
        sig_response = MagicMock()
        sig_response.json.return_value = {
            "code": 0,
            "data": {
                "url": "https://bucket.tos-cn-beijing.volces.com/uid/Video/1745203200_test_video.mp4",
                "policy": "fake_policy",
                "signature": "fake_signature",
            }
        }
        sig_response.raise_for_status = MagicMock()

        # Mock 创建任务响应
        task_response = MagicMock()
        task_response.json.return_value = {
            "code": 0,
            "data": {
                "task_id": "task-456",
                "status": "pending"
            }
        }
        task_response.raise_for_status = MagicMock()

        server._client.post = AsyncMock(side_effect=[sig_response, task_response])

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_tos_post:
            mock_tos_post.return_value.status_code = 204
            result = await server._create_task(
                video_source=str(temp_video_file),
                source_type="local",
                resolution="720p"
            )

        assert result["success"] is True
        assert result["task_id"] == "task-456"

        # 验证创建任务时使用了 file_id 而不是 file_data
        call_args = server._client.post.call_args_list
        _, kwargs = call_args[-1]
        content = kwargs["json"]["content"][0]
        assert content["type"] == "video_file"
        assert "file_id" in content
        assert content["file_id"] == "1745203200_test_video.mp4"
        assert "file_data" not in content

    @pytest.mark.asyncio
    async def test_create_task_with_url(self, server):
        """测试使用 URL 创建任务"""
        # Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "task_id": "task-123",
                "status": "pending"
            }
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient.post
        server._client.post = AsyncMock(return_value=mock_response)

        result = await server._create_task(
            video_source="http://example.com/video.mp4",
            source_type="url",
            resolution="720p"
        )

        assert result["success"] is True
        assert result["task_id"] == "task-123"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_task_api_error(self, server):
        """测试 API 返回错误"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 400,
            "message": "Invalid video URL"
        }
        mock_response.raise_for_status = MagicMock()

        server._client.post = AsyncMock(return_value=mock_response)

        result = await server._create_task(
            video_source="invalid-url",
            source_type="url",
            resolution="720p"
        )

        assert result["success"] is False
        assert "Invalid video URL" in result["error"]

    @pytest.mark.asyncio
    async def test_get_task_status_success(self, server):
        """测试获取任务状态成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "task_id": "task-123",
                "status": "completed",
                "progress": 100,
                "video_url": "http://example.com/enhanced.mp4",
            }
        }
        mock_response.raise_for_status = MagicMock()

        server._client.get = AsyncMock(return_value=mock_response)

        result = await server._get_task_status("task-123")

        assert result["success"] is True
        assert result["task_id"] == "task-123"
        assert result["status"] == "completed"
        assert result["progress"] == 100


# ============================================================================
#  文件操作边界测试
# ============================================================================

class TestFileOperationsEdgeCases:
    """测试文件操作边界情况"""

    def test_check_local_file_too_large(self, server, tmp_path):
        """测试文件超过 100MB 限制时抛出错误"""
        large_file = tmp_path / "large_video.mp4"
        # 创建一个超过 100MB 的文件（用稀疏文件或 seek 模拟）
        large_file.write_bytes(b"")
        with large_file.open("wb") as f:
            f.seek(100 * 1024 * 1024 + 1)
            f.write(b"\x00")

        with pytest.raises(ValueError) as exc_info:
            server._check_local_file(str(large_file))

        assert "超过 100MB 限制" in str(exc_info.value)


# ============================================================================
#  HTTP API 错误处理测试
# ============================================================================

class TestHttpApiErrors:
    """测试 HTTP API 错误场景"""

    @pytest.mark.asyncio
    async def test_get_tos_signature_api_error(self, server):
        """测试获取 TOS 签名时 API 返回错误码"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 500,
            "message": "内部服务器错误"
        }
        mock_response.raise_for_status = MagicMock()
        server._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(RuntimeError) as exc_info:
            await server._get_tos_signature("test.mp4")

        assert "获取 TOS 签名失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_to_tos_failure(self, server, temp_video_file):
        """测试上传文件到 TOS 失败"""
        signature_data = {
            "url": "https://bucket.tos-cn-beijing.volces.com/uid/Video/1745203200_test.mp4",
            "policy": "fake_policy",
            "signature": "fake_signature",
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 403
            with pytest.raises(RuntimeError) as exc_info:
                await server._upload_to_tos(str(temp_video_file), signature_data.copy())
            assert "TOS 上传失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_task_status_api_error(self, server):
        """测试获取任务状态时 API 返回错误"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 404,
            "message": "任务不存在"
        }
        mock_response.raise_for_status = MagicMock()
        server._client.get = AsyncMock(return_value=mock_response)

        result = await server._get_task_status("task-not-exist")

        assert result["success"] is False
        assert "任务不存在" in result["error"]


# ============================================================================
#  同步增强视频测试
# ============================================================================

class TestEnhanceVideoSync:
    """测试同步增强视频功能"""

    @pytest.mark.asyncio
    async def test_enhance_video_sync_completed(self, server):
        """测试同步增强视频成功完成"""
        server._create_task = AsyncMock(return_value={
            "success": True,
            "task_id": "task-sync-1"
        })

        server._get_task_status = AsyncMock(side_effect=[
            {"success": True, "status": "processing", "task_id": "task-sync-1"},
            {"success": True, "status": "completed", "task_id": "task-sync-1", "video_url": "http://example.com/result.mp4"},
        ])

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await server._enhance_video_sync(
                video_source="http://example.com/video.mp4",
                source_type="url",
                resolution="720p",
                poll_interval=1,
                timeout=30
            )

        assert result["status"] == "completed"
        assert result["task_id"] == "task-sync-1"
        assert result["video_url"] == "http://example.com/result.mp4"

    @pytest.mark.asyncio
    async def test_enhance_video_sync_failed(self, server):
        """测试同步增强视频任务失败"""
        server._create_task = AsyncMock(return_value={
            "success": True,
            "task_id": "task-sync-2"
        })

        server._get_task_status = AsyncMock(return_value={
            "success": True,
            "status": "failed",
            "task_id": "task-sync-2"
        })

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await server._enhance_video_sync(
                video_source="http://example.com/video.mp4",
                source_type="url",
                resolution="720p",
                poll_interval=1,
                timeout=30
            )

        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_enhance_video_sync_create_failed(self, server):
        """测试同步增强视频创建任务失败"""
        server._create_task = AsyncMock(return_value={
            "success": False,
            "error": "创建任务失败"
        })

        result = await server._enhance_video_sync(
            video_source="http://example.com/video.mp4",
            source_type="url",
            resolution="720p",
            poll_interval=1,
            timeout=30
        )

        assert result["success"] is False
        assert "创建任务失败" in result["error"]

    @pytest.mark.asyncio
    async def test_enhance_video_sync_status_query_failed(self, server):
        """测试同步增强视频查询状态失败"""
        server._create_task = AsyncMock(return_value={
            "success": True,
            "task_id": "task-sync-3"
        })

        server._get_task_status = AsyncMock(return_value={
            "success": False,
            "error": "查询失败"
        })

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await server._enhance_video_sync(
                video_source="http://example.com/video.mp4",
                source_type="url",
                resolution="720p",
                poll_interval=1,
                timeout=30
            )

        assert result["success"] is False
        assert "查询失败" in result["error"]

    @pytest.mark.asyncio
    async def test_enhance_video_sync_timeout(self, server):
        """测试同步增强视频超时"""
        server._create_task = AsyncMock(return_value={
            "success": True,
            "task_id": "task-sync-4"
        })

        # 始终返回 processing，模拟任务一直不完成
        server._get_task_status = AsyncMock(return_value={
            "success": True,
            "status": "processing",
            "task_id": "task-sync-4"
        })

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_time = MagicMock()
                mock_time.side_effect = [0, 0, 100]  # start, first poll, timeout
                mock_loop.return_value.time = mock_time
                result = await server._enhance_video_sync(
                    video_source="http://example.com/video.mp4",
                    source_type="url",
                    resolution="720p",
                    poll_interval=1,
                    timeout=30
                )

        assert result["success"] is False
        assert "任务超时" in result["error"]
        assert result["task_id"] == "task-sync-4"


# ============================================================================
#  工具调用测试（补充）
# ============================================================================

class TestCallTool:
    """测试工具调用接口"""

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server):
        """测试调用未知工具"""
        result = await server.call_tool("unknown_tool", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert "未知工具" in data["error"]

    @pytest.mark.asyncio
    async def test_call_create_tool(self, server):
        """测试调用 create_task 工具"""
        # Mock 内部方法
        server._create_task = AsyncMock(return_value={
            "success": True,
            "task_id": "task-789"
        })

        result = await server.call_tool("create_task", {
            "video_source": "http://example.com/video.mp4",
            "type": "url",
            "resolution": "720p"
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["task_id"] == "task-789"

    @pytest.mark.asyncio
    async def test_call_get_task_status_tool(self, server):
        """测试调用 get_task_status 工具"""
        server._get_task_status = AsyncMock(return_value={
            "success": True,
            "task_id": "task-999",
            "status": "completed"
        })

        result = await server.call_tool("get_task_status", {
            "task_id": "task-999"
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_call_enhance_video_sync_tool(self, server):
        """测试调用 enhance_video_sync 工具"""
        server._enhance_video_sync = AsyncMock(return_value={
            "success": True,
            "task_id": "task-sync-5",
            "status": "completed"
        })

        result = await server.call_tool("enhance_video_sync", {
            "video_source": "http://example.com/video.mp4",
            "type": "url",
            "resolution": "1080p"
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["task_id"] == "task-sync-5"

    @pytest.mark.asyncio
    async def test_call_tool_exception_handling(self, server):
        """测试 call_tool 异常处理"""
        server._create_task = AsyncMock(side_effect=RuntimeError("模拟异常"))

        result = await server.call_tool("create_task", {
            "video_source": "http://example.com/video.mp4"
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert "模拟异常" in data["error"]


# ============================================================================
#  工具列表结构验证
# ============================================================================

class TestToolSchema:
    """测试 Tool 结构定义"""

    @pytest.mark.asyncio
    async def test_create_task_schema(self, server):
        """测试 create_task 工具的 inputSchema 结构"""
        tools = await server.list_tools()
        create_task = next(t for t in tools if t.name == "create_task")

        schema = create_task.inputSchema
        assert schema["type"] == "object"
        assert "video_source" in schema["properties"]
        assert "type" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert schema["required"] == ["video_source"]

        type_enum = schema["properties"]["type"]["enum"]
        assert "url" in type_enum
        assert "local" in type_enum

    @pytest.mark.asyncio
    async def test_enhance_video_sync_schema(self, server):
        """测试 enhance_video_sync 工具的 inputSchema 结构"""
        tools = await server.list_tools()
        enhance = next(t for t in tools if t.name == "enhance_video_sync")

        schema = enhance.inputSchema
        props = schema["properties"]
        assert "video_source" in props
        assert "type" in props
        assert "resolution" in props
        assert "poll_interval" in props
        assert "timeout" in props
        assert props["poll_interval"]["default"] == 5
        assert props["timeout"]["default"] == 600


# ============================================================================
#  生命周期测试
# ============================================================================

class TestLifecycle:
    """测试服务器生命周期"""

    @pytest.mark.asyncio
    async def test_close_client(self, server):
        """测试关闭 HTTP 客户端"""
        server._client.aclose = AsyncMock()
        await server.close()
        server._client.aclose.assert_awaited_once()
