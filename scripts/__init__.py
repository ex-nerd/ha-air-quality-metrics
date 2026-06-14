"""
Repository management and automation scripts.

- If you're not a developer, you can look away.
- If you are a developer, you hopefully know what these do.

This file acts as a dynamic orchestration layer, allowing any module in this
directory to be called via uv from `[project.scripts]` in pyproject.toml. It
automatically shifts the execution context to the repository root directory
before running, ensuring imports and environment configuration files are
detected properly.

To expose a script, add it to pyproject.toml without modifying this file:

```toml
[project.scripts]
test = "scripts:test"
deploy = "scripts:deploy"
```
"""

import importlib
import os
import sys
from pathlib import Path

# Calculate the root path relative to this __init__.py file
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def _run_script(module_name: str):
    """Dynamically loads and runs the requested module's matching function entrypoint."""
    # Enforce execution context at the project root
    os.chdir(PROJECT_ROOT)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))

    # Dynamically attempt to import the matching script file
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(
            f"❌ Error: Automation script '{module_name}.py' was not found inside the scripts/ directory."
        )
        print(f"💡 Expected location: scripts/{module_name}.py")
        sys.exit(1)

    # Verify and execute the function matching the module name
    if hasattr(module, module_name):
        entrypoint_func = getattr(module, module_name)
        entrypoint_func()
    else:
        print(
            f"❌ Error: Script '{module_name}.py' loaded successfully, but it is missing a `def {module_name}():` entry point."
        )
        sys.exit(1)


def __getattr__(name: str):
    """Intercepts missing function calls (e.g., scripts:test -> name='test')

    Returns a dynamic wrapper function on the fly.
    """
    # Exclude standard double-underscore internal lookups
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

    # Return a zero-argument function that uv can execute directly
    return lambda: _run_script(name)
