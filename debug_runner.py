import subprocess
import sys
import os

# 设置环境变量以确保输出不缓冲
env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"

print("Starting main.py wrapper...")

with open("full_log.txt", "w") as f:
    process = subprocess.Popen(
        ["python", "main.py"],
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )
    exit_code = process.wait()
    print(f"Process exited with code {exit_code}")

















