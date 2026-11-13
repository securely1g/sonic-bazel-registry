"""Check the installed wheel contract against unchanged upstream source facts."""
import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import stat
import struct
import zipfile


def main():
    parser = argparse.ArgumentParser()
    for name in ("wheel", "contract", "readme", "license"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_bytes())
    dist = "bitarray-2.8.1.dist-info/"
    extensions = {"bitarray/" + name + ".cpython-313-x86_64-linux-gnu.so"
                  for name in ("_bitarray", "_util")}
    expected = set(contract["package_files"]) | extensions | {
        dist + name for name in ("METADATA", "WHEEL", "RECORD", "licenses/LICENSE")}
    assert args.wheel.name == "bitarray-2.8.1-cp313-cp313-linux_x86_64.whl"
    with zipfile.ZipFile(args.wheel) as archive:
        infos = archive.infolist()
        assert len(infos) == len(expected) and {r.filename for r in infos} == expected
        assert sum(r.file_size for r in infos) <= 64 * 1024 * 1024
        for row in infos:
            mode = row.external_attr >> 16
            assert stat.S_ISREG(mode) and stat.S_IMODE(mode) == 0o644
        for name, expected_hash in contract["package_files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected_hash
        for name in extensions:
            raw = archive.read(name)
            assert raw[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", raw, 18)[0] == 62
        assert archive.read(dist + "licenses/LICENSE") == args.license.read_bytes()
        metadata = BytesParser().parsebytes(archive.read(dist + "METADATA"))
        for field, expected_value in contract["metadata"].items():
            assert metadata.get_all(field) == expected_value, field
        assert metadata["Metadata-Version"] == "2.4"
        assert metadata.get_all("License-File") == ["LICENSE"]
        assert metadata.get_all("Requires-Dist") is None
        assert metadata.get_payload().rstrip("\n") == args.readme.read_text().rstrip("\n")
        wheel = BytesParser().parsebytes(archive.read(dist + "WHEEL"))
        assert wheel["Root-Is-Purelib"] == "false"
        assert wheel.get_all("Tag") == ["cp313-cp313-linux_x86_64"]
        records = list(csv.reader(io.StringIO(archive.read(dist + "RECORD").decode())))
        assert len(records) == len(expected) and {r[0] for r in records} == expected
        for name, digest, size in records:
            if name == dist + "RECORD":
                assert digest == size == ""
            else:
                raw = archive.read(name)
                encoded = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
                assert digest == "sha256=" + encoded and size == str(len(raw))
    print("Full wheel payload, native ABI, metadata, license, modes and RECORD verified")


if __name__ == "__main__":
    main()
