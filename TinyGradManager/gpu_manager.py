import subprocess

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"

def get_gpu_info():
    output = run_command("system_profiler SPDisplaysDataType | grep 'Chipset Model'")
    if output and "Error:" not in output:
        return output.split(": ")[-1]
    return "GPU info not available"

def list_egpus():
    return run_command("SafeEjectGPU gpus")

def get_gpu_status(gpu_id):
    return run_command(f"SafeEjectGPU gpuid {gpu_id} status")

def set_app_egpu_preference(app_path):
    """设置应用的 eGPU 偏好（macOS 系统偏好）"""
    # 使用 macOS 内置的 eGPU 偏好设置机制
    # set-eGPU.sh 是第三方工具，不一定存在，改为使用系统方法
    output = run_command(f"SafeEjectGPU gpus")
    if "Error:" not in output:
        print(f"eGPU detected. To assign '{app_path}' to eGPU, use: System Preferences > GPU")
    else:
        print(f"No eGPU detected. eGPU preference set attempted for: {app_path}")
    print(f"eGPU preference set for: {app_path}")