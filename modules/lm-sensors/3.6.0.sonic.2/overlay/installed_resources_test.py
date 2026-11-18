"""Compare original Debian/Make-selected installed resources with their sources."""
import gzip
import hashlib
import pathlib
import sys
import tarfile

source = pathlib.Path(sys.argv[1]).parent
packaging = pathlib.Path(sys.argv[2]).parent
packages = ["libsensors5", "lm-sensors", "fancontrol", "sensord", "libsensors-config"]
# Debian .install/.docs/.examples and upstream Module.mk select these sources.
resources = {
    "libsensors5": [("README.Debian", packaging / "libsensors5.README.Debian")],
    "lm-sensors": [("README.Debian", packaging / "lm-sensors.README.Debian")],
    "sensord": [("README.Debian", packaging / "sensord.README.Debian")],
}
# Installed executable/configuration paths from Debian .install, dh_installinit,
# dh_installsystemd and the source Make installation rules.
static = {
    "lm-sensors": {
        "usr/sbin/sensors-detect": ("source", "prog/detect/sensors-detect", 0o755),
        "usr/bin/sensors-conf-convert": ("source", "etc/sensors-conf-convert", 0o755),
        "etc/init.d/lm-sensors": ("debian", "lm-sensors.init", 0o755),
        "usr/lib/systemd/system/lm-sensors.service": ("debian", "lm-sensors.service", 0o644),
    },
    "fancontrol": {
        "usr/sbin/fancontrol": ("source", "prog/pwm/fancontrol", 0o755),
        "usr/sbin/pwmconfig": ("source", "prog/pwm/pwmconfig", 0o755),
        "etc/init.d/fancontrol": ("debian", "fancontrol.init", 0o755),
        "usr/lib/systemd/system/fancontrol.service": ("debian", "fancontrol.service", 0o644),
        "usr/lib/systemd/system-sleep/fancontrol": ("debian", "fancontrol-systemd-sleep", 0o755),
    },
    "sensord": {
        "etc/default/sensord": ("debian", "sensord.default", 0o644),
        "etc/init.d/sensord": ("debian", "sensord.init", 0o755),
    },
    "libsensors-config": {"etc/sensors3.conf": ("source", "etc/sensors.conf.default", 0o644)},
}
# Exact fixed-source output of original dh_installchangelogs, compatibility 13,
# DEB_BUILD_OPTIONS=nocheck. Independently projected before binding the new API.
trimmed_changelogs = {'lm-sensors': 'a9cdf37c505db3dca96674b8e617ac1270ff17596404a7cdf7456c7f4045b9b4', 'libsensors5': '532e0b22b4cbbb833e1ff0b6586013cb4075f37b6c91c67cd6fc1ad758167b59', 'fancontrol': 'dda52ce5bbfd67139c4faa47f89fbe183353776635a103b7309682dff34cac19', 'sensord': '6cce1794a7866dbe7fba8ed160471016dd1808c3d4ff73445837d5279820a59b', 'libsensors-config': 'd76383caa419630001f1fa2d4d54de46c9de603d348ef305ec2102ddc116f806'}
for package, archive in zip(packages, sys.argv[3:], strict=True):
    with tarfile.open(archive) as tar:
        members = {m.name.removeprefix("./"): m for m in tar}
        for destination, (origin, relative, mode) in static.get(package, {}).items():
            member = members[destination]
            assert member.isfile() and (member.uid, member.gid, member.mode) == (0, 0, mode), destination
            original = (source if origin == "source" else packaging) / relative
            assert tar.extractfile(member).read() == original.read_bytes(), destination
        expected = list(resources.get(package, []))
        docs = packaging / (package + ".docs")
        if docs.exists():
            for line in docs.read_text().splitlines():
                path = source / line.strip()
                if path.is_file():
                    expected.append((path.name, path))
        # dh_installchangelogs selects the upstream CHANGES for every package.
        expected.append(("changelog", source / "CHANGES"))
        for filename, original in expected:
            data = original.read_bytes()
            compressed = filename.startswith("changelog") or len(data) > 4096
            destination = "usr/share/doc/" + package + "/" + filename + (".gz" if compressed else "")
            member = members[destination]
            assert member.isfile() and (member.uid, member.gid, member.mode) == (0, 0, 0o644), destination
            actual = tar.extractfile(member).read()
            assert (gzip.decompress(actual) if compressed else actual) == data, destination
        changelog_path = "usr/share/doc/" + package + "/changelog.Debian.gz"
        installed_changelog = gzip.decompress(tar.extractfile(members[changelog_path]).read())
        assert hashlib.sha256(installed_changelog).hexdigest() == trimmed_changelogs[package], changelog_path
        copyright_path = "usr/share/doc/" + package + "/copyright"
        assert tar.extractfile(members[copyright_path]).read() == (packaging / "copyright").read_bytes()
        if package == "sensord":
            # dh_installchangelogs drops the original 427-byte NEWS after trimming.
            assert "usr/share/doc/sensord/NEWS.Debian.gz" not in members
