#!/usr/bin/env python3
"""Headless backend for TinyGrad Manager — Swift GUI companion.

Starts a FastAPI server on port 1234 with OpenAI-compatible /v1/* endpoints
and /api/* management endpoints for the native Swift frontend.

Usage:
    python backend_main.py [--port 1234]
"""

import os
import sys
import json
import time
import signal
import argparse
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gpu_manager
import service_controller
import env_checker
from api_converter import ApiConverter, _HAS_API_DEPS

if _HAS_API_DEPS:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

try:
    import image_generator as img_gen_mod
    _HAS_IMAGE_GEN = True
except ImportError:
    _HAS_IMAGE_GEN = False

# ── state ────────────────────────────────────────────────────────────────────
api_converter: Optional[ApiConverter] = None
image_gen = None
loaded_model = None
model_path: Optional[str] = None
_log_buffer: list = []
MAX_LOG = 500


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _log_buffer.append(entry)
    if len(_log_buffer) > MAX_LOG:
        del _log_buffer[: len(_log_buffer) - MAX_LOG]
    print(entry)


# ── model loading ─────────────────────────────────────────────────────────────

def _load_llm_model(file_path: str, device_key: str = "mps") -> dict:
    global loaded_model, model_path
    env_checker.set_tinygrad_device(device_key)

    from tinygrad.nn.state import safe_load, torch_load

    if file_path.endswith('.safetensors'):
        state = safe_load(file_path)
        loaded_model = state
        msg = f"SafeTensors loaded, {len(state)} keys"
    elif file_path.endswith(('.pth', '.pt')):
        state = torch_load(file_path)
        loaded_model = state
        msg = f"PyTorch loaded, {len(state)} keys"
    elif file_path.endswith('.gguf'):
        import gguf
        reader = gguf.GGUFReader(file_path)
        loaded_model = {"format": "gguf", "path": file_path, "reader": reader, "tensor_count": len(reader.tensors)}
        msg = f"GGUF loaded, {len(reader.tensors)} tensors"
    elif file_path.endswith('.mlx'):
        import mlx.core as mx
        weights = mx.load(file_path)
        loaded_model = {"format": "mlx", "path": file_path, "weights": weights, "tensor_count": len(weights)}
        msg = f"MLX loaded, {len(weights)} weights"
    elif file_path.endswith('.json'):
        with open(file_path, 'r') as f:
            loaded_model = json.load(f)
        msg = "JSON config loaded"
    else:
        return {"error": f"Unsupported format: {file_path}"}

    model_path = file_path
    api_converter.set_model(loaded_model, os.path.basename(file_path))
    _log(f"[OK] {msg}")
    return {"success": True, "model_name": os.path.basename(file_path), "detail": msg}


# ── app factory ───────────────────────────────────────────────────────────────

