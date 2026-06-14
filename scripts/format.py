import subprocess
import sys


def format():
    print("🎨 Formatting code with Ruff...")
    result = subprocess.run(["uv", "run", "ruff", "format", "."])
    sys.exit(result.returncode)
