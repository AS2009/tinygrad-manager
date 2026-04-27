import json
import base64
import io
import threading
import time
import asyncio
from typing import Optional, List, Dict, Any

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse, JSONResponse
    from pydantic import BaseModel, Field
    _HAS_API_DEPS = True
except ImportError:
    _HAS_API_DEPS = False
    # Stub classes for when deps are missing
    class BaseModel:
        pass
    class Field:
        def __init__(self, *args, **kwargs):
            pass

class ApiConverter:
    class Message(BaseModel):
        role: str
        content: str

    class ChatCompletionRequest(BaseModel):
        model: str
        messages: List[Dict[str, str]]
        temperature: Optional[float] = 0.7
        max_tokens: Optional[int] = None
        stream: Optional[bool] = False

    class ModelInfo(BaseModel):
        id: str
        object: str = "model"
        created: int = Field(default_factory=lambda: int(time.time()))
        owned_by: str = "tinygrad"

    class ImageGenerationRequest(BaseModel):
        model: Optional[str] = None
        prompt: str
        negative_prompt: Optional[str] = ""
        n: Optional[int] = 1
        size: Optional[str] = "512x512"
        response_format: Optional[str] = "url"
        num_inference_steps: Optional[int] = 25
        guidance_scale: Optional[float] = 7.5
        seed: Optional[int] = None

    def __init__(self):
        self.model = None           # 存储模型对象（可以是state_dict或完整模型）
        self.model_name = None
        self.model_format = None    # 格式标识：safetensors / pytorch / gguf / mlx / json
        self.model_keys_count = 0   # 权重的 key 数量
        self.server_thread = None
        self.server_port = 1234
        self._uvicorn_server = None  # 保存 uvicorn Server 引用以便优雅关闭
        self._lock = threading.Lock()  # 防止重复启动/停止竞态
        self.image_generator = None  # 文生图生成器引用
        if _HAS_API_DEPS:
            self.app = FastAPI(title="TinyGrad to LMStudio API Converter")
            self.setup_routes()

    def set_model(self, model, model_name: str):
        """设置用于推理的模型，同时记录模型元信息。"""
        self.model = model
        self.model_name = model_name
        if isinstance(model, dict):
            if "format" in model:
                self.model_format = model["format"]
                self.model_keys_count = model.get("tensor_count",
                                         len(model.get("weights", model.get("reader", {}))))
            else:
                self.model_format = "state_dict"
                self.model_keys_count = len(model)
        elif hasattr(model, 'keys'):
            self.model_format = "state_dict"
            try:
                self.model_keys_count = len(model.keys())
            except Exception:
                self.model_keys_count = 0
        else:
            self.model_format = "unknown"
        print(f"Model '{model_name}' ({self.model_format}, {self.model_keys_count} keys) set for API.")

    def set_image_generator(self, image_generator):
        """设置文生图生成器实例，用于 /v1/images/generations 端点。"""
        self.image_generator = image_generator

    def is_ready(self):
        return self.model is not None

    def setup_routes(self):
        @self.app.get("/v1/models")
        async def list_models():
            if not self.model or not self.model_name:
                return {"object": "list", "data": []}
            model_info = self.ModelInfo(id=self.model_name)
            return {
                "object": "list",
                "data": [model_info.model_dump() if hasattr(model_info, 'model_dump') else model_info.dict()]
            }

        @self.app.post("/v1/chat/completions")
        async def create_chat_completion(request: ApiConverter.ChatCompletionRequest):
            if not self.model:
                raise HTTPException(status_code=503, detail="No model loaded")
            if request.stream:
                return StreamingResponse(
                    self._stream_response(request.messages, request.temperature, request.max_tokens),
                    media_type="text/event-stream"
                )
            else:
                return self._generate_response(request.messages, request.temperature, request.max_tokens)

        @self.app.post("/v1/images/generations")
        async def create_image_generation(request: ApiConverter.ImageGenerationRequest):
            if self.image_generator is None or not self.image_generator.is_ready():
                raise HTTPException(status_code=503, detail="No image model loaded. Load a Stable Diffusion model first.")

            # Parse size string "WxH" or "W*H"
            size = request.size.replace("*", "x")
            try:
                parts = size.split("x")
                width = int(parts[0])
                height = int(parts[1])
            except (ValueError, IndexError):
                width, height = 512, 512

            image, meta = self.image_generator.generate(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt or "",
                width=width,
                height=height,
                num_inference_steps=request.num_inference_steps or 25,
                guidance_scale=request.guidance_scale or 7.5,
                seed=request.seed,
            )

            if image is None:
                raise HTTPException(status_code=500, detail=meta.get("error", "Image generation failed"))

            created = int(time.time())
            data = []

            n = max(1, min(request.n or 1, 4))  # OpenAI-compatible: 1–4
            for _ in range(n):
                if request.response_format == "b64_json":
                    buf = io.BytesIO()
                    image.save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    data.append({"b64_json": b64})
                else:
                    data.append({"url": f"file://{meta['filepath']}"})

            return JSONResponse({
                "created": created,
                "data": data,
                "meta": {
                    "elapsed_seconds": meta.get("elapsed_seconds"),
                    "width": meta.get("width"),
                    "height": meta.get("height"),
                    "steps": meta.get("steps"),
                }
            })

    def _generate_response(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int]) -> Dict[str, Any]:
        prompt = self._format_prompt(messages)
        last_msg = messages[-1]["content"] if messages else ""

        response = (
            f"[TinyGrad Manager] Model '{self.model_name}' is loaded "
            f"({self.model_format}, {self.model_keys_count} keys). "
            f"Received: \"{last_msg[:80]}{'...' if len(last_msg) > 80 else ''}\". "
            f"Real inference requires a model forward pass — this is a placeholder. "
            f"Replace _generate_response() with your model's generate() call."
        )

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.model_name,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response.split()),
                "total_tokens": len(prompt.split()) + len(response.split())
            }
        }

    async def _stream_response(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int]):
        prompt = self._format_prompt(messages)
        info = (
            f"[TinyGrad Manager] Model '{self.model_name}' "
            f"({self.model_format}, {self.model_keys_count} keys) is loaded. "
            f"Your message: "
        )
        tokens = [info] + prompt.split()
        limit = max_tokens if max_tokens else min(len(tokens), 50)
        chat_id = f"chatcmpl-{int(time.time())}"
        created = int(time.time())
        for i, word in enumerate(tokens[:limit]):
            chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": self.model_name,
                "choices": [{"delta": {"content": word + " "}, "index": 0, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.05)
        yield "data: [DONE]\n\n"

    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        return "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])

    def start_service(self, port: int = 1234) -> bool:
        if not _HAS_API_DEPS:
            print("API dependencies not installed. Run: pip install fastapi uvicorn pydantic")
            return False
        with self._lock:
            if self.server_thread and self.server_thread.is_alive():
                print("Service is already running.")
                return True
            self.server_port = port
            self._uvicorn_server = None
            def run():
                config = uvicorn.Config(self.app, host="0.0.0.0", port=port, log_level="info")
                server = uvicorn.Server(config)
                self._uvicorn_server = server
                server.run()
            self.server_thread = threading.Thread(target=run, daemon=True)
            self.server_thread.start()
            print(f"TinyGrad API service started on http://localhost:{port}")
            return True

    def stop_service(self) -> bool:
        if not _HAS_API_DEPS:
            return False
        with self._lock:
            print("Stopping API service...")
            if self._uvicorn_server is not None:
                self._uvicorn_server.should_exit = True
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5.0)
            self.server_thread = None
            self._uvicorn_server = None
            return True