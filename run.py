import os
import subprocess
import time
import sys
import webbrowser
import socket
from pathlib import Path

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    if is_port_in_use(port):
        print(f"[*] Port {port} is busy. Cleaning up...")
        if sys.platform == "win32":
            subprocess.run(f"powershell -Command \"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force\"", shell=True, capture_output=True)
        else:
            subprocess.run(f"fuser -k {port}/tcp", shell=True, capture_output=True)
        time.sleep(1)

def run():
    print("""
    ==================================================
    TRINETHRA AI - PROFESSIONAL ANALYZER BOOTSTRAP
    ==================================================
    """)

    # 1. Cleanup
    kill_process_on_port(8005)
    kill_process_on_port(5500)

    # 2. Install Dependencies
    print("[*] Checking dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"])

    # 3. Start Backend
    print("[*] Starting Backend (Port 8005)...")
    backend_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    # 4. Start Frontend
    print("[*] Starting Frontend (Port 5500)...")
    frontend_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "5500"],
        cwd="frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    # 5. Wait for servers to be ready
    print("[*] Waiting for services to stabilize...")
    time.sleep(3)

    # 6. Open Browser
    url = "http://localhost:5500"
    print(f"[*] Launching Trinethra AI at {url}")
    webbrowser.open(url)

    print("\n[!] Project is running. Press Ctrl+C to stop both servers.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("[+] Goodbye!")

if __name__ == "__main__":
    run()
