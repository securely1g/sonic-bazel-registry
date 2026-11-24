#!/usr/bin/env python3
"""Focused regressions for signed kernel runtime/debug payloads."""
import hashlib
import lzma
import json
import os
import tarfile
import struct
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_kernel as stage
import kernel_arch


class StageKernelTest(unittest.TestCase):
    def test_signed_runtime_keeps_bytes_and_pairs_original_debug_by_build_id(self):
        for architecture in kernel_arch.ARCHITECTURES:
            with self.subTest(architecture=architecture), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                abi = kernel_arch.kernel_abi(architecture)
                runtime, debug = root / "runtime", root / "debug"
                kernel = debug / ("usr/lib/debug/boot/vmlinux-" + abi)
                kernel.parent.mkdir(parents=True)
                kernel.write_bytes(b"kernel debug")
                runtime_file = runtime / "usr/lib/modules" / abi / "kernel/test.ko.xz"
                runtime_file.parent.mkdir(parents=True)
                signed = b"runtime ELF~Module signature appended~\n"
                runtime_file.write_bytes(lzma.compress(signed))
                original_hash = hashlib.sha256(runtime_file.read_bytes()).hexdigest()
                debug_file = debug / "usr/lib/debug/lib/modules" / abi / "kernel/test.ko"
                debug_file.parent.mkdir(parents=True)
                debug_file.write_bytes(b"debug ELF")
                def inspect(path, selected):
                    self.assertEqual(selected, architecture)
                    if path.name.startswith("vmlinux"):
                        return "a" * 40, path == kernel
                    return "b" * 40, path == debug_file
                with patch.object(stage, "elf_info", side_effect=inspect), patch.object(stage, "materialize_kernel_elf") as boot:
                    result = stage.validate_debug_pairs(root / "source", runtime, debug, architecture)
                    self.assertEqual(boot.call_args.args[0], architecture)
                    self.assertEqual(result["module_count"], 1)
                    self.assertEqual(hashlib.sha256(runtime_file.read_bytes()).hexdigest(), original_hash)
                    link = debug / "usr/lib/debug/.build-id/bb" / ("b" * 38 + ".debug")
                    self.assertEqual(link.resolve(), debug_file)
                def mismatched(path, selected):
                    identity, has_debug = inspect(path, selected)
                    return ("c" * 40 if path == debug_file else identity), has_debug
                with patch.object(stage, "elf_info", side_effect=mismatched), patch.object(stage, "materialize_kernel_elf"):
                    with self.assertRaisesRegex(ValueError, "build ID or DWARF mismatch"):
                        stage.validate_debug_pairs(root / "source", runtime, debug, architecture)

    def test_arm64_boot_image_must_match_reconstructed_debug_vmlinux(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, symbols, output = root / "Image", root / "vmlinux.debug", root / "vmlinux"
            image.write_bytes(b"actual deployed raw ARM64 image")
            symbols.write_bytes(b"debug ELF")
            def objcopy(command, **kwargs):
                Path(command[-1]).write_bytes(b"actual deployed raw ARM64 image" if "binary" in command else b"stripped ELF probe")
            with patch.object(kernel_arch.subprocess, "run", side_effect=objcopy) as child:
                kernel_arch.materialize_kernel_elf("arm64", root, image, symbols, output)
                self.assertEqual(child.call_args_list[0].args[0], [
                    "objcopy", "-O", "binary", "-R", ".note", "-R", ".note.gnu.build-id",
                    "-R", ".comment", "-S", str(symbols), str(output) + ".Image",
                ])
                self.assertEqual(child.call_args_list[1].args[0], ["objcopy", "--strip-debug", str(symbols), str(output)])
                self.assertEqual(output.read_bytes(), b"stripped ELF probe")
                image.write_bytes(b"different kernel image")
                child.reset_mock()
                with self.assertRaisesRegex(ValueError, "boot Image and debug vmlinux bytes differ"):
                    kernel_arch.materialize_kernel_elf("arm64", root, image, symbols, output)
                self.assertEqual(child.call_count, 1)

    def test_amd64_keeps_embedded_elf_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def extract(command, **kwargs):
                kwargs["stdout"].write(b"embedded ELF")
            with patch.object(kernel_arch.subprocess, "run", side_effect=extract) as child:
                kernel_arch.materialize_kernel_elf("amd64", root, root / "vmlinuz", root / "debug", root / "vmlinux")
                self.assertEqual(child.call_args.args[0], ["sh", str(root / "scripts/extract-vmlinux"), str(root / "vmlinuz")])
                self.assertEqual((root / "vmlinux").read_bytes(), b"embedded ELF")

    def test_elf_machine_must_match_selected_kernel_architecture(self):
        names = b'\0.shstrtab\0.note.gnu.build-id\0.debug_info\0'
        note = struct.pack('<III', 4, 20, 3) + b'GNU\0' + bytes.fromhex('a' * 40)
        for architecture, machine, other in [('amd64', 62, 'arm64'), ('arm64', 183, 'amd64')]:
            with self.subTest(architecture=architecture), tempfile.TemporaryDirectory() as temporary:
                header = bytearray(64)
                header[:7] = b'\x7fELF\x02\x01\x01'
                struct.pack_into('<HHI', header, 16, 1, machine, 1)
                struct.pack_into('<Q', header, 40, 64)
                struct.pack_into('<H', header, 52, 64)
                struct.pack_into('<HHH', header, 58, 64, 4, 1)
                offset = 64 + 4 * 64
                sections = bytes(64)
                sections += struct.pack('<IIQQQQIIQQ', 1, 3, 0, 0, offset, len(names), 0, 0, 1, 0)
                sections += struct.pack('<IIQQQQIIQQ', names.index(b'.note'), 7, 0, 0, offset + len(names), len(note), 0, 0, 4, 0)
                sections += struct.pack('<IIQQQQIIQQ', names.index(b'.debug'), 1, 0, 0, offset + len(names) + len(note), 1, 0, 0, 1, 0)
                path = Path(temporary) / 'fixture'
                path.write_bytes(header + sections + names + note + b'\0')
                self.assertEqual(stage.elf_info(path, architecture), ('a' * 40, True))
                with self.assertRaisesRegex(ValueError, 'kernel artifact'):
                    stage.elf_info(path, other)

    def test_interpreter_reader_ignores_signed_modules_and_reads_native_executables(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tool"
            interpreter = b"/declared/runtime/ld-linux.so\0"
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            struct.pack_into("<H", header, 16, 2)
            struct.pack_into("<Q", header, 32, 64)
            struct.pack_into("<HH", header, 54, 56, 1)
            program = struct.pack("<IIQQQQQQ", 3, 4, 120, 0, 0, len(interpreter), len(interpreter), 1)
            path.write_bytes(header + program + interpreter)
            self.assertEqual(stage.elf_interpreter(path), interpreter[:-1].decode())
            struct.pack_into("<H", header, 16, 1)
            path.write_bytes(header + program + interpreter + b"~Module signature appended~")
            before = path.read_bytes()
            self.assertIsNone(stage.elf_interpreter(path))
            self.assertEqual(path.read_bytes(), before)

    def test_packaged_tools_restore_native_loader_and_preserve_nonprivate_rpath(self):
        for architecture, loader in [("amd64", "/lib64/ld-linux-x86-64.so.2"), ("arm64", "/lib/ld-linux-aarch64.so.1")]:
            with self.subTest(architecture=architecture), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                runtime, package = root / "runtime", root / "package"
                tool = package / "usr/lib/linux-kbuild/scripts/tool"
                tool.parent.mkdir(parents=True)
                tool.write_bytes(b"native host tool")
                module = package / "signed.ko"
                module.write_bytes(b"~Module signature appended~")
                inspections = {tool: iter([str(runtime / "ld.so"), loader])}
                def inspect(path):
                    return next(inspections[path]) if path in inspections else None
                with patch.object(stage, "elf_interpreter", side_effect=inspect), \
                        patch.object(stage.subprocess, "check_output", return_value=str(runtime / "usr/lib") + ":$ORIGIN/../lib\n"), \
                        patch.object(stage.subprocess, "run") as child:
                    self.assertEqual(stage.normalize_tools(package, architecture, runtime, Path("/declared/patchelf")), 1)
                    self.assertEqual(child.call_args.args[0], ["/declared/patchelf", "--set-interpreter", loader,
                                                              "--set-rpath", "$ORIGIN/../lib", str(tool)])
                self.assertEqual(module.read_bytes(), b"~Module signature appended~")

    def test_install_preserves_payload_modes_and_real_links_from_receipt(self):
        # Installation contract: cache-normalized files restore recorded modes;
        # real links keep their installation targets instead of sandbox targets.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tree, package = root / "tree", root / "package"
            source = tree / "lib/modules/release/real.ko"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"signed module")
            source.chmod(0o444)
            (source.parent / "alias.ko").symlink_to(source)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({"core_trees": {"runtime": [
                {"path": "lib/modules/release", "type": "directory", "mode": "0755"},
                {"path": "lib/modules/release/real.ko", "type": "file", "mode": "0640"},
                {"path": "lib/modules/release/alias.ko", "type": "symlink", "mode": "0777", "target": "real.ko"},
            ]}}))
            image = root / "image"
            image.write_bytes(b"boot image")
            spec = root / "spec.json"
            spec.write_text(json.dumps({"role": "runtime", "runtime_tree": str(tree),
                                        "receipt": str(receipt), "raw_files": {"image": str(image)}}))
            with patch.dict(os.environ, SONIC_KERNEL_INSTALL_CONFIG=str(spec)):
                stage.stage_install(package, "amd64")
            installed = package / "lib/modules/release/real.ko"
            self.assertEqual(installed.read_bytes(), b"signed module")
            self.assertEqual(installed.stat().st_mode & 0o777, 0o640)
            self.assertEqual(os.readlink(installed.with_name("alias.ko")), "real.ko")
            self.assertEqual((package / "boot" / ("vmlinuz-" + kernel_arch.kernel_abi())).read_bytes(), b"boot image")

    def test_export_preserves_control_scripts_and_excludes_them_from_data(self):
        # Debian installation interface exports payload and package control apart.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            control = package / "DEBIAN"
            control.mkdir(parents=True)
            (package / "payload").write_bytes(b"payload")
            (control / "control").write_text("Package: linux-headers-test\n")
            (control / "md5sums").write_text("fixture checksum\n")
            script = control / "postinst"
            script.write_text("#!/bin/sh\nexit 0\n")
            script.chmod(0o755)
            outputs = {key: str(root / key) for key in ("data", "control_tar", "control")}
            outputs["control_files"] = {"postinst": str(root / "postinst")}
            spec = root / "spec.json"
            spec.write_text(json.dumps({"role": "headers", "install_outputs": outputs}))
            with patch.dict(os.environ, SONIC_KERNEL_INSTALL_CONFIG=str(spec), SOURCE_DATE_EPOCH="123"):
                stage.export_install(package, "amd64")
            with tarfile.open(outputs["data"]) as archive:
                self.assertEqual(archive.getnames(), ["./payload"])
                self.assertEqual(archive.extractfile("./payload").read(), b"payload")
                self.assertEqual(archive.getmember("./payload").uid, 0)
            with tarfile.open(outputs["control_tar"]) as archive:
                self.assertEqual(archive.getmember("./postinst").mode, 0o755)
                self.assertIn("./md5sums", archive.getnames())
            self.assertEqual(Path(outputs["control"]).read_text(), "Package: linux-headers-test\n")
            self.assertEqual((root / "postinst").stat().st_mode & 0o777, 0o755)


if __name__ == "__main__":
    unittest.main()
