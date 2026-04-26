# TinyGrad Manager 🚀

macOS 桌面应用程序，用于管理 [TinyGrad](https://github.com/tinygrad/tinygrad) 模型的加载、GPU 服务控制以及 OpenAI 兼容 API 的转换服务。(注：此项目完全由 DeepSeek 完成)

## 功能特性

### 📦 模型加载与管理
- 支持 `.safetensors`、`.pth`、`.pt`、`.gguf`、`.mlx`、`.json` 等多种模型文件格式
- 通过图形界面浏览并选择本地模型文件
- 自动检测并显示模型权重信息

### 💻 GPU 监控
- 自动检测并显示系统 GPU 信息
- Metal 加速支持（macOS）
- eGPU 外置显卡检测与配置

### 🌐 OpenAI 兼容 API 服务
- 将本地 TinyGrad 模型转换为 OpenAI 兼容的 API 接口
- 支持流式（Streaming）和非流式响应
- 兼容 LMStudio、OpenAI SDK 等工具
- 默认端口：`1234`

### ⚙️ GPU 服务控制
- 一键启动/停止 TinyGrad 运行时服务
- 通过 `launchctl` 管理后台服务
- 环境检测与诊断报告

## 系统要求

- **操作系统**：macOS 10.13+
- **Python**：3.10 或 3.11
- **依赖**：详见 [requirements.txt](requirements.txt)

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/tinygrad-manager.git
cd tinygrad-manager
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用程序

```bash
python TinyGradManager/main.py
```

## 使用指南

### 加载模型
1. 点击 **"Browse..."** 选择模型文件（支持 `.safetensors`、`.pth`、`.pt`、`.gguf`、`.mlx`、`.json`）
2. 点击 **"Load Model"** 加载模型
3. 加载成功后，模型会传递给 API 转换器

### 支持的模型格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| SafeTensors | `.safetensors` | 安全、快速的权重序列化格式，广泛用于 Hugging Face 模型 |
| PyTorch | `.pth` / `.pt` | PyTorch 原生模型权重格式 |
| GGUF | `.gguf` | llama.cpp 项目使用的量化模型格式，适合在 CPU/Metal 上高效推理 |
| MLX | `.mlx` / `.safetensors` | Apple MLX 框架模型格式，针对 Apple Silicon 优化 |
| JSON | `.json` | 模型配置文件 |

#### GGUF 格式说明
GGUF（GGML Universal Format）是 llama.cpp 生态系统广泛使用的模型格式，支持模型量化以降低内存占用。加载 GGUF 模型需要安装 `gguf` Python 包：
```bash
pip install gguf
```

#### MLX 格式说明
MLX 是 Apple 专为 Apple Silicon（M 系列芯片）设计的机器学习框架。MLX 模型通常以 `.safetensors` 权重文件或 `.mlx` 文件形式存在。加载 MLX 模型需要安装 `mlx` Python 包：
```bash
pip install mlx
```

### 启动 GPU 服务
- 点击 **"Start GPU Service"** 初始化 TinyGrad 运行时
- 服务启动后按钮变为 **"Stop GPU Service"**

### 启动 API 服务
1. 确保模型已加载
2. 点击 **"Start API Service"**
3. API 服务将在 `http://localhost:1234` 启动
4. 支持 OpenAI 兼容的端点：
   - `GET /v1/models` — 列出可用模型
   - `POST /v1/chat/completions` — 聊天补全（支持 `stream` 模式）

### 使用 OpenAI SDK 调用

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"  # TinyGrad API 不需要密钥
)

response = client.chat.completions.create(
    model="your-model-name",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

## 项目结构

```
tinygrad-manager/
├── TinyGradManager/
│   ├── __init__.py          # 包初始化
│   ├── main.py              # 主入口 - macOS 原生 GUI 应用
│   ├── api_converter.py     # OpenAI 兼容 API 转换器
│   ├── env_checker.py       # 环境检测工具
│   ├── gpu_manager.py       # GPU 信息管理
│   └── service_controller.py # launchctl 服务控制
├── .github/workflows/
│   └── main.yml             # CI/CD - macOS .app 构建与 DMG 打包
├── requirements.txt         # Python 依赖
├── setup.py                 # py2app 打包配置
└── README.md                # 本文件
```

## 打包为 macOS 应用程序

项目支持通过 GitHub Actions 自动构建或本地手动构建：

### 本地构建

```bash
pip install py2app
python setup.py py2app
```

构建完成后，应用程序位于 `dist/TinyGradManager.app`，可直接运行。

### 自动构建

推送至 `main` 分支后，GitHub Actions 会自动构建并生成 `.dmg` 安装包。

## 环境检测

应用启动时会自动检测并显示：

| 项目 | 说明 |
|------|------|
| TinyGrad | 是否安装及其版本 |
| Metal | macOS 图形加速 |
| CUDA | NVIDIA GPU 支持 |
| eGPU | 外置显卡状态 |
| Python | 运行时版本 |

## 依赖项

- **[tinygrad](https://github.com/tinygrad/tinygrad)** — 深度学习框架
- **pyobjc / pyobjc-framework-Cocoa** — macOS 原生 GUI
- **FastAPI + uvicorn** — API 服务
- **pydantic** — 数据验证

## License

MIT