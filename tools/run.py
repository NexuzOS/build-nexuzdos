import subprocess
import os
import sys
from pathlib import Path


def exec(cmd, cwd=None, env=None):

    if isinstance(cmd, (list, tuple)):
        cmd = [str(c) for c in cmd]
    else:
        raise TypeError("cmd must be list or tuple")

    print("$", " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed ({process.returncode}): {' '.join(cmd)}"
        )
        
        

def run(cmd, cwd=None, env=None, check=True):
    """
    Execute a command with live output.

    cmd  : list[str] | str
    cwd  : working directory
    env  : additional environment variables
    """

    if isinstance(cmd, str):
        cmd = cmd.split()

    env_combined = os.environ.copy()
    if env:
        env_combined.update(env)

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env_combined,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if check and process.returncode != 0:
        raise RuntimeError(f"Command failed ({process.returncode}): {' '.join(cmd)}")

    return process.returncode