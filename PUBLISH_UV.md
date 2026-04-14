# 发布到 PyPI 指南（uv 方式）

本文档介绍如何使用 [uv](https://docs.astral.sh/uv/) 发布包到 PyPI。

## 前置准备

1. **安装 uv**
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **注册 PyPI 账号**
   - 访问 https://pypi.org/account/register/
   - 注册并验证邮箱
   - 开启双因素认证 (2FA)
   - 创建 API Token（在 Account Settings → API tokens）

## 发布步骤

### 1. 确保代码准备就绪

```bash
# 运行测试
uv run pytest

# 代码格式化
uv run ruff format .
uv run ruff check --fix .
```

### 2. 更新版本号

修改以下文件中的版本号：
- `pyproject.toml` - `version = "x.x.x"`
- `src/http_mcp_client/__init__.py` - `__version__ = "x.x.x"`

### 3. 构建分发包

```bash
# 清理旧的构建文件
rm -rf dist/ build/ *.egg-info

# 构建 wheel 和 sdist
uv build

# 检查构建结果
ls -la dist/
# 应该包含：
# - avc_test_py_mcp-X.X.X-py3-none-any.whl
# - avc-test-py-mcp-X.X.X.tar.gz
```

### 4. 验证包

```bash
# 使用 twine 检查
uv run twine check dist/*
```

### 5. 上传到 TestPyPI（可选但推荐）

```bash
uv run twine upload --repository testpypi dist/*

# 交互式输入：
# Username: __token__
# Password: pypi-xxxxx (你的 TestPyPI API Token)
```

测试安装：
```bash
uv pip install --index-url https://test.pypi.org/simple/ avc-test-py-mcp
```

### 6. 上传到正式 PyPI

```bash
uv run twine upload dist/*

# 交互式输入：
# Username: __token__
# Password: pypi-AgEIcHlwaS5vcmcCJD...
```

### 7. 验证发布

```bash
# 等待几分钟让 PyPI 索引更新
uv pip install avc-test-py-mcp

# 验证安装
avc-test-py-mcp --help
```

### 8. 创建 Git 标签（可选）

```bash
git tag v0.1.0
git push origin v0.1.0
```

---

## 不使用 uv 的方式（备选）

如果你没有 uv，可以使用标准工具：

```bash
# 安装依赖
pip install build twine

# 构建
python -m build

# 验证
python -m twine check dist/*

# 上传
python -m twine upload dist/*
```

## 故障排除

### 上传失败：文件已存在

PyPI 不允许重复上传相同版本。需要：
1. 更新版本号
2. 重新构建: `uv build`
3. 重新上传

### 网络超时

如果构建时出现网络问题：
```bash
python -m build --no-isolation
```

### 验证失败

```bash
uv run twine check dist/*
```

常见问题：
- README.md 格式错误
- 缺少必需的元数据
- 版本号格式不正确

## 自动化发布（GitHub Actions）

创建 `.github/workflows/publish.yml`：

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v3
    - name: Build and publish
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        uv build
        uv run twine upload dist/*
```

然后在 GitHub 仓库设置中添加 `PYPI_API_TOKEN` secret。
