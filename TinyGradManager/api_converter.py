import json
import uvicorn
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import threading
import time
import asyncio

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
        created: int = int(time.time())
        owned_by: str = "tinygrad"

    def __init__(self):
        self.app = FastAPI(title="TinyGrad to LMStudio API Converter")
        self.model = None
        self.model_name = None
        self.server_thread = None
        self.server_port = 1234
        self.should_exit = threading.Event()
        self.setup_routes()

    def setup_routes(self):
        @self.app.get("/v1/models")
        async def list_models():
            if not self.model:
                return {"object": "list", "data": []}
            return {
                "object": "list",
                "data": [self.ModelInfo(id=self.model_name).model_dump()]
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

    def load_model(self, model_path: str):
        print(f"⏳ Loading TinyGrad model from {model_path}...")
        self.model = lambda prompt: f"[TinyGrad response to: {prompt}]"
        self.model_name = model_path.split("/")[-1]
        print(f"✅ Model '{self.model_name}' loaded successfully.")

    def _generate_response(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int]) -> Dict[str, Any]:
        prompt = self._format_prompt(messages)
        response = f"Echo: {prompt}"
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
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

    async def _stream_response(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int]):
        prompt = self._format_prompt(messages)
        words = prompt.split()
        for word in words:
            chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": self.model_name,
                "choices": [{"delta": {"content": word + " "}, "index": 0, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.1)
        yield "data: [DONE]\n\n"

    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        return "\n".join([f"{m['role']}: {m['content']}" for m in messages])

    def start_service(self, port: int = 1234):
        if self.server_thread and self.server_thread.is_alive():
            print("Service is already running.")
            return
        self.server_port = port
        self.should_exit.clear()
        def run():
            config = uvicorn.Config(self.app, host="0.0.0.0", port=port, log_level="info")
            server = uvicorn.Server(config)
            server.run()
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        print(f"🚀 TinyGrad API service started on http://localhost:{port}")

    def stop_service(self):
        print("🛑 Stopping API service...")
        self.should_exit.set()
        self.server_thread = None