def create_app():
    if not _HAS_API_DEPS:
        _log("FATAL: API dependencies missing. pip install fastapi uvicorn pydantic")
        sys.exit(1)

    global api_converter, image_gen

    api_converter = ApiConverter()
    if _HAS_IMAGE_GEN:
        image_gen = img_gen_mod.ImageGenerator()
        image_gen.set_log_callback(_log)
        api_converter.set_image_generator(image_gen)

    app = api_converter.app

    # CORS for Swift GUI
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    # ── Pydantic models ────────────────────────────────────────────────────

    class LoadModelReq(BaseModel):
        file_path: str
        device: str = "mps"

    class LoadImageModelReq(BaseModel):
        model_source: str
        device: str = "mps"

    class GenImageReq(BaseModel):
        prompt: str
        negative_prompt: str = ""
        width: int = 512
        height: int = 512
        steps: int = 25
        cfg_scale: float = 7.5
        seed: Optional[int] = None

    # ── /api/status ────────────────────────────────────────────────────────
    @app.get("/api/status")
    async def get_status():
        return {
            "llm_loaded": api_converter.is_ready(),
            "llm_model": api_converter.model_name,
            "llm_format": api_converter.model_format,
            "image_model_loaded": image_gen.is_ready() if image_gen else False,
            "image_model_id": image_gen.model_id if image_gen else None,
            "image_model_device": image_gen.device if image_gen else None,
            "api_running": True,
            "has_image_gen": _HAS_IMAGE_GEN,
        }

    # ── /api/model/load ────────────────────────────────────────────────────
    @app.post("/api/model/load")
    async def load_model(req: LoadModelReq):
        if not os.path.exists(req.file_path):
            raise HTTPException(404, f"File not found: {req.file_path}")
        result = _load_llm_model(req.file_path, req.device)
        if "error" in result:
            raise HTTPException(400, result["error"])
        return result

    # ── /api/image/load ────────────────────────────────────────────────────
    @app.post("/api/image/load")
    async def load_image_model(req: LoadImageModelReq):
        if not _HAS_IMAGE_GEN or image_gen is None:
            raise HTTPException(503, "Image generation not available")
        ok, msg = image_gen.load_model(req.model_source, req.device)
        if not ok:
            raise HTTPException(500, msg)
        return {"success": True, "message": msg}

    # ── /api/image/generate ────────────────────────────────────────────────
    @app.post("/api/image/generate")
    async def generate_image(req: GenImageReq):
        if not _HAS_IMAGE_GEN or image_gen is None or not image_gen.is_ready():
            raise HTTPException(503, "No image model loaded")
        img, meta = image_gen.generate(
            prompt=req.prompt, negative_prompt=req.negative_prompt,
            width=req.width, height=req.height,
            num_inference_steps=req.steps, guidance_scale=req.cfg_scale,
            seed=req.seed,
        )
        if img is None:
            raise HTTPException(500, meta.get("error", "Generation failed"))
        return {
            "success": True,
            "filepath": meta["filepath"],
            "elapsed_seconds": meta.get("elapsed_seconds"),
            "width": meta.get("width"),
            "height": meta.get("height"),
        }

    # ── /api/gpu ───────────────────────────────────────────────────────────
    @app.get("/api/gpu")
    async def get_gpu():
        return {
            "gpu_info": gpu_manager.get_gpu_info(),
            "available_devices": env_checker.get_available_gpu_devices(),
        }

    # ── /api/env ───────────────────────────────────────────────────────────
    @app.get("/api/env")
    async def get_env():
        info = env_checker.check_environment()
        return {
            "report": env_checker.format_env_report(info),
            "details": {
                "tinygrad": info.get("tinygrad", {}),
                "metal": info.get("metal", {}).get("available", False),
                "cuda": info.get("cuda", {}).get("nvcc_available", False),
                "platform": info.get("platform", ""),
                "python_version": info.get("python_version", ""),
            },
            "diffusers": env_checker.check_diffusers() if _HAS_IMAGE_GEN else {},
        }

    # ── /api/service ───────────────────────────────────────────────────────
    @app.post("/api/service/start")
    async def start_service():
        ok = service_controller.start_service()
        return {"success": ok}

    @app.post("/api/service/stop")
    async def stop_service():
        ok = service_controller.stop_service()
        return {"success": ok}

    # ── /api/logs ──────────────────────────────────────────────────────────
    @app.get("/api/logs")
    async def get_logs(since: int = 0):
        entries = _log_buffer[since:] if since < len(_log_buffer) else []
        return {"entries": entries, "total": len(_log_buffer)}

    return app


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TinyGrad Manager Backend")
    parser.add_argument("--port", type=int, default=1234)
    args = parser.parse_args()

    _log(f"TinyGrad Manager Backend")
    _log(f"Platform: {sys.platform}, Python: {sys.version.split()[0]}")
    _log(f"Image gen: {'available' if _HAS_IMAGE_GEN else 'unavailable'}")

    app = create_app()

    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=args.port, log_level="info")
    server = uvicorn.Server(config)

    def _shutdown(sig, frame):
        _log("Shutting down...")
        server.should_exit = True
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    _log(f"Ready: http://localhost:{args.port}")
    server.run()
    _log("Stopped.")


if __name__ == "__main__":
    main()
