"""Exercise libyang-Python and verify its native dependencies are runfiles."""

import json
import os
import sys
from pathlib import Path

import _cffi_backend
import _libyang
import libyang


SCHEMA = """
module libyang-python-registry-test {
  yang-version 1.1;
  namespace "urn:sonic:libyang-python-registry-test";
  prefix registry;
  container config {
    leaf source { type string; }
    leaf reference {
      type leafref { path "../source"; }
    }
    leaf count { type uint16; }
  }
}
"""


def declared_runfiles(wanted_names):
    root = Path(os.environ["TEST_SRCDIR"])
    declared = set()
    visited = set()
    for directory, subdirs, files in os.walk(root, followlinks=True):
        resolved_directory = Path(directory).resolve()
        if resolved_directory in visited:
            subdirs.clear()
            continue
        visited.add(resolved_directory)
        for name in files:
            if name in wanted_names or name.startswith("libyang.so."):
                declared.add((Path(directory) / name).resolve())
    return declared


def check_runtime():
    modules = {
        "libyang": Path(libyang.__file__).resolve(),
        "_libyang": Path(_libyang.__file__).resolve(),
        "_cffi_backend": Path(_cffi_backend.__file__).resolve(),
    }
    declared = declared_runfiles({path.name for path in modules.values()})
    for name, path in modules.items():
        if path not in declared:
            raise AssertionError(f"Imported {name} is not a declared runfile: {path}")
        print(f"Imported declared module {name}: {path}")

    loaded = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith("/"):
            loaded.add(Path(fields[5]).resolve())

    matches = {path for path in loaded if path.name.startswith("libyang.so.")}
    if len(matches) != 1:
        raise AssertionError(f"Expected one loaded libyang library, found {sorted(matches)}")
    library = matches.pop()
    if library not in declared:
        raise AssertionError(f"Loaded libyang is not a declared runfile: {library}")
    print(f"Loaded declared native library: {library}")


def check_consumer():
    expected = {
        "libyang-python-registry-test:config": {
            "source": "registered",
            "reference": "registered",
            "count": 7,
        }
    }
    with libyang.Context() as context:
        module = context.parse_module_str(SCHEMA)
        if module.name() != "libyang-python-registry-test":
            raise AssertionError(f"Unexpected parsed module: {module.name()}")

        targets = context.find_leafref_path_target_paths(
            "/libyang-python-registry-test:config/reference"
        )
        if targets != ["/libyang-python-registry-test:config/source"]:
            raise AssertionError(f"Unexpected patched leafref targets: {targets}")

        data = context.parse_data_mem(json.dumps(expected), "json", strict=True)
        if data is None:
            raise AssertionError("Parsing the consumer data returned no tree")
        try:
            actual = json.loads(data.print_mem("json", with_siblings=True))
            if actual != expected:
                raise AssertionError(f"Unexpected data roundtrip: {actual}")
        finally:
            data.free()
    print("Parsed a schema and data through the CFFI binding and patched leafref API")


def main():
    if sys.version_info[:2] != (3, 13):
        raise AssertionError(f"Expected CPython 3.13, got {sys.version}")
    if sys.implementation.name != "cpython":
        raise AssertionError(f"Expected CPython, got {sys.implementation.name}")
    check_runtime()
    check_consumer()


if __name__ == "__main__":
    main()
