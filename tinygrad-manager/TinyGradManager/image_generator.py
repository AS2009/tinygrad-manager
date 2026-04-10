import os
import time
import tempfile
from typing import Optional, Callable, Dict, Any
from threading import Thread

_loaded_model = None
_loaded_model_name = None

def get_available_sd_models():
    return [
        "Stable Diffusion v1.5",
        "Stable Diffusion v2.1",
        "Stable Diffusion XL Base",
        "SDXL Turbo",
        "SD 3 Medium"
    ]

def load_sd_model(model_name: str, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
    global _loaded_model, _loaded_model_name
    if _loaded_model_name == model_name and _loaded_model is not None:
        if progress_callback:
            progress_callback(f"Model '{model_name}' already loaded.")
        return True
    if progress_callback:
        progress_callback(f"Loading {model_name}...")
    try:
        from tinygrad.examples.stable_diffusion import StableDiffusion
        config = _get_model_config(model_name)
        _loaded_model = StableDiffusion(**config)
        _loaded_model_name = model_name
        if progress_callback:
            progress_callback(f"✅ Model '{model_name}' loaded successfully.")
        return True
    except ImportError:
        if progress_callback:
            progress_callback("❌ tinygrad stable_diffusion example not found.")
        return False
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Failed: {str(e)}")
        return False

def _get_model_config(model_name: str) -> Dict[str, Any]:
    from tinygrad import Device
    available = Device.get_available_devices()
    if "METAL" in available:
        device = "METAL"
    elif "NV" in available:
        device = "NV"
    elif "AMD" in available:
        device = "AMD"
    else:
        device = "CPU"
    config = {"device": device}
    if "XL" in model_name:
        config["model"] = "sdxl"
    elif "v2" in model_name:
        config["model"] = "sd-v2"
    elif "Turbo" in model_name:
        config["model"] = "sdxl-turbo"
    elif "SD 3" in model_name:
        config["model"] = "sd3"
    else:
        config["model"] = "sd-v1"
    return config

def generate_image(
    prompt: str,
    negative_prompt: str = "",
    steps: int = 30,
    guidance_scale: float = 7.5,
    seed: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    result_callback: Optional[Callable[[str], None]] = None
):
    global _loaded_model
    if _loaded_model is None:
        if result_callback:
            result_callback(None)
        return

    def _generate():
        try:
            if progress_callback:
                progress_callback(0, steps, "Starting...")
            gen_kwargs = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": steps,
                "guidance_scale": guidance_scale,
                "seed": seed if seed is not None else int(time.time()),
            }
            if width and height:
                gen_kwargs["W"] = width
                gen_kwargs["H"] = height
            # 调用模型生成
            image = _loaded_model.generate(**gen_kwargs)
            if progress_callback:
                progress_callback(steps, steps, "Saving...")
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            image.save(temp_file.name)
            temp_file.close()
            if result_callback:
                result_callback(temp_file.name)
        except Exception as e:
            if progress_callback:
                progress_callback(0, steps, f"Error: {str(e)}")
            if result_callback:
                result_callback(None)

    Thread(target=_generate, daemon=True).start()