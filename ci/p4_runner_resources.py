"""Verify the large runner's cgroup limits and record local foreign-build CPU usage."""

import argparse
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys

FOREIGN_MAKE_ACTIONS = {"CcCmakeMakeRule", "CcConfigureMakeRule", "CcMakeRule"}


def unified_cgroup(path: Path) -> str:
    for line in path.read_text().splitlines():
        if line.startswith("0::/"):
            return line[3:]
    raise ValueError("The large Trixie runner requires a unified cgroup v2 hierarchy")


def capacity(group: str, root: Path) -> dict:
    """The tightest enclosing CPU and memory limits govern this job."""
    parts = Path(group).parts
    if not parts or parts[0] != "/" or ".." in parts:
        raise ValueError("Invalid cgroup path")
    directory = root.joinpath(*parts[1:])
    if not directory.is_dir():
        raise ValueError("Runner cgroup is not available under /sys/fs/cgroup")
    cpus = []
    memory = []
    while True:
        if (directory / "cpu.max").is_file():
            quota, period = (directory / "cpu.max").read_text().split()
            if quota != "max":
                cpus.append(Fraction(int(quota), int(period)))
        if (directory / "memory.max").is_file():
            limit = (directory / "memory.max").read_text().strip()
            if limit != "max":
                memory.append(int(limit))
        if directory == root:
            break
        directory = directory.parent
    return {
        "cpu_quota_cores": float(min(cpus)) if cpus else None,
        "cpu_affinity_count": len(os.sched_getaffinity(0)),
        "memory_limit_bytes": min(memory) if memory else None,
    }


def memory_usage(cgroup: Path) -> dict:
    usage = {}
    peak = cgroup / "memory.peak"
    if peak.is_file():
        usage["peak_bytes"] = int(peak.read_text())
    events = cgroup / "memory.events"
    if events.is_file():
        counters = dict(line.split() for line in events.read_text().splitlines())
        usage["events"] = {key: int(counters[key]) for key in ("max", "oom", "oom_kill", "oom_group_kill")
                           if key in counters}
    return usage


def local_foreign_cpu(summary: dict) -> dict:
    """Bazel aggregates spawned CPU by mnemonic; its action counts include cache hits."""
    runners = [runner for runner in summary.get("runnerCount", []) if int(runner.get("count", 0)) > 0]
    if not any(runner.get("execKind") == "Local" for runner in runners):
        return {"status": "no_local_execution"}
    for runner in runners:
        if runner["name"] == "deduplicated" or (
                runner.get("execKind") != "Local" and runner["name"] not in ("total", "internal")
                and not runner["name"].endswith(" cache hit")):
            return {"status": "unattributed_execution"}

    groups = []
    for action in summary.get("actionData", []):
        if action["mnemonic"] not in FOREIGN_MAKE_ACTIONS:
            continue
        group = {"mnemonic": action["mnemonic"], "reported_actions": int(action.get("actionsExecuted", 0))}
        # Cache hits do not report local spawn CPU. Bazel can also omit a mnemonic from its top-N summary.
        cpu = sum(float(action.get(key, "0s").removesuffix("s")) for key in ("userTime", "systemTime"))
        start_ms = int(action.get("firstStartedMs", 0))
        elapsed_ms = int(action.get("lastEndedMs", 0)) - start_ms
        if cpu > 0 and start_ms > 0 and elapsed_ms > 0:
            group.update(cpu_seconds=round(cpu, 6), elapsed_span_seconds=elapsed_ms / 1000,
                         average_cores=round(cpu * 1000 / elapsed_ms, 3))
        groups.append(group)
    return {"status": "reported" if any("average_cores" in group for group in groups) else "no_cpu_measurement",
            "groups": groups}


def foreign_cpu(events: Path) -> dict:
    try:
        with events.open("rb") as stream:
            for line in stream:
                if b'"buildMetrics"' in line:
                    metrics = json.loads(line).get("buildMetrics")
                    if metrics and "actionSummary" in metrics:
                        return local_foreign_cpu(metrics["actionSummary"])
    except (OSError, AttributeError, KeyError, TypeError, ValueError):
        # A failed or interrupted Bazel command may have only partial build events.
        pass
    return {"status": "missing_metrics"}


def run(output: Path, command: list[str]) -> int:
    proc = Path("/proc")
    group = unified_cgroup(proc / "self/cgroup")
    cgroup_root = Path("/sys/fs/cgroup")
    limits = capacity(group, cgroup_root)
    cgroup = cgroup_root / group.lstrip("/")
    receipt = {"runner_label": "debian-trixie-container-large",
               **limits, "memory_before": memory_usage(cgroup),
               "bazel_jobs": 1, "recipe_make_jobs": 4}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    if (receipt["cpu_quota_cores"] != 8 or receipt["cpu_affinity_count"] < 8
            or receipt["memory_limit_bytes"] != 16 * 1024**3):
        raise ValueError(f"Expected an 8 CPU / 16 GiB large runner; measured {receipt}")
    status = subprocess.run(command).returncode
    receipt["foreign_build_cpu"] = {phase: foreign_cpu(output.parent / f"{phase}-events.jsonl")
                                    for phase in ("build", "test")}
    receipt["exit_code"] = status
    receipt["memory_after"] = memory_usage(cgroup)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print("Large runner evidence:", json.dumps(receipt, sort_keys=True), flush=True)
    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command:
        parser.error("a command to monitor is required")
    try:
        sys.exit(run(args.output, args.command))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Large runner resource check failed: {error}\n")
