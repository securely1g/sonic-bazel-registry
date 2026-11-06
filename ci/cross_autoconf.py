"""Give Autoconf the selected cross compiler's identity without editing recipes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil


def prepare(work: Path, artifacts: Path, flags: list[str]) -> dict:
    """Add a readonly site file for cross builds, preserving explicit action env."""
    for index, flag in enumerate(flags):
        value = None
        if flag.startswith("--action_env="):
            value = flag.removeprefix("--action_env=")
        elif flag == "--action_env" and index + 1 < len(flags):
            value = flags[index + 1]
        if value == "CONFIG_SITE" or (value is not None and value.startswith("CONFIG_SITE=")):
            receipt = {"enabled": False, "reason": "explicit CONFIG_SITE action environment"}
            break
    else:
        content = Path(__file__).with_suffix(".site").read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        directory = work.resolve() / "cross-autoconf" / digest
        directory.mkdir(parents=True, exist_ok=True)
        site = directory / "config.site"
        if site.is_symlink() or (site.exists() and site.read_bytes() != content):
            raise ValueError("Cross Autoconf site differs from its content-addressed source")
        if not site.exists():
            site.write_bytes(content)
        site.chmod(0o444)
        added = [f"--action_env=CONFIG_SITE={site}",
                 f"--sandbox_add_mount_pair={directory}:{directory}"]
        flags.extend(added)
        shutil.copy2(site, artifacts / "cross-autoconf.site")
        receipt = {"enabled": True, "site_sha256": digest, "site_path": str(site), "flags": added}
    (artifacts / "cross-autoconf.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
