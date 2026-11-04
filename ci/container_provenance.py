"""Explicit local-base/provisioner identity for disposable registry test jobs.

This is observed configuration provenance, not an OCI manifest or attestation.
No path or command is taken from the expected identity or installed marker.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat

KIND = "local_base_config_and_provisioner"
PREFIX = "sonic-worker-base-config-provisioner-v1:sha256:"
MARKER = Path("/etc/sonic-slave-github-runner.json")
HELPER_ROOT = Path("/opt/sonic-runner")
HELPERS = ("cache_credentials.py", "cache_probe.py", "entrypoint.py")


class ProvenanceError(ValueError):
    """A fixed provenance contract was not satisfied."""


def require(value, message):
    if not value:
        raise ProvenanceError(message)


def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected), "Invalid provenance object keys")


def integer(value, expected):
    require(type(value) is int and value == expected, "Invalid provenance integer")


def matching(value, pattern):
    require(type(value) is str and re.fullmatch(pattern, value) is not None,
            "Invalid provenance string")


def parse(content):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate provenance JSON key")
            result[key] = value
        return result
    try:
        return json.loads(content, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ProvenanceError("Invalid provenance JSON number")))
    except (UnicodeError, ValueError) as error:
        raise ProvenanceError("Invalid provenance JSON") from error


def file_record(value, mode, maximum):
    keys(value, ("bytes", "gid", "mode", "sha256", "uid"))
    require(type(value["bytes"]) is int and 0 < value["bytes"] <= maximum,
            "Invalid provenance file size")
    for name, expected in (("uid", 0), ("gid", 0), ("mode", mode)):
        integer(value[name], expected)
    matching(value["sha256"], r"[0-9a-f]{64}")


def marker_fields(value):
    keys(value, ("uid", "gid", "runner_root", "work_root", "base_image",
                 "manager_revision", "runner_version"))
    integer(value["uid"], 1000)
    integer(value["gid"], 1000)
    require(type(value["runner_root"]) is str and value["runner_root"] == "/opt/actions-runner"
            and type(value["work_root"]) is str and value["work_root"] == "/actions/_work",
            "Invalid worker directories")
    matching(value["base_image"], r"sha256:[0-9a-f]{64}")
    matching(value["manager_revision"], r"[0-9a-f]{40}")
    matching(value["runner_version"], r"[0-9]+[.][0-9]+[.][0-9]+")


def validate_identity(value):
    keys(value, ("schema", "kind", "scope", "architecture", "distribution", "marker",
                 "marker_file", "installed_provisioner_helpers",
                 "registry_manifest_digest_verified", "derived_image_digest_verified"))
    integer(value["schema"], 1)
    for name, expected in (("kind", KIND), ("scope", "base_config_and_provisioner_only"),
                           ("architecture", "amd64"), ("distribution", "debian-trixie")):
        require(type(value[name]) is str and value[name] == expected, "Invalid provenance type or scope")
    require(value["registry_manifest_digest_verified"] is False
            and value["derived_image_digest_verified"] is False,
            "Local provenance cannot claim an image digest")
    marker_fields(value["marker"])
    file_record(value["marker_file"], 0o444, 65536)
    keys(value["installed_provisioner_helpers"], HELPERS)
    for item in value["installed_provisioner_helpers"].values():
        file_record(item, 0o555, 1024 * 1024)
    return value


def reference(identity):
    validate_identity(identity)
    return PREFIX + hashlib.sha256(json.dumps(
        identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _directory(path):
    """Walk every component with no-follow; return an owned descriptor."""
    require(path.is_absolute() and ".." not in path.parts, "Expected an absolute confined path")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            next_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _signature(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
            value.st_ctime_ns, value.st_mode, value.st_uid, value.st_gid, value.st_nlink)


def read_file(path, maximum, mode, private=False):
    parent = _directory(path.parent)
    try:
        directory = os.fstat(parent)
        require(directory.st_uid == directory.st_gid == 0
                and (stat.S_IMODE(directory.st_mode) == 0o700 if private
                     else not directory.st_mode & 0o022), "Unsafe provenance parent")
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 0
                    and stat.S_IMODE(before.st_mode) == mode and before.st_nlink == 1,
                    "Unsafe provenance file metadata")
            require(0 < before.st_size <= maximum, "Provenance file size exceeded")
            content = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        current_parent = _directory(path.parent)
        try:
            current_directory = os.fstat(current_parent)
            current = os.stat(path.name, dir_fd=current_parent, follow_symlinks=False)
            require((directory.st_dev, directory.st_ino, directory.st_uid, directory.st_gid,
                     directory.st_mode) ==
                    (current_directory.st_dev, current_directory.st_ino, current_directory.st_uid,
                     current_directory.st_gid, current_directory.st_mode),
                    "Provenance parent changed while reading")
            require(len(content) == before.st_size and _signature(before) == _signature(after)
                    and _signature(after) == _signature(named) == _signature(current),
                    "Provenance file changed while reading")
        finally:
            os.close(current_parent)
        return content, {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                         "uid": before.st_uid, "gid": before.st_gid, "mode": stat.S_IMODE(before.st_mode)}
    finally:
        os.close(parent)


def require_container():
    # These are the original runtime guards; typed mode additionally has a fixed
    # AMD64 slave profile. The qualified-image path in registry_ci stays exact.
    require(os.geteuid() == 0 and any(Path(p).exists() for p in ("/.dockerenv", "/run/.containerenv")),
            "Typed runtime preparation requires real disposable container root")
    release = Path("/etc/os-release").read_text().splitlines()
    require("VERSION_CODENAME=trixie" in release and "ID=debian" in release,
            "Typed runtime preparation requires Debian Trixie")
    require(platform.system() == "Linux" and platform.machine() == "x86_64",
            "Typed runtime preparation requires native AMD64")


def measure():
    require_container()
    content, record = read_file(MARKER, 65536, 0o444)
    raw = parse(content)
    required = {"uid", "gid", "runner_root", "work_root", "base_image", "base_image_ref",
                "manager_revision", "runner_version"}
    require(type(raw) is dict and required.issubset(raw), "Invalid installed marker profile")
    # Preserve the diagnostic reader whitelist; any additional marker bytes are
    # hash-bound to the reviewed expected file, never serialized or executed.
    matching(raw["base_image_ref"], r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,511}")
    require("://" not in raw["base_image_ref"], "Invalid recorded base reference")
    marker = {key: raw[key] for key in required if key != "base_image_ref"}
    marker_fields(marker)
    helpers = {}
    for name in HELPERS:
        _, helpers[name] = read_file(HELPER_ROOT / name, 1024 * 1024, 0o555)
    return validate_identity({
        "schema": 1, "kind": KIND, "scope": "base_config_and_provisioner_only",
        "architecture": "amd64", "distribution": "debian-trixie", "marker": marker,
        "marker_file": record, "installed_provisioner_helpers": helpers,
        "registry_manifest_digest_verified": False, "derived_image_digest_verified": False})


class Session:
    """Retain bounded proof even on failure, and reject changed live identity."""
    def __init__(self, expected_path, work_dir, artifacts):
        self.path = Path(expected_path)
        # The input is a sibling of the fresh empty Bazel work directory, in the
        # same root-owned0700 per-run directory. It cannot be any caller-chosen path.
        self.work_dir = work_dir.absolute()
        self.required_path = self.work_dir.parent / "expected-provenance.json"
        self.artifacts = artifacts
        self.expected_bytes = None
        self.identity = None
        self.receipt = {"schema": 1, "kind": KIND, "scope": "base_config_and_provisioner_only",
                        "status": "pending", "checks": [], "registry_manifest_digest_verified": False,
                        "derived_image_digest_verified": False}

    def save(self):
        (self.artifacts / "test-container-provenance.json").write_text(
            json.dumps(self.receipt, indent=2, sort_keys=True) + "\n")

    def check(self, stage):
        require(stage in ("before_build", "before_preparation", "after_preparation"),
                "Invalid provenance stage")
        self.receipt["stage"] = stage
        try:
            require_container()
            require(self.path.is_absolute() and self.path == self.required_path
                    and ".." not in self.path.parts and ".." not in self.work_dir.parts
                    and self.work_dir.resolve() == self.work_dir, "Expected provenance must stay in the private run directory")
            content, record = read_file(self.path, 65536, 0o400, private=True)
            expected = validate_identity(parse(content))
            if self.expected_bytes is None:
                self.expected_bytes = content
                self.identity = expected
                self.receipt.update(expected_sha256=record["sha256"], identity=expected,
                                    reference=reference(expected))
                (self.artifacts / "test-container-provenance.expected.json").write_bytes(content)
            require(content == self.expected_bytes, "Expected provenance changed after admission")
            actual = measure()
            require(actual == self.identity, "Live provenance differs from reviewed identity")
            self.receipt["checks"].append({"stage": stage, "status": "passed", "measured": actual})
            self.save()
            return self.receipt["reference"]
        except (OSError, ValueError, TypeError) as error:
            self.receipt.update(status="failed", failed_stage=stage, error_class=type(error).__name__)
            self.save()
            raise

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        self.finish(error_type is not None)

    def finish(self, failed):
        if self.receipt["status"] != "failed":
            self.receipt["status"] = "failed" if failed else "passed"
        self.save()
