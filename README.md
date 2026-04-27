# TinyGrad Manager

macOS 原生菜单栏应用，采用 **Apple Liquid Glass** 设计语言。用于管理 [TinyGrad](https://github.com/tinygrad/tinygrad) 深度学习框架的模型加载、文生图生成、GPU 服务控制，以及提供 OpenAI 兼容的 HTTP API（支持 LLM 对话和图像生成）。

## 截图预览

应用以菜单栏图标形态常驻，点击图标弹出控制窗口（840×920）。窗口采用毛玻璃材质卡片式布局，支持深色/浅色模式自动适配。

## 功能特性

### 模型管理
- 图形界面浏览和选择本地模型文件
- 支持格式：`.safetensors`、`.pth` / `.pt`、`.gguf`、`.mlx`、`.json`
- 加载后自动解析权重结构，传递给 API 转换器
- **自定义 GPU 分配**：可为 LLM 和文生图模型分别指定运行 GPU

### 文生图（Text-to-Image）
- 基于 Stable Diffusion（`diffusers` 库）的图像生成
- 支持 HuggingFace 模型 ID 或本地路径（默认 `runwayml/stable-diffusion-v1-5`）
- 可自定义 Prompt、图像尺寸、推理步数、CFG Scale、随机种子
- 生成图片自动保存至 `~/TinyGradManager/output/`
- **LLM 与文生图模型可同时加载**，各自运行在独立 GPU 上

### GPU 监控与分配
- 启动时自动检测系统 GPU 型号（`system_profiler` + `torch.cuda`）
- Metal 加速（Apple Silicon）/ CUDA（NVIDIA）/ CPU 回退
- eGPU 外置显卡检测
- 每个模型独立的 GPU 设备下拉菜单

### 后台服务
- **GPU Service**：通过 `launchctl` 管理 TinyGrad 运行时守护进程
- **API Service**：一键启动 FastAPI + uvicorn，将本地模型暴露为 HTTP API

### OpenAI 兼容 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/models` | GET | 列出已加载的模型 |
| `/v1/chat/completions` | POST | 聊天补全（支持 `stream: true`） |
| `/v1/images/generations` | POST | 文生图（兼容 DALL·E API 格式） |

默认监听 `http://localhost:1234`，可直接替换 OpenAI SDK 的 `base_url` 使用。

### 菜单栏驻留
- 关闭窗口 → 最小化到 macOS 菜单栏，**不退出应用**
- **不显示 Dock 图标**（`LSUIElement` / `NSApplicationActivationPolicyAccessory`）
- 菜单栏下拉菜单：Show/Hide 窗口 / Quit 退出

## 界面设计

基于 **macOS 26 Liquid Glass** 设计规范：

- 全窗口 `NSVisualEffectView` 磨砂玻璃背景（`underWindowBackground` 材质）
- 四张玻璃质感卡片：Model File、Text-to-Image、System Status、Console
- 卡片圆角 14pt，半透明边框，`contentBackground` / `HUD` 材质
- **SF Symbols** 图标体系（`shippingbox.fill`、`photo.fill`、`cpu.fill`、`terminal.fill`）
- 系统字体 SF Pro，多级字重（Bold 26pt / Medium 13pt / Regular 11-12pt）
- 按钮使用系统强调色，圆角 pill 样式
- `NSPopUpButton` 下拉菜单用于 GPU 选择
- 透明标题栏 + 全尺寸内容视图

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS 12.0+（Monterey 及以上） |
| Python | 3.10+ |
| 架构 | Apple Silicon（M 系列）/ Intel Mac |
| 文生图 | 需安装 diffusers / torch（见下方） |

## 快速开始

```bash
# 安装全部依赖（含文生图）
pip install -r requirements.txt

# 仅运行基础功能（无需文生图依赖）
pip install tinygrad pyobjc pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

运行应用：

```bash
python TinyGradManager/main.py
```

应用启动后出现在**菜单栏**（非 Dock），点击菜单栏图标打开控制窗口。

## 使用指南

### 加载 LLM 模型

1. 在 **Model File** 卡片中选择 GPU 设备（下拉菜单）
2. 点击 **Browse...** 选择本地模型文件
3. 点击 **Load Model** 加载权重
4. 状态日志显示在 Console 卡片中

### 文生图

1. 在 **Text-to-Image** 卡片中选择 GPU 设备（可与 LLM 不同）
2. 输入模型 ID（如 `runwayml/stable-diffusion-v1-5`）
3. 点击 **Load Image Model**（首次运行将从 HuggingFace 下载模型，约 5 GB）
4. 输入 Prompt，点击 **Generate Image**
5. 图片保存至 `~/TinyGradManager/output/`，Console 显示路径和耗时

**注意**：LLM 和文生图模型可同时驻留在不同 GPU 上。例如 LLM 跑在 `mps`，SD 跑在 `cuda:0`。

### 启动 API 服务

1. 确保至少一个模型已加载（LLM 或文生图均可）
2. 点击 **Start API Service**
3. 调用方式：

**LLM 对话：**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="your-model-name",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

**文生图：**
```python
import requests

resp = requests.post("http://localhost:1234/v1/images/generations", json={
    "prompt": "a cat sitting on a cloud, digital art",
    "size": "512x512",
    "num_inference_steps": 25,
    "response_format": "url"
})

print(resp.json())
# {"created": ..., "data": [{"url": "file:///Users/.../output/sd_...png"}], "meta": {...}}
```

## 支持的模型格式

| 格式 | 扩展名 | 依赖 | 说明 |
|------|--------|------|------|
| SafeTensors | `.safetensors` | tinygrad | Hugging Face 广泛使用的安全权重格式 |
| PyTorch | `.pth` / `.pt` | tinygrad | PyTorch 原生格式 |
| GGUF | `.gguf` | `pip install gguf` | llama.cpp 量化格式，适合 CPU/Metal 推理 |
| MLX | `.mlx` | `pip install mlx` | Apple MLX 框架，针对 M 系列芯片优化 |
| JSON Config | `.json` | — | 模型配置文件 |
| Stable Diffusion | HuggingFace ID | `pip install diffusers torch` | 文生图模型（SD 1.5 / 2.1 / XL 等） |

## 环境检测

启动时自动输出诊断报告：

- TinyGrad 版本及默认设备
- Metal 图形加速可用性
- CUDA 编译器检测
- diffusers / torch 文生图依赖检测
- 可用 GPU 设备列表（CUDA / MPS / CPU）
- Python 运行时版本

## 项目结构

```
tinygrad-manager/
├── TinyGradManager/
│   ├── __init__.py           # 包标记
│   ├── main.py               # 主入口：Liquid Glass GUI + 菜单栏
│   ├── api_converter.py      # FastAPI 服务器（OpenAI 兼容端点）
│   ├── env_checker.py        # 环境诊断 + GPU 设备枚举
│   ├── gpu_manager.py        # GPU / eGPU 检测
│   ├── image_generator.py    # 文生图模块（Stable Diffusion via diffusers）
│   └── service_controller.py # launchctl 守护进程管理
├── .github/workflows/
│   └── main.yml              # CI：py2app 构建 → 签名 → DMG 打包
├── requirements.txt
├── setup.py                  # py2app 配置
└── README.md
```

## 打包为 .app

### 本地构建

```bash
pip install py2app
python setup.py py2app
```

构建产物位于 `dist/TinyGradManager.app`。

### CI 自动构建

推送至 `main` 分支后，GitHub Actions 自动构建并上传 `.dmg` 安装包。构建流程：
1. macOS runner 安装依赖
2. py2app 打包为 `.app` bundle
3. ad-hoc 代码签名
4. hdiutil 创建 `.dmg` 磁盘镜像

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI 框架 | AppKit (pyobjc) — NSVisualEffectView + SF Symbols + NSPopUpButton |
| LLM 推理 | [tinygrad](https://github.com/tinygrad/tinygrad) |
| 文生图 | [diffusers](https://github.com/huggingface/diffusers) (Stable Diffusion) |
| API 服务 | FastAPI + uvicorn + pydantic |
| 后台服务 | macOS launchctl (LaunchAgent plist) |
| 打包 | py2app → .app → DMG |

## License

MIT
