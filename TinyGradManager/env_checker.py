import os
import subprocess
import sys
import importlib.util
import shutil
from typing import Dict, Any, List, Optional, Tuple

# Force Metal GPU usage on macOS — must be set before any tinygrad import
if sys.platform == "darwin":
    os.environ.setdefault("METAL", "1")
    os.environ.setdefault("GPU", "1")

def run_command(cmd: str, timeout: int = 5) -> Tuple[bool, str]:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        return False, str(e)

def find_executable(name: str) -> Optional[str]:
    return shutil.which(name)

def check_tinygrad() -> Dict[str, Any]:
    result = {"installed": False, "version": None, "default_device": None, "error": None}
    spec = importlib.util.find_spec("tinygrad")
    if spec is None:
        result["error"] = "TinyGrad not found in Python environment."
        return result
    try:
        import tinygrad
        result["installed"] = True
        if hasattr(tinygrad, "__version__"):
            result["version"] = tinygrad.__version__
        try:
            from tinygrad import Device
            result["default_device"] = Device.DEFAULT
        except:
            pass
    except Exception as e:
        result["error"] = str(e)
    return result

def check_tinygpu_driver() -> Dict[str, Any]:
    result = {"installed": False, "activated": False, "details": ""}
    if sys.platform != "darwin":
        result["details"] = "Not macOS"
        return result
    success, output = run_command("systemextensionsctl list", timeout=5)
    if success:
        lines = output.split('\n')
        for line in lines:
            if "TinyGPU" in line or ("tinygrad" in line.lower() and "com.tinygrad" in line):
                result["installed"] = True
                if "[activated" in line or "activated enabled" in line.lower():
                    result["activated"] = True
                break
    return result

def check_metal() -> Dict[str, Any]:
    result = {"available": False, "details": ""}
    if sys.platform != "darwin":
        result["details"] = "Not macOS"
        return result
    success, output = run_command("system_profiler SPDisplaysDataType", timeout=10)
    if success and "Metal:" in output:
        result["available"] = True
        for line in output.split('\n'):
            if "Metal:" in line:
                result["details"] = line.strip()
                break
    return result

def check_cuda() -> Dict[str, Any]:
    result = {
        "nvcc_available": False, "nvcc_version": None, "nvcc_path": None,
        "cuda_home": None, "docker_cuda": False, "orbstack_cuda": False, "details": ""
    }
    nvcc_path = find_executable("nvcc")
    if nvcc_path:
        result["nvcc_available"] = True
        result["nvcc_path"] = nvcc_path
        success, version_out = run_command("nvcc --version", timeout=5)
        if success:
            for line in version_out.split('\n'):
                if "release" in line:
                    result["nvcc_version"] = line.strip()
                    break
    return result

def check_amd_compiler() -> Dict[str, Any]:
    """检测 AMD GPU / ROCm 编译器。macOS 上检测 AMD 显卡存在性。"""
    result = {"available": False, "details": ""}
    if sys.platform == "darwin":
        success, output = run_command("system_profiler SPDisplaysDataType", timeout=8)
        if success and "AMD" in output:
            result["available"] = True
            for line in output.split('\n'):
                if "AMD" in line:
                    result["details"] = line.strip()
                    break
        else:
            result["details"] = "No AMD GPU found"
    else:
        # Linux: check for ROCm
        rocm_path = shutil.which("hipcc") or shutil.which("amdclang")
        if rocm_path:
            result["available"] = True
            result["details"] = f"ROCm compiler found: {rocm_path}"
        else:
            result["details"] = "ROCm compiler not found"
    return result

def check_egpu_hardware() -> Dict[str, Any]:
    """通过 SafeEjectGPU 检测外置 GPU (eGPU)。"""
    result = {"detected": False, "gpu_list": [], "details": ""}
    if sys.platform != "darwin":
        result["details"] = "Not macOS"
        return result
    success, output = run_command("SafeEjectGPU gpus", timeout=8)
    if success and output:
        result["detected"] = True
        result["gpu_list"] = [line.strip() for line in output.split('\n') if line.strip()]
        result["details"] = output.strip()
    else:
        result["details"] = "No eGPU detected or SafeEjectGPU unavailable"
    return result

