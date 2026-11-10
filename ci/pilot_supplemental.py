"""Keep the previous production fleet's compiler and output checks when main's routes change."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registry_ci import ROOT, RUNNERS, validate_entry


def supplemental_plan(primary, root=ROOT):
    indexed = {(job["module"], job["architecture"]): job for job in primary["include"]}
    jobs = []
    # These ARM modules previously compiled inside the ARM userspace on the pool.
    # Socat previously used the AMD64 cross compiler to produce and test ARM code.
    for module, cross in (("iproute2", False), ("p4c", False), ("rules_go", False),
                          ("sonic-sairedis", False), ("sonic-swss", False), ("socat", True)):
        job = indexed[module, "arm64"]
        if job["cross_compile"] == cross:
            continue
        jobs.append({**job, "cross_compile": cross, "execution_architecture": "amd64" if cross else "arm64",
                     "physical_architecture": "amd64", "runner": RUNNERS["amd64"], "emulated_arm": not cross,
                     "case": "arm-cross" if cross else "arm-guest"})

    # sflowtool 6.11.0.sonic.2 published its configure log as a checked AMD64 output.
    # The newer release still builds and tests the tool, but dropped this output.
    current = indexed["sflowtool", "amd64"]
    def checks_log(version):
        config = validate_entry(root, "sflowtool", version)
        targets = config["build_targets"] + config.get("additional_targets", {}).get("amd64", {}).get("build_targets", [])
        return "amd64" in config["architectures"] and "@sflowtool//:configure_log" in targets

    if not checks_log(current["version"]):
        previous = "6.11.0.sonic.2"
        if not checks_log(previous):
            raise ValueError("The historical sflowtool presubmit must check its configure_log")
        jobs.append({**current, "version": previous, "case": "legacy-output"})
    return {"include": jobs}


if __name__ == "__main__":
    matrix = supplemental_plan(json.loads(Path("plan.json").read_text()))
    Path("fleet-supplemental.json").write_text(json.dumps(matrix, indent=2) + "\n")
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        print("matrix=" + json.dumps(matrix, separators=(",", ":")), file=output)
        print("has_jobs=" + str(bool(matrix["include"])).lower(), file=output)
