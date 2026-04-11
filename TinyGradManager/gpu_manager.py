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
    run_command(f"set-eGPU.sh -ss {app_path}")
    print(f"Set eGPU preference for: {app_path}")