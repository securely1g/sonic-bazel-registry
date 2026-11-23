"""Validate Debian/SONiC installed interfaces without requiring sensor hardware."""
import hashlib
import json
from pathlib import Path
import sys
import struct
import tarfile

# Debian's LIBDIR=/usr/lib/$(DEB_HOST_MULTIARCH) and ELF e_machine identify
# the installed target ABI independently of the rule's path expressions.
metadata = json.loads(Path(sys.argv[-1]).read_text())
architecture = metadata["architecture"]
multiarch, machine = {"amd64": ("x86_64-linux-gnu", 62), "arm64": ("aarch64-linux-gnu", 183)}[architecture]
required = {
 "libsensors5": {"usr/lib/" + multiarch + "/libsensors.so.5.0.0": ("file", 0o644), "usr/lib/" + multiarch + "/libsensors.so.5": ("link", 0o777)},
 "lm-sensors": {"usr/bin/sensors": ("file", 0o755), "usr/sbin/sensors-detect": ("file", 0o755), "usr/bin/sensors-conf-convert": ("file", 0o755), "usr/sbin/isadump": ("file", 0o755), "usr/sbin/isaset": ("file", 0o755)},
 "libsensors-config": {"etc/sensors3.conf": ("file", 0o644)},
 "fancontrol": {"usr/sbin/fancontrol": ("file", 0o755), "usr/sbin/pwmconfig": ("file", 0o755), "usr/lib/systemd/system/fancontrol.service": ("file", 0o644)},
 "sensord": {"usr/sbin/sensord": ("file", 0o755), "etc/default/sensord": ("file", 0o644)},
}
def check_package_record(package, name, archive_path):
    assert package["control_fields"]["Package"] == name, name
    with open(archive_path, "rb") as archive:
        assert package["payload_sha256"] == hashlib.file_digest(archive, "sha256").hexdigest(), name
    if name == "libsensors-config":
        assert package["control_fields"]["Architecture"] == "all", name


for (name, expected), path in zip(required.items(), sys.argv[1:-1], strict=True):
 check_package_record(metadata["packages"][name], name, path)
 with tarfile.open(path) as tar:
  members={m.name.removeprefix("./"):m for m in tar}
  if name == "libsensors5":
   assert {p for p in members if Path(p).name.startswith("libsensors.so")} == set(expected), name
  for filename,(kind,mode) in expected.items():
   member=members[filename]
   assert (member.uid,member.gid,member.mode)==(0,0,mode),(name,filename,member)
   assert member.issym() if kind=="link" else member.isfile(),(name,filename)
   if filename.endswith("libsensors.so.5"): assert member.linkname=="libsensors.so.5.0.0"
   if filename.endswith("libsensors.so.5.0.0") or filename in ("usr/bin/sensors","usr/sbin/sensord","usr/sbin/isadump","usr/sbin/isaset"):
    header = tar.extractfile(member).read(20)
    assert header[:4] == b"\x7fELF", filename
    order = {1: "<", 2: ">"}[header[5]]
    assert struct.unpack_from(order + "H", header, 18)[0] == machine, (filename, architecture)
