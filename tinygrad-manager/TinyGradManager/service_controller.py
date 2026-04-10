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
    subprocess.run(["launchctl", "load", PLIST_PATH])
    subprocess.run(["launchctl", "start", SERVICE_LABEL])
    return True

def stop_service():
    subprocess.run(["launchctl", "stop", SERVICE_LABEL])
    subprocess.run(["launchctl", "unload", PLIST_PATH])
    return True

def serve():
    print("TinyGrad service is running...")
    import time
    while True:
        time.sleep(10)

if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()