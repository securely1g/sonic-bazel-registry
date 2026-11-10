"""Verify the large runner's cgroup limits and record observed GCC parallelism."""

import argparse
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys

SAMPLE_SECONDS = 3


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


def gcc_frontends(proc: Path, group: str) -> int:
    count = 0
    prefix = group.rstrip("/") + "/"
    for comm in proc.glob("[0-9]*/comm"):
        try:
            if comm.read_text().strip() in ("cc1", "cc1plus"):
                child = unified_cgroup(comm.with_name("cgroup"))
                if child == group or child.startswith(prefix):
                    count += 1
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            # A compiler can exit while /proc is being read.
            continue
    return count


def monitor(output: Path, command: list[str]) -> int:
    proc = Path("/proc")
    group = unified_cgroup(proc / "self/cgroup")
    cgroup_root = Path("/sys/fs/cgroup")
    limits = capacity(group, cgroup_root)
    cgroup = cgroup_root / group.lstrip("/")
    receipt = {"runner_label": "debian-trixie-container-large",
               **limits, "memory_before": memory_usage(cgroup),
               "bazel_jobs": 1, "recipe_make_jobs": 4, "sample_interval_seconds": SAMPLE_SECONDS,
               "samples": 0, "peak_observed_gcc_frontends": 0}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    if (receipt["cpu_quota_cores"] != 8 or receipt["cpu_affinity_count"] < 8
            or receipt["memory_limit_bytes"] != 16 * 1024**3):
        raise ValueError(f"Expected an 8 CPU / 16 GiB large runner; measured {receipt}")
    with subprocess.Popen(command) as process:
        while True:
            receipt["samples"] += 1
            receipt["peak_observed_gcc_frontends"] = max(receipt["peak_observed_gcc_frontends"],
                                                         gcc_frontends(proc, group))
            try:
                status = process.wait(timeout=SAMPLE_SECONDS)
                break
            except subprocess.TimeoutExpired:
                continue
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
        sys.exit(monitor(args.output, args.command))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Large runner resource check failed: {error}\n")