def check_environment() -> Dict[str, Any]:
    return {
        "tinygrad": check_tinygrad(),
        "tinygpu": check_tinygpu_driver(),
        "metal": check_metal(),
        "cuda": check_cuda(),
        "amd": check_amd_compiler(),
        "egpu_hardware": check_egpu_hardware(),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "available_runtimes": get_available_runtimes()
    }

def format_env_report(env_info: Dict[str, Any]) -> str:
    lines = ["=== TinyGrad Environment ==="]
    tg = env_info["tinygrad"]
    lines.append(f"TinyGrad: {'✅ ' + tg['version'] if tg['installed'] else '❌ Not installed'}")
    lines.append(f"Metal: {'✅' if env_info['metal']['available'] else '❌'}")
    lines.append(f"CUDA: {'✅' if env_info['cuda']['nvcc_available'] else '❌'}")
    return "\n".join(lines)

def has_local_tinygrad() -> bool:
    return check_tinygrad()["installed"]

def get_available_runtimes() -> List[str]:
    try:
        from tinygrad import Device
        return list(Device.get_available_devices())
    except:
        return []

def get_available_gpu_devices() -> List[str]:
    """Return GPU device strings usable by both tinygrad and PyTorch/diffusers.

    Priority: CUDA devices first, then MPS (Apple Silicon).
    Only GPU devices are returned — no CPU fallback.
    """
    devices = []
    has_mps = False

    # Check for CUDA GPUs via PyTorch
    try:
        import torch
        cuda_count = torch.cuda.device_count()
        for i in range(cuda_count):
            name = torch.cuda.get_device_name(i)
            devices.append(f"cuda:{i} ({name})")
    except Exception:
        pass

    # Check for MPS (Apple Silicon) via PyTorch
    try:
        import torch
        if torch.backends.mps.is_available():
            devices.append("mps (Apple Silicon GPU)")
            has_mps = True
    except Exception:
        pass

    # Also check tinygrad devices and map them
    try:
        from tinygrad import Device
        tg_devices = list(Device.get_available_devices())
        for d in tg_devices:
            d_upper = d.upper()
            if "CUDA" in d_upper and not any(dev.startswith("cuda:") for dev in devices):
                try:
                    import torch
                    cuda_count = torch.cuda.device_count()
                    for i in range(cuda_count):
                        name = torch.cuda.get_device_name(i)
                        dev_str = f"cuda:{i} ({name})"
                        if dev_str not in devices:
                            devices.append(dev_str)
                except Exception:
                    devices.append(d)
            elif _is_apple_gpu_device(d_upper):
                if not has_mps and "mps" not in str(devices).lower():
                    devices.append("mps (Apple Silicon GPU)")
                    has_mps = True
    except Exception:
        pass

    # Fallback: system-level Metal check on macOS (covers built-in GPU)
    if not has_mps and sys.platform == "darwin" and "mps" not in str(devices).lower():
        metal_info = check_metal()
        if metal_info.get("available"):
            devices.append("mps (Apple Silicon GPU)")
            has_mps = True

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for d in devices:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


def _is_apple_gpu_device(device_name_upper: str) -> bool:
    """Check if a tinygrad device name represents an Apple GPU (Metal/ANE)."""
    apple_devices = {"METAL", "GPU", "ANE"}
    # Exact match for short names like "METAL", "GPU", "ANE"
    if device_name_upper in apple_devices:
        return True
    # Prefix match for names like "METAL:0", "METAL:1", "ANE:0"
    for prefix in apple_devices:
        if device_name_upper.startswith(prefix + ":") or device_name_upper.startswith(prefix + "|"):
            return True
    return False

