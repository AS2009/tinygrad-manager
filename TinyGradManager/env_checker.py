# env_checker.py
# 对齐 tinygrad 官方文档的环境检测模块

import subprocess
import sys
import importlib.util
import os
import shutil
from typing import Dict, Any, List, Optional, Tuple

# ------------------------------------------------------------
# 基础工具函数
# ------------------------------------------------------------
def run_command(cmd: str, timeout: int = 5) -> Tuple[bool, str]:
    """安全地执行 shell 命令，返回 (成功与否, 输出内容)。"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        return False, str(e)

def find_executable(name: str) -> Optional[str]:
    """在系统 PATH 中查找可执行文件。"""
    return shutil.which(name)

# ------------------------------------------------------------
# 1. TinyGrad 检测
# ------------------------------------------------------------
def check_tinygrad() -> Dict[str, Any]:
    """检测 tinygrad 是否已安装，并获取版本和默认设备。"""
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
        else:
            try:
                import pkg_resources
                result["version"] = pkg_resources.get_distribution("tinygrad").version
            except Exception:
                result["version"] = "unknown"
        try:
            from tinygrad import Device
            result["default_device"] = Device.DEFAULT
        except Exception:
            pass
    except Exception as e:
        result["error"] = str(e)
    return result

# ------------------------------------------------------------
# 2. TinyGPU 驱动检测 (对齐官方文档)
# ------------------------------------------------------------
def check_tinygpu_driver() -> Dict[str, Any]:
    """
    检测 TinyGPU 驱动是否已安装并激活。
    严格对齐官方文档：https://docs.tinygrad.org/tinygpu/
    """
    result = {"installed": False, "activated": False, "details": ""}
    if sys.platform != "darwin":
        result["details"] = "Not macOS"
        return result

    # 1. 检查 systemextensionsctl 中的 TinyGPU 扩展
    success, output = run_command("systemextensionsctl list", timeout=5)
    if success:
        lines = output.split('\n')
        for line in lines:
            # 查找包含 "TinyGPU" 的行
            if "TinyGPU" in line or ("tinygrad" in line.lower() and "com.tinygrad" in line):
                result["installed"] = True
                result["details"] += "Extension found in systemextensionsctl; "
                # 检查激活状态：通常有 "[activated enabled]" 字样
                if "[activated" in line or "activated enabled" in line.lower():
                    result["activated"] = True
                break

    # 2. 备选：检查官方驱动扩展目录
    driver_ext_path = "/Library/DriverExtensions"
    if os.path.exists(driver_ext_path):
        for item in os.listdir(driver_ext_path):
            if "tinygrad" in item.lower() or "tinygpu" in item.lower():
                result["installed"] = True
                result["details"] += f"Extension directory found: {item}; "
                # 检查系统设置中的激活状态
                settings_check = run_command("defaults read /Library/Preferences/com.apple.driverkit", timeout=3)
                if settings_check[0] and "TinyGPU" in settings_check[1]:
                    result["activated"] = True

    # 3. 检测 tinygrad 运行时是否识别到 NV 或 AMD 设备 (TinyGPU 激活的标志)
    try:
        from tinygrad import Device
        available = Device.get_available_devices()
        if any(dev in available for dev in ["NV", "AMD"]):
            result["activated"] = True
            result["details"] += "NV/AMD device available via tinygrad; "
    except Exception:
        pass

    return result

# ------------------------------------------------------------
# 3. Metal 检测
# ------------------------------------------------------------
def check_metal() -> Dict[str, Any]:
    """检测 macOS Metal 加速是否可用。"""
    result = {"available": False, "details": ""}
    if sys.platform != "darwin":
        result["details"] = "Not macOS"
        return result
    try:
        success, output = run_command("system_profiler SPDisplaysDataType", timeout=10)
        if success and "Metal:" in output:
            result["available"] = True
            for line in output.split('\n'):
                if "Metal:" in line:
                    result["details"] = line.strip()
                    break
    except Exception as e:
        result["details"] = f"Error: {e}"
    return result

# ------------------------------------------------------------
# 4. CUDA / NVCC 检测 (对齐官方 setup_nvcc_osx.sh)
# ------------------------------------------------------------
def check_cuda() -> Dict[str, Any]:
    """
    全面检测 CUDA/NVCC 环境，对齐官方 setup_nvcc_osx.sh 方案。
    支持通过 Docker (官方方式) 或 OrbStack 等虚拟化环境。
    """
    result = {
        "nvcc_available": False, "nvcc_version": None, "nvcc_path": None,
        "cuda_home": None, "docker_cuda": False, "orbstack_cuda": False, "details": ""
    }

    # 1. 标准 nvcc 检测
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

    # 2. 检测官方 Docker 方式的 CUDA 环境 (setup_nvcc_osx.sh)
    docker_nvcc_path = os.path.expanduser("~/.local/bin/nvcc")
    if os.path.exists(docker_nvcc_path) and not result["nvcc_available"]:
        # 官方脚本创建的是一个 shim，指向 Docker 容器
        result["nvcc_available"] = True
        result["nvcc_path"] = docker_nvcc_path
        result["docker_cuda"] = True
        result["details"] += "Official Docker-based CUDA environment detected; "

    # 3. CUDA_HOME 环境变量
    cuda_home = os.environ.get("CUDA_HOME") or os.environ.get("CUDA_PATH")
    if cuda_home:
        result["cuda_home"] = cuda_home

    # 4. OrbStack 环境检测
    orbstack_indicators = ["~/.orbstack", "/Applications/OrbStack.app", "/usr/local/bin/orb"]
    for indicator in orbstack_indicators:
        if os.path.exists(os.path.expanduser(indicator)):
            result["orbstack_cuda"] = True
            result["details"] += "OrbStack environment detected; "
            break

    # 5. 若 tinygrad 本身能识别 NV 运行时
    if not result["nvcc_available"]:
        try:
            from tinygrad import Device
            if "NV" in Device.get_available_devices():
                result["nvcc_available"] = True
                result["details"] += "NV runtime detected by tinygrad; "
        except Exception:
            pass

    return result

# ------------------------------------------------------------
# 5. AMD 编译器检测 (对齐官方 setup_hipcomgr_osx.sh)
# ------------------------------------------------------------
def check_amd_compiler() -> Dict[str, Any]:
    """
    检测 AMD 编译器环境。
    对齐官方 setup_hipcomgr_osx.sh: 检查 libamd_comgr.dylib。
    """
    result = {"available": False, "lib_comgr_path": None, "details": ""}
    # 官方默认安装路径
    default_paths = ["/opt/homebrew/lib/libamd_comgr.dylib", "/usr/local/lib/libamd_comgr.dylib"]
    # 也可以通过 LD_LIBRARY_PATH 查找
    ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
    for path in default_paths + ld_library_path.split(':'):
        if path and os.path.exists(path):
            result["available"] = True
            result["lib_comgr_path"] = path
            result["details"] = f"Found at {path}"
            break
    return result

# ------------------------------------------------------------
# 6. eGPU 硬件检测
# ------------------------------------------------------------
def check_egpu_hardware() -> Dict[str, Any]:
    """检测物理 eGPU 设备是否连接。"""
    result = {"detected": False, "gpu_list": [], "details": ""}
    if sys.platform == "darwin":
        safe_eject = find_executable("SafeEjectGPU")
        if safe_eject:
            success, output = run_command("SafeEjectGPU gpus", timeout=5)
            if success and output and "Error" not in output:
                lines = output.strip().splitlines()
                for line in lines:
                    if line.strip() and not line.startswith("GPUs"):
                        result["gpu_list"].append(line.strip())
                if result["gpu_list"]:
                    result["detected"] = True
                    result["details"] = f"Found {len(result['gpu_list'])} eGPU(s) via SafeEjectGPU"
    return result

# ------------------------------------------------------------
# 7. 综合检测函数
# ------------------------------------------------------------
def check_environment() -> Dict[str, Any]:
    """综合检测所有环境组件。"""
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
    """将环境检测结果格式化为人类可读的文本报告。"""
    lines = []
    lines.append("=" * 60)
    lines.append("TinyGrad Environment Check (Aligned with Official Docs)")
    lines.append("=" * 60)
    lines.append(f"Python: {env_info['python_version']} on {env_info['platform']}")
    if env_info["available_runtimes"]:
        lines.append(f"Available Runtimes: {', '.join(env_info['available_runtimes'])}")
    lines.append("")

    # TinyGrad
    tg = env_info["tinygrad"]
    lines.append("--- TinyGrad ---")
    if tg["installed"]:
        lines.append(f"✅ Installed (version {tg['version']})")
        if tg["default_device"]:
            lines.append(f"   Default device: {tg['default_device']}")
    else:
        lines.append(f"❌ Not installed ({tg.get('error', 'unknown')})")
    lines.append("")

    # TinyGPU 驱动
    tgpu = env_info["tinygpu"]
    lines.append("--- TinyGPU Driver (Official) ---")
    if tgpu["installed"]:
        status = "✅ Activated" if tgpu["activated"] else "⚠️ Installed but not activated"
        lines.append(f"{status}")
    else:
        lines.append("ℹ️ Not installed")
    if tgpu["details"]:
        lines.append(f"   Details: {tgpu['details']}")
    lines.append("")

    # Metal
    metal = env_info["metal"]
    lines.append("--- Metal ---")
    if metal["available"]:
        lines.append(f"✅ Available ({metal['details']})")
    else:
        lines.append("ℹ️ Not available")
    lines.append("")

    # CUDA
    cuda = env_info["cuda"]
    lines.append("--- CUDA / NVCC ---")
    if cuda["nvcc_available"]:
        lines.append(f"✅ NVCC available: {cuda['nvcc_path']}")
        if cuda["nvcc_version"]:
            lines.append(f"   Version: {cuda['nvcc_version']}")
        if cuda["docker_cuda"]:
            lines.append("   📦 Using official Docker-based CUDA")
    else:
        lines.append("❌ NVCC not found")
    if cuda["orbstack_cuda"]:
        lines.append("   📦 OrbStack environment detected")
    if cuda["details"]:
        lines.append(f"   Details: {cuda['details']}")
    lines.append("")

    # AMD
    amd = env_info["amd"]
    lines.append("--- AMD Compiler (Official) ---")
    if amd["available"]:
        lines.append(f"✅ libamd_comgr.dylib found: {amd['lib_comgr_path']}")
    else:
        lines.append("ℹ️ Not installed")
    lines.append("")

    # eGPU 硬件
    egpu = env_info["egpu_hardware"]
    lines.append("--- eGPU Hardware ---")
    if egpu["detected"]:
        lines.append(f"✅ Detected {len(egpu['gpu_list'])} eGPU device(s)")
        for gpu in egpu["gpu_list"]:
            lines.append(f"   - {gpu}")
    else:
        lines.append("ℹ️ No eGPU detected")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)

# ------------------------------------------------------------
# 便捷函数
# ------------------------------------------------------------
def has_local_tinygrad() -> bool:
    return check_tinygrad()["installed"]

def has_gpu_acceleration() -> bool:
    env = check_environment()
    return (env["metal"]["available"] or env["cuda"]["nvcc_available"] or
            env["tinygpu"]["activated"] or env["amd"]["available"])

def get_available_runtimes() -> List[str]:
    """获取 tinygrad 可用的运行时列表。"""
    try:
        from tinygrad import Device
        return list(Device.get_available_devices())
    except Exception:
        return []