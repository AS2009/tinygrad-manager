import subprocess
import os
import sys

SERVICE_LABEL = "com.tinygrad.manager.service"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{SERVICE_LABEL}.plist")

def create_plist():
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{SERVICE_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
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
    """后台服务：初始化 tinygrad 运行时，保持运行"""
    print("TinyGrad GPU service starting...")
    try:
        from tinygrad import Device
        default_device = Device.DEFAULT
        print(f"Initialized default device: {default_device}")
    except Exception as e:
        print(f"Error initializing tinygrad: {e}")

    import time
    while True:
        time.sleep(10)

if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()