"""
Project: Documents Team
Author: Dhinakaran Sekar
Email: dhinakaran.s@jubilantenterprises.in
Date: 2026-04-30 18:41
Description: Orchestration script to run both Flask backend and Vite frontend simultaneously.
"""

import subprocess
import os
import sys
import time
import signal

def run_app():
    """
    Launches the backend and frontend processes, monitors them, 
    and handles graceful shutdown on keyboard interrupt.
    """
    # Get the root directory
    root_dir = os.path.abspath(os.path.dirname(__file__))
    backend_dir = os.path.join(root_dir, 'backend')
    frontend_dir = os.path.join(root_dir, 'frontend')

    # Determine Python executable path in virtual environment
    if os.name == 'nt':  # Windows
        python_exe = os.path.join(backend_dir, 'env', 'Scripts', 'python.exe')
        npm_cmd = 'npm.cmd'
    else:
        python_exe = os.path.join(backend_dir, 'env', 'bin', 'python')
        npm_cmd = 'npm'

    if not os.path.exists(python_exe):
        print(f"Error: Virtual environment not found at {python_exe}")
        print("Please ensure the 'backend/env' virtual environment is set up.")
        return

    print("--- Starting Documents Team Application ---")

    # 1. Start Backend (Flask)
    print(f"[*] Starting Backend (Flask) from {backend_dir}...")
    backend_process = subprocess.Popen(
        [python_exe, 'app.py'],
        cwd=backend_dir
    )

    # Give backend a moment to initialize
    time.sleep(2)

    # 2. Start Frontend (Vite)
    print(f"[*] Starting Frontend (Vite/React) from {frontend_dir}...")
    try:
        frontend_process = subprocess.Popen(
            [npm_cmd, 'run', 'dev'],
            cwd=frontend_dir,
            shell=True if os.name == 'nt' else False
        )
    except FileNotFoundError:
        print("Error: 'npm' command not found. Please ensure Node.js is installed.")
        backend_process.terminate()
        return

    print("\n[✔] Both processes are running!")
    print("[!] Press Ctrl+C to shut down both servers.\n")

    try:
        # Keep the script running and monitor processes
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print("\n[!] Backend process stopped unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("\n[!] Frontend process stopped unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\n[!] Shutdown signal received (Ctrl+C).")
    finally:
        print("[*] Terminating processes...")
        backend_process.terminate()
        frontend_process.terminate()
        
        # Ensure they are really dead
        try:
            backend_process.wait(timeout=5)
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("[!] Processes did not terminate gracefully, forcing...")
            backend_process.kill()
            frontend_process.kill()
            
        print("[✔] Shutdown complete.")

if __name__ == "__main__":
    run_app()
