import subprocess
import os
import sys
import signal

SERVICE_LABEL = "com.tinygrad.manager.service"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{SERVICE_LABEL}.plist")

# Use the same Python that runs the GUI, not a hardcoded path
_PYTHON_BIN = sys.executable

def create_plist():
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{SERVICE_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{_PYTHON_BIN}</string>
        <string>{os.path.abspath(__file__)}</string>
        <string>--serve</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{os.path.expanduser("~/tinygrad-service.log")}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.expanduser("~/tinygrad-service.err")}</string>
</dict>
</plist>
"""
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    with open(PLIST_PATH, "w") as f:
        f.write(plist_content)

def start_service():
    if not os.path.exists(PLIST_PATH):
        create_plist()
    r1 = subprocess.run(["launchctl", "load", PLIST_PATH])
    if r1.returncode != 0:
        return False
    r2 = subprocess.run(["launchctl", "start", SERVICE_LABEL])
    return r2.returncode == 0

def stop_service():
    r1 = subprocess.run(["launchctl", "stop", SERVICE_LABEL])
    r2 = subprocess.run(["launchctl", "unload", PLIST_PATH])
    return r1.returncode == 0 and r2.returncode == 0

def serve():
    """后台服务：初始化 tinygrad 运行时并保持运行，支持优雅退出"""
    print("TinyGrad GPU service starting...")
    running = True

    def _handle_signal(signum, frame):
        nonlocal running
        print(f"Received signal {signum}, shutting down...")
        running = False

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        from tinygrad import Device
        default_device = Device.DEFAULT
        print(f"Initialized default device: {default_device}")
    except Exception as e:
        print(f"Error initializing tinygrad: {e}")
        return 1

    import time
    while running:
        time.sleep(5)
    print("GPU service stopped.")
    return 0

if __name__ == "__main__":
    if "--serve" in sys.argv:
        sys.exit(serve())