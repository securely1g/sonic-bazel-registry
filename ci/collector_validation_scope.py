#!/usr/bin/env python3
"""Temporary no-DEB validation scope for the collector fix and its PR175 consumer.

Normal branches retain the full registry matrix. Remove this guard when those
PRs leave their authorized source-only scope; it is not a general CI exemption.
The ordinary planner must run first so publication checks are never bypassed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

BRANCHES = {"codex/registry-unicode-artifacts", "codex/docbook-tools-registry"}
VERSION = "0.0.26-270b1cb187a3e42aec95ab2d3871fb077b4c484d"
CANDIDATE = "modules/sonic-build-infra/" + VERSION
CANDIDATE_TREE = "ca25ddbe7cb4aee9c41738c8094afc0f14ddc98a"
COLLECTOR_FILES = {
    ".github/workflows/registry-ci.yml", "ci/registry_ci.py",
    "ci/collector_validation_scope.py", "ci/README.md",
    "ci/tests/test_artifact_preservation.py", "ci/tests/test_bazel_artifacts.py",
    "ci/tests/test_collector_validation_scope.py",
}


def select(matrix: dict, changed: list[str], branch: str, candidate_tree: str | None) -> dict:
    if branch not in BRANCHES:
        raise ValueError("Temporary collector scope requires an explicitly reviewed branch")
    allowed_modules = branch == "codex/docbook-tools-registry"
    for name in changed:
        if name in COLLECTOR_FILES:
            continue
        if allowed_modules and name.startswith("modules/sonic-build-infra/"):
            continue
        raise ValueError("Unexpected change in source-only collector scope: " + name)
    if not allowed_modules:
        return {"include": []}
    if candidate_tree != CANDIDATE_TREE:
        raise ValueError("PR175 source-only candidate changed; review its action graph before updating scope")
    jobs = [job for job in matrix["include"]
            if job["module"] == "sonic-build-infra" and job["version"] == VERSION]
    if len(jobs) != 1 or jobs[0]["architecture"] != "amd64":
        raise ValueError("Expected the reviewed PR175 AMD64 source build and test matrix")
    return {"include": jobs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--branch", required=True, choices=sorted(BRANCHES))
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()

    def git(*arguments: str) -> str:
        return subprocess.check_output(["git", *arguments], text=True).strip()

    if git("rev-parse", "HEAD") != args.head:
        raise ValueError("Checkout differs from reviewed head")
    base = git("merge-base", args.base, args.head)
    changed = git("diff", "--name-only", "--no-renames", base, args.head).splitlines()
    tree = git("rev-parse", args.head + ":" + CANDIDATE) if args.branch.endswith("docbook-tools-registry") else None
    original = json.loads(args.plan.read_text())
    selected = select(original, changed, args.branch, tree)
    args.plan.with_name("unrestricted-plan.json").write_text(json.dumps(original, indent=2) + "\n")
    args.plan.write_text(json.dumps(selected, indent=2) + "\n")
    print("Temporary no-DEB scope: all AMD64/ARM64 runner tests remain enabled; "
          f"{len(selected['include'])} reviewed source-only module job(s).")


if __name__ == "__main__":
    main()
