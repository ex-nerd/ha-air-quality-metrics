#!/usr/bin/env python3
"""Unified verification script that directly imports and executes pipeline steps."""

import sys

from scripts.format import format
from scripts.lint import lint
from scripts.test import test
from scripts.typecheck import typecheck


def run_step(description: str, step_func) -> None:
    """Execute a single verification step and manage output wrapper blocks.

    This ensures we continue to run the full verification suite even if
    an individual step tries to exit cleanly.
    """
    print("=" * 60)
    print(f"🏃 Running: {description}...")
    print("=" * 60)

    try:
        # Run the imported function directly in-process
        step_func()
        print(f"✅ {description} passed!\n")

    except SystemExit as exit_exc:
        # Catch explicit exits from the tool run (e.g. pytest or ruff failing)
        if exit_exc.code != 0:
            print(f"❌ {description} failed with exit code {exit_exc.code}.\n")
            sys.exit(exit_exc.code)
        print(f"✅ {description} passed!\n")

    except Exception as err:
        print(f"💥 Unexpected runtime error running {description}: {err}\n")
        sys.exit(1)


def verify() -> None:
    """Execute the hard-coded development verification pipeline."""
    run_step("Format", format)
    run_step("Type checking", typecheck)
    run_step("Linting checks", lint)
    run_step("Unit test suite", test)

    print("==================================================")
    print("🎉 All checks passed successfully! Your code is clean.")
    print("==================================================")
    sys.exit(0)
