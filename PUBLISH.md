# 发布到 PyPI 指南

## 前置准备

1. **注册 PyPI 账号**
   - 访问 https://pypi.org/account/register/
   - 注册并验证邮箱
   - 开启双因素认证 (2FA)
   - 创建 API Token（在 Account Settings → API tokens）

2. **准备 API Token**

   在 PyPI 账号设置中创建 API Token，发布时需要用到。

   每次上传时会提示输入：
   - Username: `__token__`
   - Password: 你的 API Token (格式: `pypi-xxxxxxxxxxxx`)

## 发布步骤

### 1. 确保代码准备就绪

```bash
# 运行测试
pytest

# 代码格式化
ruff format .
ruff check --fix .

# 验证包可以正常构建
python -m build
```

### 2. 更新版本号

修改以下文件中的版本号：
- `pyproject.toml` - `version = "x.x.x"`
- `src/http_mcp_client/__init__.py` - `__version__ = "x.x.x"`

### 3. 构建分发包

**方式一：使用 uv（推荐，更快）**

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

**方式二：使用 python -m build**

PowerShell:
```powershell
# 清理旧的构建文件
Remove-Item -Recurse -Force dist/, build/ -ErrorAction SilentlyContinue
Remove-Item *.egg-info -Recurse -Force -ErrorAction SilentlyContinue

# 构建 wheel 和 sdist
python -m build

# 检查构建结果
Get-ChildItem dist/
```

CMD / macOS / Linux:
```bash
# 清理旧的构建文件
rm -rf dist/ build/ *.egg-info

# 构建 wheel 和 sdist
python -m build

# 检查构建结果
ls -la dist/
```

**网络超时解决方法：**

如果 `python -m build` 出现网络超时，使用 `--no-isolation` 选项：
```bash
python -m build --no-isolation
```

### 4. 验证包

```bash
# 使用 twine 检查（uv 方式）
uv run twine check dist/*

# 或使用已安装的 twine
python -m twine check dist/*

# 测试安装
uv pip install dist/avc_test_py_mcp-X.X.X-py3-none-any.whl
```

### 5. 上传到 TestPyPI（可选但推荐）

**使用 uv（推荐）：**
```bash
uv run twine upload --repository testpypi dist/*

# 交互式输入：
# Username: __token__
# Password: pypi-xxxxx (你的 TestPyPI API Token)
```

**使用已安装的 twine：**
```bash
python -m twine upload --repository testpypi dist/*
```

测试安装：
```bash
pip install --index-url https://test.pypi.org/simple/ avc-test-py-mcp
```

### 6. 上传到正式 PyPI

#### 方式一：使用 uv（推荐，无需单独安装 twine）

```bash
# 直接运行 twine（uv 会自动安装临时依赖）
uv run twine upload dist/*

# 然后按提示输入：
# Username: __token__
# Password: pypi-AgEIcHlwaS5vcmcCJD...
```

#### 方式二：交互式输入（使用已安装的 twine）

**PowerShell:**
```powershell
cd python_client
python -m twine upload dist/*
# 然后按提示输入：
# Username: __token__
# Password: pypi-AgEIcHlwaS5vcmcCJD...
```

**CMD:**
```cmd
cd python_client
python -m twine upload dist/*
REM 然后按提示输入用户名和密码
```

**macOS/Linux:**
```bash
cd python_client
python -m twine upload dist/*
# 然后按提示输入用户名和密码
```

#### 方式二：环境变量方式（不保存到文件）

**PowerShell:**
```powershell
# 设置环境变量（仅当前会话有效）
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-AgEIcHlwaS5vcmcCJD..."

# 执行上传（不需要输入用户名密码）
python -m twine upload dist/*

# 上传完成后清除环境变量（可选，关闭窗口自动清除）
Remove-Item Env:\TWINE_USERNAME
Remove-Item Env:\TWINE_PASSWORD
```

**CMD:**
```cmd
set TWINE_USERNAME=__token__
set TWINE_PASSWORD=pypi-xxxxx
python -m twine upload dist/*
```

**macOS/Linux:**
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxx
python -m twine upload dist/*
```

### 7. 验证发布

```bash
# 等待几分钟让 PyPI 索引更新
pip install avc-test-py-mcp

# 验证安装
avc-test-py-mcp --help
```

### 8. 创建 Git 标签（可选）

```bash
git tag v0.1.0
git push origin v0.1.0
```

## 故障排除

### 上传失败：文件已存在

PyPI 不允许重复上传相同版本。需要：
1. 更新版本号
2. 重新构建
3. 重新上传

### 构建失败

确保安装了 build 工具：
```bash
uv pip install build
```

### 验证失败

运行 `twine check` 查看具体错误：
```bash
python -m twine check dist/*
```

常见问题：
- README.md 格式错误
- 缺少必需的元数据
- 版本号格式不正确

## 自动化发布（GitHub Actions）

可以创建 `.github/workflows/publish.yml` 实现自动发布：

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
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build and publish
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        python -m build
        twine upload dist/*
```

然后在 GitHub 仓库设置中添加 `PYPI_API_TOKEN` secret。
