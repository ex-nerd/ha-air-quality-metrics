"""Deploy script with structured JSON value parsing."""

import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def load_gitignore_patterns() -> list[str]:
    """Read the root .gitignore file and return a list of clean glob patterns."""
    patterns = []
    gitignore_path = Path(".gitignore")

    if gitignore_path.exists():
        with open(gitignore_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    else:
        print("⚠️ Warning: No .gitignore file found in the root directory.")
        sys.exit(1)
    return patterns


def prepare_staging_dir(
    prod_source_dir: Path,
    staging_dir: Path,
    domain: str,
    dev_domain: str,
    exclusions: list[str],
):
    """Clone and modify the original source so we can deploy a copy as dev_domain."""
    if prod_source_dir == staging_dir:
        return

    print(f"Creating clean local staging at: {staging_dir}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    # Use the gitignore patterns to prevent junk from copying into the sandbox
    shutil.copytree(
        prod_source_dir,
        staging_dir,
        ignore=shutil.ignore_patterns(*exclusions),
    )

    print("Updating sandbox files for dev name/domain using native JSON parsing...")

    # Update manifest.json for domain and package name
    manifest_path = staging_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest_data = json.load(f)

        if manifest_data.get("domain") == domain:
            manifest_data["domain"] = dev_domain

        if "name" in manifest_data:
            manifest_data["name"] = f"{manifest_data['name']} (dev)"

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    # Gather updates for strings.json and anything inside the translations folder
    translation_files = list(staging_dir.glob("*.json")) + list(
        staging_dir.glob("translations/*.json")
    )
    for json_file in translation_files:
        if json_file.name == "manifest.json":
            continue  # Handled above

        with open(json_file, encoding="utf-8") as f:
            json_data = json.load(f)

        if "title" in json_data:
            json_data["title"] = f"{json_data['title']} (dev)"

        # if (
        #     "config_entry_title" in json_data
        #     and domain in json_data["config_entry_title"]
        # ):
        #     # Reinsert config_entry_title under the new development domain header
        #     entry_title_map = json_data["config_entry_title"].pop(domain)
        #     json_data["config_entry_title"][dev_domain] = entry_title_map

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

    # Update python code namespace paths and hardcoded internal string constants
    print("Updating python code namespaces...")
    for py_file in staging_dir.rglob("*.py"):
        with open(py_file, encoding="utf-8") as f:
            code = f.read()

        initial_code = code

        # Swap module paths: custom_components.air_quality_metrics -> custom_components.air_quality_metrics_dev
        code = re.sub(
            r"custom_components\." + re.escape(domain) + r"\b",
            f"custom_components.{dev_domain}",
            code,
        )

        # Catch raw literal string references to the components DOMAIN constant definitions
        code = re.sub(
            r'(["\'])' + re.escape(domain) + r"\b\1",
            r"\1" + dev_domain + r"\1",
            code,
        )

        if code != initial_code:
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(code)


def monitor_ssh_command(remote_host: str, command: str, ssh_port: str | None = None):
    """Run remote SSH commands and stream standard outputs frame-by-frame."""
    ssh_cmd = ["ssh", "-tt"]
    if ssh_port and ssh_port != "22":
        ssh_cmd.extend(["-p", ssh_port])
    ssh_cmd.extend([remote_host, command])

    process = subprocess.Popen(
        ssh_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,  # Keep raw bytes at the Popen level
        bufsize=0,
    )

    if process.stdout is None:
        raise RuntimeError("Failed to open stdout stream.")

    # Wrap byte stream to smoothly handle line returns (\r) without TypeError
    text_stdout = io.TextIOWrapper(
        process.stdout,
        encoding="utf-8",
        errors="replace",
        newline="",
    )

    while True:
        char_str = text_stdout.read(1)
        if not char_str:
            break
        sys.stdout.write(char_str)
        sys.stdout.flush()

    process.wait()


def deploy():
    """Rsync the integration directory into Home Assistant."""
    try:
        from custom_components.air_quality_metrics.const import DOMAIN
    except ImportError:
        print(
            "❌ Error: Could not import 'DOMAIN' from 'custom_components/air_quality_metrics/const.py'!"
        )
        print("💡 Please ensure the folder structure is intact.")
        sys.exit(1)

    # Load local .env overrides if present
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Error: Local '.env' configuration file not found!")
        print(
            "Please copy '.env.example' to '.env' and populate your server variables."
        )
        sys.exit(1)

    from dotenv import load_dotenv

    load_dotenv(dotenv_path=env_path)

    # Pull configuration strings safely from environment arrays
    server_ip = os.getenv("HA_SERVER_IP")
    ssh_user = os.getenv("HA_SSH_USER")
    ssh_port = os.getenv("HA_SSH_PORT")
    cc_path = os.getenv("HA_CUSTOM_COMPONENTS_PATH", "/config/custom_components")

    if not server_ip:
        print(
            "❌ Error: 'HA_SERVER_IP' is not defined inside your local .env configuration."
        )
        sys.exit(1)

    dev_domain = os.getenv("HA_DEV_DOMAIN", f"{DOMAIN}_dev")
    is_dev_mode = DOMAIN != dev_domain
    target_domain = dev_domain if is_dev_mode else DOMAIN

    # Directory mapping
    base_components_dir = Path("custom_components")
    prod_source_dir = base_components_dir / DOMAIN
    staging_dir = base_components_dir / dev_domain

    # Load exclusions directly from the .gitignore file
    exclusions = load_gitignore_patterns()

    print(
        f"Context: {'DEVELOPMENT STAGING' if is_dev_mode else 'PRODUCTION RELEASE'} (Domain: {target_domain})"
    )

    try:
        if is_dev_mode:
            prepare_staging_dir(
                prod_source_dir, staging_dir, DOMAIN, dev_domain, exclusions
            )

        # Build connection paths dynamically
        remote_host = f"{ssh_user}@{server_ip}" if ssh_user else server_ip
        remote_component_dir = f"{cc_path.rstrip('/')}/{target_domain}"

        # Deploy source targets the sandboxed area during dev workflows
        active_source_dir = staging_dir if is_dev_mode else prod_source_dir
        local_source = f"{active_source_dir}/"
        remote_target = f"{remote_host}:{remote_component_dir}/"

        # Prepare base rsync command flags
        rsync_cmd = ["rsync", "-avz", "--delete"]
        if ssh_port and ssh_port != "22":
            rsync_cmd.extend(["-e", f"ssh -p {ssh_port}"])

        # Append .gitignore exclusions directly as rsync hide filters
        for pattern in exclusions:
            rsync_cmd.append(f"--filter=hide {pattern}")

        rsync_cmd.extend([local_source, remote_target])

        print(f"rsync to: {remote_target}")
        subprocess.run(rsync_cmd, check=True)
        print("✅ Deploy complete.")

        print(f"Restarting Home Assistant via 'ssh {remote_host}'.")
        monitor_ssh_command(remote_host, command="ha core restart", ssh_port=ssh_port)
        print("✅ Restart successful.")

    except KeyboardInterrupt:
        print("\n❌ Stream closed by user.")
        raise
    except subprocess.CalledProcessError as err:
        print(f"❌ Deployment pipeline failed with exit code: {err.returncode}")
        sys.exit(err.returncode)
    except FileNotFoundError:
        print("❌ Error: 'rsync' was not found in PATH variable.")
        sys.exit(1)

    finally:
        # Clean up our local sandbox directory so git stays unpolluted
        if is_dev_mode and staging_dir != prod_source_dir and staging_dir.exists():
            print(f"🧹 Dropping local scratchpad directory '{staging_dir}'...")
            shutil.rmtree(staging_dir)
