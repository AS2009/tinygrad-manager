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
    """Check for eGPU presence and report status."""
    output = run_command("SafeEjectGPU gpus")
    if "Error:" not in output and output:
        print(f"eGPU detected: {output}")
        print(f"To assign '{app_path}' to eGPU, use: System Preferences > GPU")
        return True
    else:
        print(f"No eGPU detected for: {app_path}")
        return False