"""Run the original suite against the direct installation in a declared APT runtime."""
import argparse
import base64
import csv
import email
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET


def child():
    import importlib.metadata
    import struct
    import cairo
    from tests import cmod
    root = Path(os.environ["PYCAIRO_INSTALLED"])
    assert Path(cairo.__file__).is_relative_to(root)
    assert isinstance(cmod.create_image_surface(), cairo.ImageSurface)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 3)
    context = cairo.Context(surface)
    context.set_source_rgb(1, 0, 0)
    context.paint()
    pixels = memoryview(surface.get_data())
    assert struct.unpack_from("=I", pixels)[0] == 0xffff0000
    png = io.BytesIO()
    surface.write_to_png(png)
    assert png.getvalue().startswith(b"\x89PNG\r\n\x1a\n")
    restored = cairo.ImageSurface.create_from_png(io.BytesIO(png.getvalue()))
    assert (restored.get_width(), restored.get_height()) == (2, 3)
    dist = importlib.metadata.distribution("pycairo")
    assert dist.version == "1.26.1"
    assert dist.metadata["Requires-Python"] == ">=3.8"
    assert not dist.requires
    source = Path(os.environ["PYCAIRO_SOURCE"])
    original = email.message_from_bytes((source / "PKG-INFO").read_bytes())
    for field in ["Name", "Version", "Summary", "Home-page", "Maintainer", "Maintainer-email", "License", "Project-URL", "Classifier", "Requires-Python", "License-File", "Requires-Dist"]:
        assert dist.metadata.get_all(field, []) == original.get_all(field, []), field
    assert dist.metadata.get_payload().strip() == (source / "README.rst").read_text().strip()
    metadata = json.loads(Path(os.environ["PYCAIRO_METADATA"]).read_text())
    assert metadata["distribution"] == original["Name"]
    assert metadata["version"] == original["Version"]
    assert metadata["requires_python"] == original["Requires-Python"]
    assert metadata["requires_dist"] == original.get_all("Requires-Dist", [])
    assert metadata["python_tag"] == metadata["abi"] == "cp%d%d" % sys.version_info[:2]
    import sysconfig
    assert metadata["platform"] == sysconfig.get_platform().replace("-", "_")
    wheel = email.message_from_string(dist.read_text("WHEEL"))
    assert wheel["Root-Is-Purelib"] == "false"
    assert wheel["Tag"] == "-".join(metadata[x] for x in ["python_tag", "abi", "platform"])
    installed_files = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    records = list(csv.reader(io.StringIO(dist.read_text("RECORD"))))
    assert len(records) == len(installed_files)
    seen = set()
    for name, digest, size in records:
        assert name and not Path(name).is_absolute()
        path = Path(dist.locate_file(name)).resolve()
        relative = str(path.relative_to(root))
        assert relative in installed_files and relative not in seen
        seen.add(relative)
        if relative == "pycairo-1.26.1.dist-info/RECORD":
            assert digest == size == ""
        else:
            assert digest and size, name
            algorithm, encoded = digest.split("=", 1)
            assert base64.urlsafe_b64encode(hashlib.new(algorithm, path.read_bytes()).digest()).rstrip(b"=").decode() == encoded, name
            assert path.stat().st_size == int(size)
    assert seen == installed_files
    source = Path(os.environ["PYCAIRO_SOURCE"])
    assert (root / "cairo/include/py3cairo.h").read_bytes() == (source / "cairo/py3cairo.h").read_bytes()
    for name in ["COPYING", "COPYING-LGPL-2.1", "COPYING-MPL-1.1"]:
        assert (root / "pycairo-1.26.1.dist-info/licenses" / name).read_bytes() == (source / name).read_bytes()
    # Every Cairo-dependent DSO must come from the declared package tree.
    runtime = Path(os.environ["PYCAIRO_APT_RUNTIME"])
    allowed = {p.resolve() for p in runtime.rglob("*") if p.is_file() and ".so" in p.name}
    allowed.add(Path(os.environ["PYCAIRO_CMOD"]).resolve())
    maps = Path("/proc/self/maps").read_text().splitlines()
    cairo_maps = [line.split()[-1] for line in maps if "libcairo.so" in line]
    assert cairo_maps
    for line in maps:
        path = line.split()[-1]
        if ".so" in path and path.startswith("/") and not Path(path).is_relative_to(root) and not Path(path).is_relative_to(Path.cwd()):
            assert Path(path).resolve() in allowed, path
    print("Installed import, C API, drawing, RECORD, license and declared-library checks passed", flush=True)
    import pytest
    args = ["tests", "-ra", "--junitxml=" + os.environ["XML_OUTPUT_FILE"]]
    return pytest.main(args)


