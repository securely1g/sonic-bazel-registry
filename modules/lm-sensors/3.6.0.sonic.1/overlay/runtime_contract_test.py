"""Validate Debian/SONiC installed interfaces without requiring sensor hardware."""
import sys
import tarfile

required = {
 "libsensors5": {"usr/lib/x86_64-linux-gnu/libsensors.so.5.0.0": ("file", 0o644), "usr/lib/x86_64-linux-gnu/libsensors.so.5": ("link", 0o777)},
 "lm-sensors": {"usr/bin/sensors": ("file", 0o755), "usr/sbin/sensors-detect": ("file", 0o755), "usr/bin/sensors-conf-convert": ("file", 0o755), "usr/sbin/isadump": ("file", 0o755), "usr/sbin/isaset": ("file", 0o755)},
 "libsensors-config": {"etc/sensors3.conf": ("file", 0o644)},
 "fancontrol": {"usr/sbin/fancontrol": ("file", 0o755), "usr/sbin/pwmconfig": ("file", 0o755), "usr/lib/systemd/system/fancontrol.service": ("file", 0o644)},
 "sensord": {"usr/sbin/sensord": ("file", 0o755), "etc/default/sensord": ("file", 0o644)},
}
for (name, expected), path in zip(required.items(), sys.argv[1:], strict=True):
 with tarfile.open(path) as tar:
  members={m.name.removeprefix("./"):m for m in tar}
  for filename,(kind,mode) in expected.items():
   member=members[filename]
   assert (member.uid,member.gid,member.mode)==(0,0,mode),(name,filename,member)
   assert member.issym() if kind=="link" else member.isfile(),(name,filename)
   if filename.endswith("libsensors.so.5"): assert member.linkname=="libsensors.so.5.0.0"
   if filename.endswith("libsensors.so.5.0.0") or filename in ("usr/bin/sensors","usr/sbin/sensord","usr/sbin/isadump","usr/sbin/isaset"):
    assert tar.extractfile(member).read(4)==b"\x7fELF",filename
