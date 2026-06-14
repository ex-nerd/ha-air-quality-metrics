import subprocess
import sys


def lint():
    print("🧹 Linting and auto-fixing with Ruff...")
    result = subprocess.run(["uv", "run", "ruff", "check", ".", "--fix"])
    sys.exit(result.returncode)
