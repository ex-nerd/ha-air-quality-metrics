import shutil
from pathlib import Path


def clean():
    print("🧹 Cleaning project workspace...")
    patterns = [".pytest_cache", ".ruff_cache", "*.egg-info"]
    for pattern in patterns:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"Removed directory: {path}")
            elif path.is_file():
                path.unlink()
                print(f"Removed file: {path}")

    # Clean nested __pycache__
    for path in Path(".").rglob("__pycache__"):
        shutil.rmtree(path)
    print("✨ Workspace is clean!")