def main():
    parser = argparse.ArgumentParser()
    for name in ["runtime", "archive", "metadata", "cmod", "source", "native", "patchelf"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    # Fontconfig resolves paths relative to its sysroot. Canonicalize Bazel
    # runfiles paths before supplying both the config filename and sysroot.
    runtime = args.runtime.resolve()
    source = args.source.absolute().parent
    output = Path(os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", tempfile.gettempdir()))
    with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as scratch:
        scratch = Path(scratch)
        with tarfile.open(args.archive) as archive:
            archive.extractall(scratch, filter="data")
        installed = scratch / "usr/local/lib/python3.13/dist-packages"
        tests = scratch / "tests"
        tests.mkdir()
        for p in (source / "tests").rglob("*"):
            relative = p.relative_to(source / "tests")
            dest = tests / relative
            if p.is_dir():
                dest.mkdir(exist_ok=True)
            else:
                dest.symlink_to(p)
        (tests / "cmod.so").symlink_to(args.cmod.absolute())
        # Test tools are pure-Python wheels from the declared hash lock.
        pip_paths = [p for p in sys.path if "site-packages" in p and Path(p).is_dir()]
        # Match the declared build-tools runtime's font isolation: use only
        # its fonts and a writable test-local cache, without host config paths.
        fontconfig = ET.Element("fontconfig")
        ET.SubElement(fontconfig, "dir").text = str(runtime / "usr/share/fonts")
        ET.SubElement(fontconfig, "cachedir").text = str(scratch / "font-cache")
        fontconfig_file = scratch / "fonts.conf"
        ET.ElementTree(fontconfig).write(fontconfig_file, encoding="utf-8", xml_declaration=True)
        env = {k: v for k, v in os.environ.items() if not k.startswith("LD_") and k != "FONTCONFIG_SYSROOT"}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHOME=str(runtime / "usr"), PYTHONPATH=os.pathsep.join([str(installed), str(scratch)] + pip_paths), PYTHONNOUSERSITE="1", PYCAIRO_INSTALLED=str(installed), PYCAIRO_SOURCE=str(source), PYCAIRO_APT_RUNTIME=str(runtime), PYCAIRO_CMOD=str(args.cmod.absolute()), PYCAIRO_METADATA=str(args.metadata.absolute()), PATH="", HOME=str(scratch), XDG_CACHE_HOME=str(scratch / "cache"), HYPOTHESIS_STORAGE_DIRECTORY=str(scratch / "hypothesis"), FONTCONFIG_PATH=str(scratch), FONTCONFIG_FILE=str(fontconfig_file))
        env.setdefault("XML_OUTPUT_FILE", str(output / "pytest.xml"))
        cmd = [str(runtime / "bin/python3"), str(Path(__file__).absolute()), "--child"]
        startup = subprocess.run([str(runtime / "bin/python3"), "--version"], cwd=scratch, env=env)
        startup.check_returncode()
        # Exercise the unmodified native build separately, then the installed
        # distribution, in the same declared target Python/library environment.
        native_code = "import importlib.util,sys;s=importlib.util.spec_from_file_location('_cairo',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);assert m.ImageSurface(m.FORMAT_ARGB32,2,3).get_height()==3;print('Native build-tree binding passed')"
        subprocess.run([str(runtime / "bin/python3"), "-c", native_code, str(args.native.absolute())], cwd=scratch, env=env, check=True)
        native_rpath = subprocess.check_output([str(args.patchelf.absolute()), "--print-rpath", str(args.native.absolute())], text=True).strip()
        installed_so = installed / "cairo/_cairo.cpython-313-x86_64-linux-gnu.so"
        installed_rpath = subprocess.check_output([str(args.patchelf.absolute()), "--print-rpath", str(installed_so)], text=True).strip()
        assert not installed_rpath, installed_rpath
        (output / "elf-search-paths.json").write_text(json.dumps({"native": native_rpath, "installed": installed_rpath}, indent=2)+"\n")
        status = subprocess.run(cmd, cwd=scratch, env=env).returncode
        (output / "installed-runtime.json").write_text(json.dumps({"exit": status, "command": cmd, "runtime": str(runtime), "source": str(source), "metadata_sha256": hashlib.sha256(args.metadata.read_bytes()).hexdigest(), "runtime_tar_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest()}, indent=2) + "\n")
        return status


if __name__ == "__main__":
    raise SystemExit(child() if sys.argv[1:] == ["--child"] else main())
