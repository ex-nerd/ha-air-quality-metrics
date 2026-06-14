import subprocess
import sys


def typecheck():
    print("🔍 Running type checker with ty...")
    result = subprocess.run(["uv", "run", "ty", "check"])
    sys.exit(result.returncode)
