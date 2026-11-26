#!/usr/bin/env python3
"""Check input identity and Debian package handoff without compiling a sample kernel."""

import hashlib
import io
import gzip
import tarfile
import json
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel_action as action
import verify_install


class KernelActionTest(unittest.TestCase):
    def test_installed_arm64_package_requires_device_trees_for_its_abi(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            verify_install.verify_device_trees(root, "amd64")
            wrong = root / "usr/lib/linux-image-wrong-abi/vendor/board.dtb"
            wrong.parent.mkdir(parents=True)
            wrong.write_bytes(b"wrong ABI")
            with self.assertRaisesRegex(ValueError, "device trees for its ABI"):
                verify_install.verify_device_trees(root, "arm64")
            native = root / "usr/lib" / ("linux-image-" + action.kernel_abi("arm64")) / "vendor/board.dtb"
            native.parent.mkdir(parents=True)
            native.write_bytes(b"native device tree")
            verify_install.verify_device_trees(root, "arm64")

    def test_source_identity_ignores_path_but_tracks_content_and_executable_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            first.write_text("same content")
            second.write_text("same content")
            inventory = lambda path: action.source_inventory([{"name": "manage-config", "path": str(path)}])
            self.assertEqual(action.source_tree_sha256(inventory(first)), action.source_tree_sha256(inventory(second)))
            second.chmod(0o755)
            self.assertNotEqual(action.source_tree_sha256(inventory(first)), action.source_tree_sha256(inventory(second)))
            second.chmod(0o644)
            second.write_text("changed configuration")
            self.assertNotEqual(action.source_tree_sha256(inventory(first)), action.source_tree_sha256(inventory(second)))

    def test_source_paths_cannot_escape_or_collide(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input"
            path.write_text("source")
            for name in ("../escape", "/absolute"):
                with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                    action.source_inventory([{"name": name, "path": str(path)}])
            with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                action.source_inventory([{"name": "same", "path": str(path)}] * 2)

    def test_source_identity_reads_readonly_sandbox_links_without_changing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            source.write_text("source")
            source.chmod(0o444)
            alias = root / "link"
            alias.symlink_to(source)
            inventory = lambda path: action.source_inventory([
                {"name": "config.local/test", "path": str(path)}])
            self.assertEqual(inventory(alias), inventory(source))
            self.assertTrue(alias.is_symlink())
            self.assertEqual(source.read_text(), "source")
            self.assertEqual(source.stat().st_mode & 0o777, 0o444)

    def test_runtime_requires_matching_architecture_and_input_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for architecture in action.ARCHITECTURES:
                with self.subTest(architecture=architecture):
                    inputs = ["a" * 64, "b" * 64]
                    identity = hashlib.sha256(json.dumps({"architecture": architecture, "inputs": inputs},
                                                         sort_keys=True).encode()).hexdigest()
                    marker = {"schema_version": 1, "kind": "debian-build-tools", "architecture": architecture,
                              "execution": "relocatable",
                              "identity_sha256": identity, "input_sha256": inputs, "packages": {"make": "4.4.1"}}
                    (root / "kernel-runtime.json").write_text(json.dumps(marker))
                    self.assertEqual(action.runtime_identity(root, architecture), marker)
                    other = "arm64" if architecture == "amd64" else "amd64"
                    with self.assertRaisesRegex(ValueError, "must execute on " + other.upper()):
                        action.runtime_identity(root, other)
                    marker["input_sha256"][0] = "c" * 64
                    marker["input_sha256"].sort()
                    (root / "kernel-runtime.json").write_text(json.dumps(marker))
                    with self.assertRaisesRegex(ValueError, "identity digest"):
                        action.runtime_identity(root, architecture)

    def test_runtime_extra_cross_tools_do_not_restrict_selected_kernel_target(self):
        inputs = ["a" * 64]
        marker = {
            "schema_version": 1, "kind": "debian-build-tools", "architecture": "amd64",
            "cross_architectures": ["arm64", "armhf"], "execution": "relocatable",
            "identity_sha256": hashlib.sha256(json.dumps(
                {"architecture": "amd64", "inputs": inputs}, sort_keys=True).encode()).hexdigest(),
            "input_sha256": inputs, "packages": {"make": "4.4.1"},
        }
        for target in ("amd64", "arm64"):
            self.assertEqual(action.validate_runtime_identity(marker, target_architecture=target), marker)
        marker["cross_architectures"] = ["armhf"]
        with self.assertRaisesRegex(ValueError, "do not support the target"):
            action.validate_runtime_identity(marker, target_architecture="arm64")

    def test_packaging_database_uses_declared_library_paths_without_modifying_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, private = root / "runtime", root / "private-dpkg"
            source = runtime / "var/lib/dpkg/info/libc6:amd64.list"
            source.parent.mkdir(parents=True)
            source.write_text("/.\n/usr/lib/x86_64-linux-gnu/libc.so.6\n")
            source.chmod(0o444)
            before = source.read_bytes()
            alias = root / "sandbox-runtime"
            alias.symlink_to(runtime, target_is_directory=True)
            action.packaging_database(alias, private)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual((private / "info/libc6:amd64.list").read_text().splitlines(),
                             [str(runtime), str(runtime / "usr/lib/x86_64-linux-gnu/libc.so.6")])

    # User contract: raw kernel/module interfaces work without DEBs; the final
    # manifest reads real package identity and requires the five preserved kinds.
    def test_raw_outputs_and_modes_without_deb(self):
        for arch, karch, image in [('amd64','x86','bzImage'),('arm64','arm64','Image')]:
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as temp:
                root=Path(temp);work=root/'work';work.mkdir();out=root/'out';out.mkdir()
                for name in ['include/generated/test.h','arch/'+karch+'/include/generated/test.h','scripts/module.lds','.config','.kernelvariables','Module.symvers','arch/'+karch+'/boot/'+image,'vmlinux','System.map']:
                    path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name)
                for kind in ['image','image-dbg']:
                    modules=work/'output'/kind/'lib/modules'/action.kernel_abi(arch);modules.mkdir(parents=True)
                    (modules/'test.ko').write_bytes(b'module');(modules/'test.ko').chmod(0o640)
                    (modules/'alias.ko').symlink_to('test.ko')
                cfg={'artifacts':str(out/'artifacts'),'runtime_tree':str(out/'runtime'),'debug_tree':str(out/'debug'), 'raw_files':{n:str(out/n) for n in ['image','vmlinux','System.map','config','Module.symvers','kernel.release']}}
                (out/'runtime').mkdir()
                (out/'debug').mkdir()
                manifests=action.export_build_data(root/'source',work,cfg,arch)
                self.assertEqual((out/'image').read_text(),'arch/'+karch+'/boot/'+image)
                self.assertFalse((work/'vmlinux').exists())
                self.assertFalse((work/'output/image').exists())
                for role in ['runtime', 'debug']:
                    self.assertTrue((out/role/'lib/modules'/action.kernel_abi(arch)/'test.ko').is_file())
                self.assertFalse((out/'runtime/image').exists())
                self.assertFalse((out/'debug/image-dbg').exists())
                self.assertTrue((out/'artifacts/build/include/generated/test.h').is_file())
                alias=next(x for x in manifests['runtime'] if x['path'].endswith('alias.ko'))
                self.assertEqual((alias['type'],alias['target']),('symlink','test.ko'))
                ko=next(x for x in manifests['runtime'] if x['path'].endswith('/test.ko'))
                self.assertEqual(ko['mode'],'0640')
                self.assertFalse(list(out.rglob('*.deb')))
    def test_manifest_reads_gzip_control_without_unpacking_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);packages=[]
            names=['linux-image-6.12.94+deb13-sonic-amd64-unsigned','linux-image-6.12.94+deb13-sonic-amd64-dbg','linux-headers-6.12.94+deb13-sonic-amd64','linux-headers-6.12.94+deb13-common-sonic','linux-kbuild-6.12.94+deb13']
            for index,name in enumerate(names):
                arch='all' if index==3 else 'amd64'; directory=root/str(index);directory.mkdir();packages.append(str(directory))
                control=f'Package: {name}\nVersion: 6.12.94-1\nArchitecture: {arch}\nDescription: example\n continuation\n'.encode()
                buf=io.BytesIO()
                with tarfile.open(fileobj=buf,mode='w') as stream:
                    info=tarfile.TarInfo('./control');info.size=len(control);stream.addfile(info,io.BytesIO(control))
                members=[('debian-binary',b'2.0\n'),('control.tar.gz',gzip.compress(buf.getvalue())),('data.tar.gz',b'payload-must-not-be-unpacked')]
                deb=directory/f'{name}_6.12.94-1_{arch}.deb'
                with deb.open('wb') as stream:
                    stream.write(b'!<arch>\n')
                    for member,data in members:
                        stream.write(f'{member+"/":<16}{0:<12}{0:<6}{0:<6}{100644:<8}{len(data):<10}`\n'.encode());stream.write(data)
                        if len(data)%2:stream.write(b'\n')
            receipt=root/'receipt.json';receipt.write_text(json.dumps({'schema':4,'architecture':'amd64','compilation_completed':True}))
            cfg={'receipt':str(receipt),'packages':packages,'manifest':str(root/'manifest.json')}
            action.build({'schema': 6, 'mode': 'manifest', **cfg})
            result=json.loads((root/'manifest.json').read_text());self.assertEqual({r['kind'] for r in result['packages']},{'runtime','debug','headers','headers_common','kbuild'})
            self.assertTrue(all(r['exported'] for r in result['created_packages']))
            cfg['packages']=packages[:-1]
            with self.assertRaisesRegex(ValueError,'all five'):
                action.build({'schema': 6, 'mode': 'manifest', **cfg})


if __name__ == "__main__":
    unittest.main()
