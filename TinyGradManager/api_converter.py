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
        self.model = None           # 存储模型对象（可以是state_dict或完整模型）
        self.model_name = None
        self.server_thread = None
        self.server_port = 1234
        self._uvicorn_server = None  # 保存 uvicorn Server 引用以便优雅关闭
        self.setup_routes()

    def set_model(self, model, model_name: str):
        """设置用于推理的模型"""
        self.model = model
        self.model_name = model_name
        print(f"Model '{model_name}' set for API.")

    def is_ready(self):
        return self.model is not None

    def setup_routes(self):
        @self.app.get("/v1/models")
        async def list_models():
            if not self.model or not self.model_name:
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

    def _generate_response(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int]) -> Dict[str, Any]:
        prompt = self._format_prompt(messages)
        # 此处应调用实际模型的推理逻辑
        # 由于不同模型推理接口差异，这里提供一个模拟响应，提醒用户自行实现
        # temperature 参数被用于影响响应的随机性（模拟实现中体现在响应文本里）
        response = f"[TinyGrad] Received: {prompt[:100]}... (temp={temperature})"
        # 实际使用时替换为：
        # tokens = tokenizer.encode(prompt)
        # output = model.generate(tokens, temperature, max_tokens)
        # response = tokenizer.decode(output)

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
            "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": len(response.split()), "total_tokens": len(prompt.split())+len(response.split())}
        }

    async def _stream_response(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int]):
        prompt = self._format_prompt(messages)
        words = prompt.split()
        # 修复：当 max_tokens 为 None 时取 20，为 0 时也应取 20
        limit = max_tokens if max_tokens is not None else 20
        for i, word in enumerate(words[:limit]):
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
        self._uvicorn_server = None
        def run():
            config = uvicorn.Config(self.app, host="0.0.0.0", port=port, log_level="info")
            server = uvicorn.Server(config)
            self._uvicorn_server = server  # 保存引用以便后续停止
            server.run()
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        print(f"🚀 TinyGrad API service started on http://localhost:{port}")

    def stop_service(self):
        print("🛑 Stopping API service...")
        # 通过设置 uvicorn server 的 should_exit 标志来优雅停止
        if self._uvicorn_server is not None:
            self._uvicorn_server.should_exit = True
        # 等待线程结束（最多等待5秒）
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)
        self.server_thread = None
        self._uvicorn_server = None