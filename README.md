# TinyGrad Manager

> macOS native menu-bar app with **Apple Liquid Glass** design. Manage [TinyGrad](https://github.com/tinygrad/tinygrad) models, text-to-image generation, GPU services, and expose an OpenAI-compatible HTTP API.

macOS 原生菜单栏应用，采用 **Apple Liquid Glass** 设计语言。用于管理 [TinyGrad](https://github.com/tinygrad/tinygrad) 深度学习框架的模型加载、文生图生成、GPU 服务控制，以及提供 OpenAI 兼容的 HTTP API。

---

## Features / 功能特性

### Model Management / 模型管理
- Browse and load local model files via GUI
- Supported formats: `.safetensors`, `.pth`/`.pt`, `.gguf`, `.mlx`, `.json`
- Auto-parse weight structure and wire to API converter
- **Per-model GPU assignment**: LLM and image models each get their own GPU selector

### Text-to-Image / 文生图
- Stable Diffusion via `diffusers` (HuggingFace)
- Local checkpoint files or HuggingFace model IDs
- Customizable prompt, resolution, steps, CFG scale, seed
- Output saved to `~/TinyGradManager/output/`

### GPU Monitoring & Assignment / GPU 监控与分配
- Auto-detect system GPU at startup (`system_profiler` + `torch.cuda` + `tinygrad`)
- **Metal** (Apple Silicon built-in GPU) / **CUDA** (NVIDIA) / **CPU** fallback
- eGPU detection via `SafeEjectGPU`
- Independent GPU selectors for LLM and image models

### Services / 后台服务
- **GPU Service**: launchctl-managed TinyGrad runtime daemon
- **API Service**: One-click FastAPI + uvicorn, exposing models as HTTP API

### OpenAI-Compatible API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/models` | GET | List loaded models |
| `/v1/chat/completions` | POST | Chat completions (supports `stream: true`) |
| `/v1/images/generations` | POST | Image generation (DALL·E API compatible) |

Default: `http://localhost:1234`. Drop-in replacement for OpenAI SDK `base_url`.

### Menu Bar / 菜单栏驻留
- Close window → hide to menu bar (app stays running)
- No Dock icon (`LSUIElement`)
- Menu: Show/Hide window / Quit

---

## System Requirements / 系统要求

| Item | Requirement |
|------|-------------|
| OS | macOS 12.0+ (Monterey or later) |
| Python | 3.10+ |
| Architecture | Apple Silicon (M-series) / Intel Mac |
| GPU (LLM) | Metal-capable GPU (built-in Apple Silicon GPU or AMD/NVIDIA discrete) |
| GPU (Image Gen) | Requires `diffusers` + `torch` (see below) |

> **Important:** On Apple Silicon Macs, the **built-in GPU is used via Metal (MPS)**. Make sure your Python environment has tinygrad installed — it auto-detects the built-in GPU without additional drivers.

---

## Quick Start / 快速开始

```bash
# Full install (including image generation)
pip install -r requirements.txt

# Minimal install (LLM only, no image gen deps)
pip install tinygrad pyobjc pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

Run the app:

```bash
python TinyGradManager/main.py
```

The app appears in the **menu bar** (not the Dock). Click the menu bar icon to open the control window.

---

## GPU Setup / GPU 设置

### Built-in GPU (Apple Silicon) / 内置 GPU

On Apple Silicon Macs (M1/M2/M3/M4), the built-in GPU is used through **Metal** (Apple's graphics API). TinyGrad calls this the `METAL` device, and PyTorch calls it `mps`.

The app auto-detects your built-in GPU at startup. You should see **"mps (Apple Silicon GPU)"** in the GPU dropdown menus. If not, see [Troubleshooting](#troubleshooting).

### Checking GPU Detection / 验证 GPU 检测

Run this to verify your GPU is detected:

```bash
# Check system-level Metal support
system_profiler SPDisplaysDataType | grep -E "Chipset Model|Metal"

# Check tinygrad device detection
python -c "from tinygrad import Device; print(list(Device.get_available_devices()))"

# Check torch MPS (if installed)
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

---

## Troubleshooting / 常见问题

### Built-in GPU not showing up / 内置 GPU 未显示

1. **Verify tinygrad is installed:**
   ```bash
   python -c "import tinygrad; print(tinygrad.__version__)"
   ```

2. **Check Metal availability:**
   ```bash
   system_profiler SPDisplaysDataType | grep "Metal"
   ```
   Expected output: `Metal Support: Metal 3` (or similar)

3. **Restart the app** — GPU detection runs at startup. If you installed tinygrad after launching the app, restart it.

4. **Check Console output** in the app — it logs detected GPU info at startup.

### "mps (Apple Silicon GPU)" selected but model runs on CPU

This usually means `Device.DEFAULT` wasn't set correctly before tinygrad loaded the model. The latest version sets `Device.DEFAULT = "METAL"` (tinygrad's name for the Apple GPU) before loading weights. Make sure you're using the current code.

### Image generation slow or not working

- Image generation requires `torch` with MPS support. Install: `pip install torch diffusers transformers accelerate`
- First run downloads ~5 GB from HuggingFace — this is normal
- If MPS runs out of memory, try: use CPU fallback or a smaller resolution (384×384)

### No GPU options at all / 完全没有 GPU 选项

This happens when neither CUDA, Metal, nor MPS is detected. The console will show which checks passed/failed. Common causes:
- Python environment doesn't have tinygrad installed
- Running on a VM without GPU passthrough
- macOS version too old (Metal requires 10.14+, but GPU detection is best on 12.0+)

---

## Usage Guide / 使用指南

### Load an LLM Model / 加载 LLM 模型

1. Select GPU device in the **Model File** card dropdown
2. Click **Browse...** to pick a local model file
3. Click **Load Model** to load weights
4. Status/logs appear in the Console card

### Text-to-Image / 文生图

1. Select GPU device in the **Text-to-Image** card (can differ from LLM GPU)
2. Enter a HuggingFace model ID (e.g. `runwayml/stable-diffusion-v1-5`) or browse a local file
3. Click **Load Image Model** (first run downloads ~5 GB from HuggingFace)
4. Enter a prompt and click **Generate Image**
5. Images saved to `~/TinyGradManager/output/`

### Start API Service / 启动 API 服务

1. Ensure at least one model is loaded (LLM or image)
2. Click **Start API Service**

**LLM Chat:**
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

**Image Generation:**
```python
import requests

resp = requests.post("http://localhost:1234/v1/images/generations", json={
    "prompt": "a cat sitting on a cloud, digital art",
    "size": "512x512",
    "num_inference_steps": 25,
    "response_format": "url"
})

print(resp.json())
```

---

## Supported Model Formats / 支持的模型格式

| Format | Extension | Dependency | Notes |
|--------|-----------|------------|-------|
| SafeTensors | `.safetensors` | tinygrad | Safe weight format from HuggingFace |
| PyTorch | `.pth` / `.pt` | tinygrad | Native PyTorch format |
| GGUF | `.gguf` | `pip install gguf` | llama.cpp quantized, good for CPU/Metal |
| MLX | `.mlx` | `pip install mlx` | Apple MLX, optimized for M-series |
| JSON Config | `.json` | — | Model configuration files |
| Stable Diffusion | HF ID or local | `pip install diffusers torch` | SD 1.5 / 2.1 / XL |

---

## Environment Diagnostics / 环境检测

At startup, the app outputs a diagnostic report including:
- TinyGrad version and default device
- Metal graphics acceleration availability
- CUDA compiler detection
- diffusers/torch dependency status
- Available GPU device list (CUDA / MPS / CPU)
- Python runtime version

---

## Project Structure / 项目结构

```
tinygrad-manager/
├── TinyGradManager/
│   ├── main.py               # Main entry: Liquid Glass GUI + menu bar
│   ├── backend_main.py       # Headless FastAPI backend (for Swift GUI)
│   ├── api_converter.py      # FastAPI server (OpenAI-compatible endpoints)
│   ├── env_checker.py        # Environment diagnostics + GPU device enumeration
│   ├── gpu_manager.py        # GPU / eGPU detection
│   ├── image_generator.py    # Text-to-image (Stable Diffusion via diffusers)
│   └── service_controller.py # launchctl daemon management
├── SwiftGUI/                 # Native SwiftUI rewrite (in progress)
│   ├── Sources/
│   │   ├── AppMain.swift
│   │   └── BackendClient.swift
│   └── Package.swift
├── .github/workflows/
│   └── main.yml              # CI: build → sign → DMG package
├── requirements.txt
├── setup.py                  # py2app config
└── README.md
```

---

## Building .app Bundle / 打包为 .app

### Local Build

```bash
pip install py2app
python setup.py py2app
```

Output: `dist/TinyGradManager.app`.

### CI Auto-Build

Push to `main` triggers GitHub Actions on `macos-15`:
1. Install dependencies
2. Build Swift GUI (`swift build --configuration release --arch arm64`)
3. Assemble `.app` bundle (Swift binary + Python backend + deps)
4. Ad-hoc code sign
5. Create `.dmg` with `hdiutil`

---

## Tech Stack / 技术栈

| Component | Technology |
|-----------|------------|
| GUI | AppKit (pyobjc) + SwiftUI (rewrite in progress) |
| LLM Inference | [tinygrad](https://github.com/tinygrad/tinygrad) |
| Image Generation | [diffusers](https://github.com/huggingface/diffusers) (Stable Diffusion) |
| API Server | FastAPI + uvicorn + pydantic |
| Background Service | macOS launchctl (LaunchAgent plist) |
| Packaging | py2app → .app → DMG |

---

## License

MIT
