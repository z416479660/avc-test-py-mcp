#!/usr/bin/env python
"""
手动测试脚本 - 用于快速验证功能

使用方法:
    1. 确保已开发安装: pip install -e .
    2. 设置环境变量: set HTTP_API_BASE_URL=http://localhost:8000
                     set HTTP_API_KEY=your_api_key
    3. 运行: python test_manual.py

注意: 这需要真实的 API 服务器才能测试网络请求部分
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加 src 到路径（开发模式不需要，但直接运行时可能需要）
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from http_mcp_client import __version__
from http_mcp_client.server import VideoEnhancementMCPServer


def test_version():
    """测试 1: 检查版本号"""
    print("=" * 50)
    print("测试 1: 检查版本号")
    print(f"版本号: {__version__}")
    assert __version__ == "0.1.0", f"版本号不匹配: {__version__}"
    print("✓ 版本号正确\n")


def test_import():
    """测试 2: 检查是否能正常导入"""
    print("=" * 50)
    print("测试 2: 检查导入")
    print(f"成功导入 VideoEnhancementMCPServer: {VideoEnhancementMCPServer}")
    print("✓ 导入成功\n")


def test_server_init():
    """测试 3: 检查服务器初始化"""
    print("=" * 50)
    print("测试 3: 检查服务器初始化")

    base_url = "http://localhost:8000"
    api_key = "test_api_key"

    server = VideoEnhancementMCPServer(base_url=base_url, api_key=api_key)

    print(f"Base URL: {server.base_url}")
    print(f"API Key: {'*' * len(api_key)} (已隐藏)")

    # 检查属性是否正确设置
    assert server.base_url == "http://localhost:8000"
    assert server.api_key == api_key

    print("✓ 服务器初始化成功\n")

    return server


def test_list_tools():
    """测试 4: 检查工具列表"""
    print("=" * 50)
    print("测试 4: 检查工具列表")

    server = VideoEnhancementMCPServer(
        base_url="http://localhost:8000",
        api_key="test_key"
    )

    # 运行异步函数获取工具列表
    tools = asyncio.run(server.list_tools())

    print(f"可用工具数量: {len(tools)}")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

    # 验证工具名称
    tool_names = [t.name for t in tools]
    assert "create_task" in tool_names
    assert "get_task_status" in tool_names
    assert "enhance_video_sync" in tool_names

    print("✓ 工具列表正确\n")


def test_read_local_file():
    """测试 5: 检查本地文件读取"""
    print("=" * 50)
    print("测试 5: 检查本地文件读取")

    # 创建一个临时测试文件
    test_file = Path("test_temp_video.txt")
    test_content = b"fake video content"
    test_file.write_bytes(test_content)

    try:
        server = VideoEnhancementMCPServer(
            base_url="http://localhost:8000",
            api_key="test_key"
        )

        base64_data, file_name = server._read_local_file(str(test_file))

        print(f"文件名: {file_name}")
        print(f"Base64 长度: {len(base64_data)}")
        print(f"Base64 前 20 字符: {base64_data[:20]}...")

        assert file_name == test_file.name
        assert len(base64_data) > 0

        print("✓ 文件读取正确\n")

    finally:
        # 清理临时文件
        test_file.unlink()


def test_file_not_found():
    """测试 6: 检查文件不存在时的错误处理"""
    print("=" * 50)
    print("测试 6: 检查文件不存在时的错误")

    server = VideoEnhancementMCPServer(
        base_url="http://localhost:8000",
        api_key="test_key"
    )

    try:
        server._read_local_file("/path/to/nonexistent/file.mp4")
        assert False, "应该抛出 FileNotFoundError"
    except FileNotFoundError as e:
        print(f"正确捕获错误: {e}")
        print("✓ 错误处理正确\n")


def test_env_variables():
    """测试 7: 检查环境变量读取"""
    print("=" * 50)
    print("测试 7: 检查环境变量")

    # 设置测试环境变量
    os.environ["HTTP_API_BASE_URL"] = "http://test-server.com"
    os.environ["HTTP_API_KEY"] = "test_key_from_env"

    # 重新导入以读取新环境变量
    # 注意：实际使用时通过 argparse 读取
    base_url = os.getenv("HTTP_API_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("HTTP_API_KEY", "")

    print(f"从环境变量读取的 Base URL: {base_url}")
    print(f"从环境变量读取的 API Key: {'*' * len(api_key)}")

    assert base_url == "http://test-server.com"
    assert api_key == "test_key_from_env"

    print("✓ 环境变量读取正确\n")


async def test_create_task_mock():
    """测试 8: 模拟测试创建任务（需要 mock HTTP 请求）"""
    print("=" * 50)
    print("测试 8: 模拟创建任务")
    print("注意: 这个测试需要真实的 API 服务器，或者使用 mock")
    print("跳过实际网络请求...")
    print("✓ 如需测试网络请求，请确保 API 服务器运行并提供有效 API Key\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("开始手动测试 http_mcp_client")
    print("=" * 50 + "\n")

    tests = [
        ("版本号测试", test_version),
        ("导入测试", test_import),
        ("初始化测试", test_server_init),
        ("工具列表测试", test_list_tools),
        ("文件读取测试", test_read_local_file),
        ("错误处理测试", test_file_not_found),
        ("环境变量测试", test_env_variables),
        ("创建任务测试", lambda: asyncio.run(test_create_task_mock())),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} 失败: {e}\n")
            failed += 1

    print("=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
