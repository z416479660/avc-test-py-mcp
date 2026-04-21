#!/usr/bin/env python
"""
HTTP MCP Server - 提供视频增强功能的 MCP 服务

通过 MCP 协议暴露 tools，内部调用 FastAPI HTTP Server。
支持 URL 上传和本地文件上传（base64）。
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


class VideoEnhancementMCPServer:
    """MCP Server for video enhancement"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.server = Server("video-enhancement")

        # 注册 tools
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)

        # HTTP 客户端
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def list_tools(self) -> list[Tool]:
        """列出所有可用的 tools"""
        return [
            Tool(
                name="create_task",
                description="""创建视频增强任务（异步）

支持两种上传方式：
1. URL 上传：提供视频 URL
2. 本地上传：提供本地文件路径，MCP Server 自动上传到 TOS 对象存储

参数说明：
- video_source: 视频 URL 或本地文件路径
- type: "url" 或 "local"
- resolution: 目标分辨率
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "video_source": {
                            "type": "string",
                            "description": "视频URL地址或本地文件路径",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["url", "local"],
                            "default": "url",
                            "description": "上传类型：url=网络视频，local=本地文件",
                        },
                        "resolution": {
                            "type": "string",
                            "enum": ["480p", "540p", "720p", "1080p", "2k"],
                            "default": "720p",
                            "description": "目标分辨率，默认720p",
                        },
                    },
                    "required": ["video_source"],
                },
            ),
            Tool(
                name="get_task_status",
                description="查询视频增强任务状态",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                    },
                    "required": ["task_id"],
                },
            ),
            Tool(
                name="enhance_video_sync",
                description="""同步增强视频（阻塞等待完成）

支持两种上传方式：
1. URL 上传：提供视频 URL
2. 本地上传：提供本地文件路径，MCP Server 自动上传到 TOS 对象存储

参数说明：
- video_source: 视频 URL 或本地文件路径
- type: "url" 或 "local"
- resolution: 目标分辨率
- poll_interval: 轮询间隔（秒）
- timeout: 超时时间（秒）
""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "video_source": {
                            "type": "string",
                            "description": "视频URL地址或本地文件路径",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["url", "local"],
                            "default": "url",
                            "description": "上传类型：url=网络视频，local=本地文件",
                        },
                        "resolution": {
                            "type": "string",
                            "enum": ["480p", "540p", "720p", "1080p", "2k"],
                            "default": "720p",
                            "description": "目标分辨率，默认720p",
                        },
                        "poll_interval": {
                            "type": "number",
                            "default": 5,
                            "description": "轮询间隔（秒），默认5",
                        },
                        "timeout": {
                            "type": "number",
                            "default": 600,
                            "description": "超时时间（秒），默认600",
                        },
                    },
                    "required": ["video_source"],
                },
            ),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """调用 tool"""
        try:
            if name == "create_task":
                result = await self._create_task(
                    video_source=arguments["video_source"],
                    source_type=arguments.get("type", "url"),
                    resolution=arguments.get("resolution", "720p"),
                )
            elif name == "get_task_status":
                result = await self._get_task_status(
                    task_id=arguments["task_id"],
                )
            elif name == "enhance_video_sync":
                result = await self._enhance_video_sync(
                    video_source=arguments["video_source"],
                    source_type=arguments.get("type", "url"),
                    resolution=arguments.get("resolution", "720p"),
                    poll_interval=arguments.get("poll_interval", 5),
                    timeout=arguments.get("timeout", 600),
                )
            else:
                result = {"success": False, "error": f"未知工具: {name}"}

            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        except Exception as e:
            return [
                TextContent(
                    type="text", text=json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2)
                )
            ]

    def _check_local_file(self, file_path: str) -> tuple[str, str]:
        """
        检查本地文件是否存在并符合大小限制

        Args:
            file_path: 本地文件路径

        Returns:
            (file_path, file_name)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查文件大小（最大 100MB）
        max_size = 100 * 1024 * 1024
        file_size = path.stat().st_size
        if file_size > max_size:
            raise ValueError("文件大小超过 100MB 限制")

        return str(path), path.name

    async def _get_tos_signature(self, file_name: str) -> dict:
        """获取 TOS 预签名上传凭证"""
        response = await self._client.post(
            "/api/v3/contents/generations/tos-signature",
            json={"file_type": "video", "file_name": file_name},
        )
        response.raise_for_status()

        data = response.json()
        code = data.get("code", 0)
        if code != 0 and code != 200:
            raise RuntimeError(data.get("message", "获取 TOS 签名失败"))

        return data["data"]

    async def _upload_to_tos(self, file_path: str, signature_data: dict) -> None:
        """上传文件到 TOS（不携带 Bearer Token）"""
        import httpx as httpx_module
        from urllib.parse import urlparse

        url = signature_data.pop("url")

        # TOS 要求必须有 key 字段（对象键）
        object_key = urlparse(url).path.lstrip("/")

        # 后端返回的字段名去掉了 x-tos- 前缀，但 TOS policy 里用的是带前缀的，需要映射回来
        field_mapping = {
            "algorithm": "x-tos-algorithm",
            "credential": "x-tos-credential",
            "date": "x-tos-date",
            "signature": "x-tos-signature",
        }

        form_data = {"key": object_key}
        for key, value in signature_data.items():
            if key == "origin_policy":
                continue
            form_key = field_mapping.get(key, key)
            form_data[form_key] = value

        async with httpx_module.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = await client.post(url, data=form_data, files=files)

        if response.status_code not in (200, 204):
            raise RuntimeError(f"TOS 上传失败: {response.status_code}")

    @staticmethod
    def _parse_file_id(url: str) -> str:
        """从预签名 URL 中解析 file_id"""
        from urllib.parse import urlparse

        path = urlparse(url).path
        return path.split("/")[-1]

    async def _create_task(self, video_source: str, source_type: str, resolution: str) -> dict:
        """创建任务"""
        # 根据类型构建请求
        if source_type == "local":
            # 本地上传：检查文件、获取 TOS 签名、直传文件
            file_path, file_name = self._check_local_file(video_source)
            signature_data = await self._get_tos_signature(file_name)
            await self._upload_to_tos(file_path, signature_data.copy())
            file_id = self._parse_file_id(signature_data["url"])
            content_item = {
                "type": "video_file",
                "file_id": file_id,
                "file_name": file_name,
            }
        else:
            # URL 上传
            content_item = {
                "type": "video_url",
                "video_url": {"url": video_source},
            }

        payload = {
            "model": "avc-enhance",
            "content": [content_item],
            "resolution": resolution,
        }

        response = await self._client.post(
            "/api/v3/contents/generations/tasks",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        code = data.get("code", 0)
        if code != 0 and code != 200:
            return {"success": False, "error": data.get("message", "Unknown error")}

        return {
            "success": True,
            "task_id": data["data"]["task_id"],
            "status": data["data"]["status"],
        }

    async def _get_task_status(self, task_id: str) -> dict:
        """查询任务状态"""
        response = await self._client.get(
            f"/api/v3/contents/generations/tasks/{task_id}",
        )
        response.raise_for_status()

        data = response.json()
        code = data.get("code", 0)
        if code != 0 and code != 200:
            return {"success": False, "error": data.get("message", "Unknown error")}

        result = data["data"]
        return {
            "success": True,
            "task_id": result["task_id"],
            "status": result["status"],
            "progress": result.get("progress", 0),
            "video_url": result.get("video_url"),
            "error_message": result.get("error_message"),
            "created_at": result.get("created_at"),
            "updated_at": result.get("updated_at"),
        }

    async def _enhance_video_sync(
        self,
        video_source: str,
        source_type: str,
        resolution: str,
        poll_interval: int,
        timeout: int,
    ) -> dict:
        """同步增强视频"""
        # 创建任务
        create_result = await self._create_task(video_source, source_type, resolution)
        if not create_result["success"]:
            return create_result

        task_id = create_result["task_id"]

        # 轮询等待完成
        start_time = asyncio.get_event_loop().time()
        while True:
            status = await self._get_task_status(task_id)
            if not status["success"]:
                return status

            if status["status"] in ("completed", "failed"):
                return status

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                return {
                    "success": False,
                    "error": f"任务超时: {task_id}",
                    "task_id": task_id,
                }

            await asyncio.sleep(poll_interval)

    async def run(self):
        """运行 MCP Server (stdio mode)"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def close(self):
        """关闭客户端"""
        await self._client.aclose()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="HTTP MCP Server for video enhancement")
    parser.add_argument(
        "--base-url",
        default=os.getenv("HTTP_API_BASE_URL", "https://mcp.luluhero.com/"),
        help="FastAPI HTTP Server base URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("HTTP_API_KEY", ""),
        help="API key for authentication",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("错误: 需要提供 --api-key 或设置 HTTP_API_KEY 环境变量", flush=True)
        exit(1)

    server = VideoEnhancementMCPServer(
        base_url=args.base_url,
        api_key=args.api_key,
    )

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n服务已停止", flush=True)
    finally:
        asyncio.run(server.close())


if __name__ == "__main__":
    main()
