import os
import time
import threading
from typing import Optional, Dict, Any, Tuple


class ImageGenerator:
    """Text-to-image generation using diffusers Stable Diffusion pipeline."""

    def __init__(self):
        self.pipeline = None
        self.model_id = None
        self.device = None
        self._lock = threading.Lock()
        self._output_dir = os.path.expanduser("~/TinyGradManager/output")

    def load_model(self, model_id: str, device: str = "cpu") -> Tuple[bool, str]:
        """Load a Stable Diffusion pipeline onto the specified device.

        Args:
            model_id: HuggingFace model ID or local path (e.g. 'runwayml/stable-diffusion-v1-5')
            device: Device string ('cuda:0', 'cuda:1', 'mps', 'cpu')

        Returns:
            (success, message) tuple
        """
        with self._lock:
            try:
                import torch
                from diffusers import StableDiffusionPipeline

                self.append_log_fn(f"[IMG] Loading Stable Diffusion pipeline: {model_id}")

                dtype = torch.float32
                if device.startswith("cuda"):
                    dtype = torch.float16

                pipe = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    safety_checker=None,
                    requires_safety_checker=False,
                )

                if device.startswith("cuda") and torch.cuda.is_available():
                    pipe = pipe.to(device)
                    self.append_log_fn(f"[IMG] Pipeline moved to {device}")
                    # Enable memory-efficient attention if available
                    try:
                        pipe.enable_attention_slicing()
                        self.append_log_fn("[IMG] Attention slicing enabled for memory efficiency")
                    except Exception:
                        pass
                elif device == "mps" and torch.backends.mps.is_available():
                    pipe = pipe.to("mps")
                    self.append_log_fn("[IMG] Pipeline moved to MPS (Apple Silicon)")
                else:
                    pipe = pipe.to("cpu")
                    self.append_log_fn("[IMG] Pipeline moved to CPU (this will be slow)")

                self.pipeline = pipe
                self.model_id = model_id
                self.device = device

                os.makedirs(self._output_dir, exist_ok=True)

                return True, f"Model '{model_id}' loaded on {device}"

            except ImportError as e:
                return False, f"Missing dependency: {e}. Install with: pip install diffusers transformers accelerate torch"
            except Exception as e:
                import traceback
                detail = traceback.format_exc()
                return False, f"Failed to load model: {e}\n{detail}"

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 25,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
        """Generate an image from a text prompt.

        Returns:
            (PIL Image or None, metadata dict)
        """
        with self._lock:
            if self.pipeline is None:
                return None, {"error": "No image model loaded. Load a model first."}

            try:
                import torch

                generator = None
                if seed is not None:
                    generator = torch.Generator(device=self.device if self.device else "cpu")
                    generator = generator.manual_seed(seed)

                self.append_log_fn(f"[IMG] Generating: '{prompt[:80]}{'...' if len(prompt) > 80 else ''}'")

                t0 = time.time()
                result = self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt if negative_prompt else None,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                )
                elapsed = time.time() - t0

                image = result.images[0]

                # Save to output directory
                timestamp = int(time.time())
                safe_prompt = "".join(c if c.isalnum() or c in " _-" else "_" for c in prompt[:30])
                filename = f"sd_{safe_prompt}_{timestamp}.png"
                filepath = os.path.join(self._output_dir, filename)
                image.save(filepath)

                meta = {
                    "success": True,
                    "filepath": filepath,
                    "filename": filename,
                    "elapsed_seconds": round(elapsed, 1),
                    "width": width,
                    "height": height,
                    "steps": num_inference_steps,
                    "seed": seed,
                }

                self.append_log_fn(f"[IMG] Done in {elapsed:.1f}s → {filepath}")
                return image, meta

            except Exception as e:
                import traceback
                detail = traceback.format_exc()
                self.append_log_fn(f"[IMG ERROR] {e}")
                return None, {"error": str(e), "traceback": detail}

    def is_ready(self) -> bool:
        return self.pipeline is not None

    def get_info(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "device": self.device,
            "ready": self.is_ready(),
        }

    def set_log_callback(self, fn):
        """Set a callback for log messages (e.g., the UI console)."""
        self.append_log_fn = fn

    def append_log_fn(self, message: str):
        """Default no-op log — replaced by set_log_callback."""
        print(message)

    def unload_model(self):
        """Release the pipeline from memory."""
        with self._lock:
            if self.pipeline is not None:
                self.append_log_fn(f"[IMG] Unloading model '{self.model_id}' from {self.device}")
                del self.pipeline
                self.pipeline = None
                self.model_id = None
                self.device = None
                # Suggest CUDA cache cleanup
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
