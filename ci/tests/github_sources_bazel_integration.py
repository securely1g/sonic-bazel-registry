#!/usr/bin/env python3
"""Prove that Bazel 8.5.1 reuses verified distdir files with downloads disabled.

This manual integration check never fetches sources or executes their contents.
It uses an isolated WORKSPACE repository rule containing only ctx.download and
ctx.file. Bzlmod is disabled so registry metadata cannot bypass the repository
download switch. The supplied distdir is read only; each scenario has a fresh
output base and repository cache. Evidence remains in the new work directory.
Local no-op configuration repositories satisfy Bazel's injected WORKSPACE
toolchain loads; this proof does not use or validate language toolchains.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit


BASENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+@~-]{0,254}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
RULE = '''def _download(ctx):
    ctx.download(url = ctx.attr.url, output = "payload", sha256 = ctx.attr.sha256)
    ctx.file("BUILD.bazel", 'exports_files(["payload"])\\n')

pinned_file = repository_rule(
    implementation = _download,
    attrs = {"url": attr.string(mandatory = True), "sha256": attr.string(mandatory = True)},
)
'''
BOOTSTRAP = {
    "rules_cc": {
        "cc/private/toolchain/cc_configure.bzl": "def cc_configure():\n    pass\n",
        "cc/toolchains/toolchain_config_utils.bzl": "MSVC_ENVVARS = []\n",
    },
    "rules_java": {
        "java/rules_java_deps.bzl": "def rules_java_dependencies():\n    pass\n",
        "java/repositories.bzl": "def rules_java_toolchains():\n    pass\n",
    },
    "bazel_features": {"deps.bzl": "def bazel_features_deps():\n    pass\n"},
    "rules_python": {"python/repositories.bzl": "def py_repositories():\n    pass\n"},
    "com_google_protobuf": {"protobuf_deps.bzl": "def protobuf_deps():\n    pass\n"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    require(len(raw) <= 1024 * 1024, "JSON input exceeds 1 MiB")
    return json.loads(raw, object_pairs_hook=unique)


def selected_files(manifest):
    require(isinstance(manifest, dict) and type(manifest.get("schema_version")) is int
            and manifest["schema_version"] == 1,
            "Expected a version 1 GitHub sources manifest")
    require(isinstance(manifest.get("sources"), list) and manifest["sources"],
            "Manifest must select sources")
    files = []
    names = set()
    for source in manifest["sources"]:
        require(isinstance(source, dict) and isinstance(source.get("files"), list)
                and source["files"], "Each source must select files")
        for item in source["files"]:
            require(isinstance(item, dict), "Invalid selected file")
            name, size, sha256 = item.get("name"), item.get("size"), item.get("sha256")
            require(isinstance(name, str) and BASENAME.fullmatch(name) and name not in names,
                    "File names must be safe, unique basenames")
            require(type(size) is int and size > 0, "File size must be a positive integer")
            require(isinstance(sha256, str) and SHA256.fullmatch(sha256), "Invalid SHA256")
            names.add(name)
            files.append({"name": name, "size": size, "sha256": sha256})
    return files


def original_urls(files, mapping):
    names = {item["name"] for item in files}
    require(isinstance(mapping, dict) and set(mapping) == names,
            "URL mapping must name exactly the selected files")
    for name, url in mapping.items():
        require(isinstance(url, str) and not any(ord(char) < 33 for char in url),
                "Invalid original URL")
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError:
            raise ValueError("Invalid original URL") from None
        require(parsed.scheme == "https" and parsed.hostname and parsed.username is None
                and parsed.password is None and port is None
                and not parsed.query and not parsed.fragment,
                "Original URLs must use HTTPS without credentials, ports or query strings")
        require(unquote(parsed.path.rsplit("/", 1)[-1]) == name,
                "Original URL basename must match the distdir file")
    return mapping


def verify_file(path, expected):
    require(path.is_file() and not path.is_symlink(), "Expected a regular nonsymlink payload")
    require(path.stat().st_size == expected["size"] and digest(path) == expected["sha256"],
            "Payload size or SHA256 mismatch")


def minimal_environment():
    # Do not inherit API tokens, proxies, Java options, Bazel flags or shell hooks.
    # Preserve HOME's existing value rather than changing the user's home.
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    for key in ("HOME", "USER", "LOGNAME", "TMPDIR"):
        if key in os.environ:
            environment[key] = os.environ[key]
    return environment


def execute(command, cwd, directory, environment, timeout=120):
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        # This group belongs only to this invocation, including its batch JVM.
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    (directory / "stdout.log").write_bytes(stdout)
    (directory / "stderr.log").write_bytes(stderr)
    (directory / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    require(not timed_out, "Bazel fixture exceeded its timeout; safe diagnostics retained locally")
    return process.returncode, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace"), round(time.monotonic() - started, 3)


def scenario(bazel, work, case, files, urls, distdir, environment):
    directory = work / case
    directory.mkdir()
    workspace = directory / "workspace"
    workspace.mkdir()
    (workspace / "fixture.bzl").write_text(RULE)
    (workspace / "BUILD.bazel").write_text("")
    definitions = ['workspace(name = "github_distdir_probe")']
    # Bazel's default WORKSPACE suffix loads these macros even for a plain
    # exported-file query. Stub only unused toolchain setup, never downloads.
    for name, contents in BOOTSTRAP.items():
        repository = directory / "bootstrap" / name
        repository.mkdir(parents=True)
        (repository / "WORKSPACE.bazel").write_text("workspace(name = %s)\n" % json.dumps(name))
        for relative, content in contents.items():
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            (path.parent / "BUILD.bazel").write_text("")
            path.write_text(content)
        definitions.append("local_repository(name = %s, path = %s)" % (
            json.dumps(name), json.dumps(str(repository))))
    definitions.append('load(":fixture.bzl", "pinned_file")')
    for index, item in enumerate(files):
        definitions.append("pinned_file(name = %s, url = %s, sha256 = %s)" % (
            json.dumps(f"verified_input_{index}"), json.dumps(urls[item["name"]]),
            json.dumps(item["sha256"])))
    (workspace / "WORKSPACE.bazel").write_text("\n".join(definitions) + "\n")
    output_base = directory / "output-base"
    command = [str(bazel), "--ignore_all_rc_files", "--batch", "--host_jvm_args=-Xmx512m",
               f"--install_base={work / 'bazel-install'}",
               f"--output_user_root={directory / 'output-user-root'}",
               f"--output_base={output_base}", "query",
               "set(" + " ".join(f"@verified_input_{i}//:payload" for i in range(len(files))) + ")",
               "--enable_workspace", "--noenable_bzlmod", "--repository_disable_download",
               "--incompatible_autoload_externally=",
               f"--repository_cache={directory / 'repository-cache'}", f"--distdir={distdir}",
               "--noshow_progress", "--color=no", "--curses=no"]
    code, stdout, stderr, seconds = execute(command, workspace, directory, environment)
    if case == "positive":
        require(code == 0, "Positive Bazel query failed; inspect its local stderr.log")
        outputs = []
        for index, item in enumerate(files):
            path = output_base / "external" / f"verified_input_{index}" / "payload"
            verify_file(path, item)
            outputs.append({**item, "path": str(path)})
        return {"status": "passed", "exit_code": code, "seconds": seconds, "outputs": outputs}
    require(code != 0 and "download is disabled" in stderr,
            "Missing/corrupt input did not fail specifically because downloads are disabled")
    return {"status": "passed", "exit_code": code, "seconds": seconds,
            "expected_failure": "download is disabled", "input": files[0]["name"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bazel", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--distdir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--urls-json", type=Path,
                        help="Optional basename-to-original-HTTPS-URL map; no URLs are fetched")
    args = parser.parse_args()
    try:
        bazel, manifest, distdir = (path.resolve(strict=True) for path in
                                   (args.bazel, args.manifest, args.distdir))
        work = args.work_dir.resolve()
        require(bazel.is_file() and os.access(bazel, os.X_OK), "Bazel must be an executable file")
        require(distdir.is_dir(), "distdir must be a directory")
        require(not work.is_relative_to(distdir) and not distdir.is_relative_to(work),
                "work-dir and the input distdir must not overlap")
        require(not work.exists() or (work.is_dir() and not any(work.iterdir())),
                "work-dir must be new or empty")
        manifest_sha256 = digest(manifest)
        files = selected_files(read_json(manifest))
        require(digest(manifest) == manifest_sha256, "Manifest changed while reading")
        urls = original_urls(files, read_json(args.urls_json) if args.urls_json else
                             {item["name"]: "https://example.invalid/" + item["name"] for item in files})
        for item in files:
            verify_file(distdir / item["name"], item)
        work.mkdir(parents=True, exist_ok=True)
        environment = minimal_environment()
        version_dir = work / "version"
        version_dir.mkdir()
        code, stdout, _stderr, _seconds = execute([str(bazel), "--version"], work, version_dir,
                                                 environment, timeout=30)
        require(code == 0 and stdout.strip() == "bazel 8.5.1", "This integration check requires Bazel 8.5.1")
        result = {"status": "incomplete", "bazel_version": stdout.strip(), "bazel_sha256": digest(bazel),
                  "manifest_sha256": manifest_sha256, "original_urls": urls,
                  "scope": "ctx.download distdir reuse; no payload execution or full build claim",
                  "unused_toolchain_configuration": "local no-op WORKSPACE repositories",
                  "repository_downloads_disabled": True, "bzlmod_disabled": True, "scenarios": {}}
        receipt = work / "integration.json"
        try:
            result["scenarios"]["positive"] = scenario(bazel, work, "positive", files, urls, distdir, environment)
            smallest = min(files, key=lambda item: item["size"])
            for case in ("missing", "corrupt"):
                selected = work / (case + "-distdir")
                selected.mkdir()
                if case == "corrupt":
                    path = selected / smallest["name"]
                    shutil.copyfile(distdir / smallest["name"], path)
                    with path.open("r+b") as stream:
                        byte = stream.read(1)
                        stream.seek(0)
                        stream.write(bytes([byte[0] ^ 1]))
                result["scenarios"][case] = scenario(bazel, work, case, [smallest], urls, selected, environment)
            for item in files:
                verify_file(distdir / item["name"], item)
            require(digest(manifest) == manifest_sha256, "Manifest changed during validation")
            result["input_distdir_unchanged"] = True
            result["status"] = "passed"
        finally:
            receipt.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": "passed", "files_verified": len(files), "scenarios": 3,
                          "receipt": str(receipt)}))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"GitHub distdir integration failed: {error}\n")


if __name__ == "__main__":
    main()
