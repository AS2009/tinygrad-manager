import subprocess
import sys
import importlib.util
import shutil
from typing import Dict, Any, List, Optional, Tuple

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