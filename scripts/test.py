import subprocess
import sys


def test():
    print("🧪 Running unit tests with pytest...")
    # Directly calls pytest inside the uv managed environment
    result = subprocess.run(["pytest", "tests/"])
    sys.exit(result.returncode)