def parse_gpu_device_key(device_str: str) -> str:
    """Extract the device key (e.g. 'cuda:0', 'mps') from a display string.

    Handles display strings like "cuda:0 (NVIDIA ...)", "mps (Apple Silicon GPU)",
    and raw tinygrad device names like "METAL", "GPU", "ANE", "CUDA".
    Only GPU devices are supported — defaults to "mps" if unrecognized.
    """
    if not device_str:
        return "mps"
    d = device_str.strip()
    d_upper = d.upper()

    # "cuda:0 (NVIDIA GeForce RTX 3080)" -> "cuda:0"
    if d.startswith("cuda:") or d_upper.startswith("CUDA"):
        if " (" in d:
            return d.split(" (")[0].lower()
        return d.lower()

    # "mps (Apple Silicon GPU)" -> "mps"
    if d.lower().startswith("mps"):
        return "mps"

    # Raw tinygrad device names: METAL, GPU, ANE -> mps
    if d_upper in ("METAL", "GPU", "ANE"):
        return "mps"
    # METAL:0, GPU:0, ANE:0, etc.
    for prefix in ("METAL:", "GPU:", "ANE:"):
        if d_upper.startswith(prefix):
            return "mps"

    # Default to MPS (Apple Silicon GPU) — no CPU fallback
    return "mps"

def set_tinygrad_device(device_key: str) -> str:
    """Set tinygrad's device based on a parsed device key.

    Uses multiple strategies to force GPU usage:
    1. Environment variables (METAL=1, GPU=1)
    2. DEV.value API (tinygrad >= 0.9)
    3. Device.DEFAULT assignment (older tinygrad)

    Returns the actual device string that was set (e.g. 'METAL', 'CUDA:0').
    """
    # Map parsed key to tinygrad device name
    if device_key.startswith("cuda"):
        cuda_idx = device_key.split(":")[-1] if ":" in device_key else "0"
        target = f"CUDA:{cuda_idx}"
        os.environ["GPU"] = "1"
    elif device_key == "mps":
        target = "METAL"
        os.environ["METAL"] = "1"
        os.environ["GPU"] = "1"
    else:
        target = "METAL"  # Default to Metal GPU
        os.environ["METAL"] = "1"
        os.environ["GPU"] = "1"

    # Strategy 1: newer tinygrad DEV.value API
    try:
        from tinygrad.helpers import DEV
        DEV.value = target
    except ImportError:
        pass

    # Strategy 2: deprecated Device.DEFAULT assignment
    try:
        from tinygrad import Device
        Device.DEFAULT = target
    except (ImportError, AttributeError):
        pass

    # Strategy 3: set Device._DEFAULT directly (bypass property)
    try:
        from tinygrad import Device
        if hasattr(Device, '_DEFAULT'):
            Device._DEFAULT = target
    except (ImportError, AttributeError):
        pass

    # Verify what actually got set
    try:
        from tinygrad import Device
        current = str(Device.DEFAULT)
    except Exception:
        current = target
    return f"{target} (current: {current})"

def check_diffusers() -> Dict[str, Any]:
    """Check if diffusers and related packages are available for image generation."""
    result = {
        "diffusers_available": False,
        "transformers_available": False,
        "torch_available": False,
        "stable_diffusion_ready": False,
        "details": ""
    }
    try:
        spec = importlib.util.find_spec("diffusers")
        result["diffusers_available"] = spec is not None
    except Exception:
        pass
    try:
        spec = importlib.util.find_spec("transformers")
        result["transformers_available"] = spec is not None
    except Exception:
        pass
    try:
        spec = importlib.util.find_spec("torch")
        result["torch_available"] = spec is not None
    except Exception:
        pass

    if result["diffusers_available"] and result["transformers_available"] and result["torch_available"]:
        result["stable_diffusion_ready"] = True
        result["details"] = "Stable Diffusion dependencies available"
    else:
        missing = []
        if not result["diffusers_available"]:
            missing.append("diffusers")
        if not result["transformers_available"]:
            missing.append("transformers")
        if not result["torch_available"]:
            missing.append("torch")
        result["details"] = f"Missing: {', '.join(missing)}"

    return result