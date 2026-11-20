"""Exercise OCI owner metadata with the real libyang TAR and Debian recipe."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

from debian.changelog import Changelog
from debian.deb822 import Deb822
from sonic_oci.owner_metadata import module_identity, resolve
from sonic_oci.paths import expand_required_paths


def main():
    metadata, runtime, module, control, changelog = map(Path, sys.argv[1:6])
    control_archive = Path(sys.argv[6])
    architecture = sys.argv[7]
    document = json.loads(metadata.read_text())
    assert document['architecture'] == architecture
    package = document['packages']['libyang3']
    fields = package['control_fields']
    recipe = next(item for item in Deb822.iter_paragraphs(control.read_text().splitlines())
                  if item.get('Package') == 'libyang3')
    with changelog.open() as stream:
        version = str(Changelog(stream).version)
    assert fields['Package'] == recipe['Package']
    assert fields['Version'] == version
    assert fields['Description'] == recipe['Description']
    assert '${' not in json.dumps(fields)
    payload_sha = hashlib.sha256(runtime.read_bytes()).hexdigest()
    assert package['payload_sha256'] == payload_sha

    # Debian's original dh sequence emits actual binary control effects.
    with tarfile.open(control_archive, 'r:') as archive:
        controls = {entry.name.removeprefix('./'): archive.extractfile(entry).read()
                    for entry in archive if entry.isfile()}
    installed_control = Deb822(controls['control'].decode().splitlines())
    assert installed_control['Package'] == recipe['Package']
    assert installed_control['Version'] == version
    assert installed_control['Architecture'] == architecture
    assert '${' not in controls['control'].decode()
    assert b'activate-noawait ldconfig' in controls['triggers']
    assert b'libyang 3 libyang3 ' in controls['shlibs']
    assert controls['symbols'].startswith(b'libyang.so.3 libyang3 ')

    # The image need not duplicate the library path already owned by libyang.
    policy = {'schema': 1, 'packages': {}}
    owners = {'@libyang//:runtime_packages.json': metadata}
    modules = {'libyang': module}
    sources = {'libyang3': '@libyang//:libyang_pkg'}
    resolved, identities = resolve(policy, owners, modules, sources, architecture)
    record = resolved['packages']['libyang3']
    assert record['payload_sha256'] == payload_sha
    assert record['control_fields']['Version'] == version
    assert record['control_fields']['Architecture'] == architecture
    assert record['source_revision'] == module_identity(module, 'libyang')
    assert identities['libyang']['module_sha256'] == hashlib.sha256(module.read_bytes()).hexdigest()
    multiarch = {'amd64': 'x86_64-linux-gnu', 'arm64': 'aarch64-linux-gnu'}[architecture]
    abi_path = 'usr/lib/' + multiarch + '/libyang.so.3'
    assert abi_path in expand_required_paths(record['required_paths'], architecture)
    with tarfile.open(runtime) as archive:
        assert any(item.name.removeprefix('./') == abi_path for item in archive)

    for labels, selected_architecture in [
        ({'libyang3': '@libyang//:tools_pkg'}, architecture),
        (sources, 'arm64' if architecture == 'amd64' else 'amd64'),
    ]:
        try:
            resolve(policy, owners, modules, labels, selected_architecture)
        except ValueError:
            pass
        else:
            raise AssertionError('OCI consumer accepted a mismatched TAR or target architecture')
    print('Recipe version, real TAR identity, producer ABI path and OCI owner consumer verified')


if __name__ == '__main__':
    main()
