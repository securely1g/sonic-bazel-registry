"""Exercise the original registry pipeline with the job-local #92 executor."""
import hashlib
import json
import sys
from pathlib import Path

ci = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ci))
import registry_ci

scope = sys.argv.pop(1)
assert scope in ("four", "all")
assert sys.argv[1] == "run"
assert sys.argv[sys.argv.index("--module") + 1] == "sonic-swss-common"
assert sys.argv[sys.argv.index("--version") + 1] == "0.0.9-334389eae54afd1f4f5ee69f89c3a7ad2062ee61"
guest = Path(sys.argv[sys.argv.index("--test-executor") + 1])
proot = guest.with_name("proot")
assert proot.exists() and 'iproute2-arm-executor/bin/' in str(guest)
assert str(proot.resolve()) in guest.read_text()
registry_ci.ARM_DECLARED_RUNTIME_FIXTURES.clear()

labels = {
    "@sonic-swss-common//dist:libswsscommon_package_test",
    "@sonic-swss-common//goext:swsscommon_runtime_test",
    "@sonic-swss-common//goext/tests/hiredis:hiredis_cgo_test",
    "@sonic-swss-common//goext/tests/gnmi:alias_test",
}
validate = registry_ci.validate_entry
if scope == "four":
    def focused_contract(*args, **kwargs):
        contract = validate(*args, **kwargs)
        selected = [target for target in contract["test_targets"] if target in labels]
        assert set(selected) == labels and len(selected) == 4
        return {**contract, "test_targets": selected}
    registry_ci.validate_entry = focused_contract

artifacts = Path(sys.argv[sys.argv.index("--artifacts") + 1])
artifacts.mkdir(parents=True, exist_ok=True)
receipt = {
    "scope": scope, "declared_fixture_overrides": registry_ci.ARM_DECLARED_RUNTIME_FIXTURES,
    "manager_pr": 92, "executor_sha256": hashlib.sha256(guest.read_bytes()).hexdigest(),
    "proot_sha256": hashlib.sha256(proot.read_bytes()).hexdigest(),
    "source_head": "59d7043e256f0933970e1bc8e96acde232fba578",
    "focused_labels": sorted(labels),
}
(artifacts / "executor-diagnostic.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt), flush=True)
raise SystemExit(registry_ci.main())
