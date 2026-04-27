# TinyGrad Manager

macOS 原生菜单栏应用，采用 **Apple Liquid Glass** 设计语言。用于管理 [TinyGrad](https://github.com/tinygrad/tinygrad) 深度学习框架的模型加载、GPU 服务控制，以及提供 OpenAI 兼容的 HTTP API。

## 截图预览

应用以菜单栏图标形态常驻，点击图标弹出控制窗口（840×700）。窗口采用毛玻璃材质卡片式布局，支持深色/浅色模式自动适配。

## 功能特性

### 模型管理
- 图形界面浏览和选择本地模型文件
- 支持格式：`.safetensors`、`.pth` / `.pt`、`.gguf`、`.mlx`、`.json`
- 加载后自动解析权重结构，传递给 API 转换器

### GPU 监控
- 启动时自动检测系统 GPU 型号（`system_profiler`）
- Metal 加速可用性检查
- eGPU 外置显卡检测

### 后台服务
- **GPU Service**：通过 `launchctl` 管理 TinyGrad 运行时守护进程
- **API Service**：一键启动 FastAPI + uvicorn，将本地模型暴露为 HTTP API

### OpenAI 兼容 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/models` | GET | 列出已加载的模型 |
| `/v1/chat/completions` | POST | 聊天补全（支持 `stream: true`） |

默认监听 `http://localhost:1234`，可直接替换 OpenAI SDK 的 `base_url` 使用。

### 菜单栏驻留
- 关闭窗口 → 最小化到 macOS 菜单栏，**不退出应用**
- **不显示 Dock 图标**（`LSUIElement` / `NSApplicationActivationPolicyAccessory`）
- 菜单栏下拉菜单：Show/Hide 窗口 / Quit 退出

## 界面设计

基于 **macOS 26 Liquid Glass** 设计规范：

- 全窗口 `NSVisualEffectView` 磨砂玻璃背景（`underWindowBackground` 材质）
- 三张玻璃质感卡片：Model File、System Status、Console
- 卡片圆角 14pt，半透明边框，`contentBackground` 材质
- **SF Symbols** 图标体系（`shippingbox.fill`、`cpu.fill`、`doc.fill`、`terminal.fill`）
- 系统字体 SF Pro，多级字重（Bold 26pt / Medium 13pt / Regular 11-12pt）
- 按钮使用系统强调色，圆角 pill 样式
- 透明标题栏 + 全尺寸内容视图

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS 12.0+（Monterey 及以上） |
| Python | 3.10+ |
| 架构 | Apple Silicon（M 系列）/ Intel Mac |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python TinyGradManager/main.py
```

应用启动后出现在**菜单栏**（非 Dock），点击菜单栏图标打开控制窗口。

## 使用指南

### 加载模型

1. 点击 **Browse...** 选择本地模型文件
2. 点击 **Load Model** 加载权重
3. 状态日志显示在 Console 卡片中

### 启动 API 服务

1. 确保模型已加载
2. 点击 **Start API Service**
3. 使用 OpenAI SDK 调用：

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

## 支持的模型格式

| 格式 | 扩展名 | 依赖 | 说明 |
|------|--------|------|------|
| SafeTensors | `.safetensors` | tinygrad | Hugging Face 广泛使用的安全权重格式 |
| PyTorch | `.pth` / `.pt` | tinygrad | PyTorch 原生格式 |
| GGUF | `.gguf` | `pip install gguf` | llama.cpp 量化格式，适合 CPU/Metal 推理 |
| MLX | `.mlx` | `pip install mlx` | Apple MLX 框架，针对 M 系列芯片优化 |
| JSON Config | `.json` | — | 模型配置文件 |

## 环境检测

启动时自动输出诊断报告：

- TinyGrad 版本及默认设备
- Metal 图形加速可用性
- CUDA 编译器检测
- Python 运行时版本
- 可用计算后端列表

## 项目结构

```
tinygrad-manager/
├── TinyGradManager/
│   ├── __init__.py           # 包标记
│   ├── main.py               # 主入口：Liquid Glass GUI + 菜单栏
│   ├── api_converter.py      # FastAPI 服务器（OpenAI 兼容端点）
│   ├── env_checker.py        # 环境诊断
│   ├── gpu_manager.py        # GPU / eGPU 检测
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
| GUI 框架 | AppKit (pyobjc) — NSVisualEffectView + SF Symbols |
| 深度学习 | [tinygrad](https://github.com/tinygrad/tinygrad) |
| API 服务 | FastAPI + uvicorn + pydantic |
| 后台服务 | macOS launchctl (LaunchAgent plist) |
| 打包 | py2app → .app → DMG |

## License

MIT
