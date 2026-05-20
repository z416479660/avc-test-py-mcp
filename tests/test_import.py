"""测试包导入和基本信息."""

import http_mcp_client


def test_package_import():
    """测试包能正常导入."""
    assert hasattr(http_mcp_client, "__version__")
    assert http_mcp_client.__version__ == "0.1.4"


def test_server_import():
    """测试 server 模块能正常导入."""
    from http_mcp_client.server import VideoEnhancementMCPServer, main

    assert VideoEnhancementMCPServer is not None
    assert main is not None
