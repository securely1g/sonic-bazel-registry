"""Create a native tool layout and a deterministic, independent archive fixture."""
import io
from pathlib import Path
import sys
import tarfile

if sys.argv[1] == "tool":
    launcher, runtime, tar = map(Path, sys.argv[2:])
    runtime.mkdir(exist_ok=True)
    program = runtime / "run"
    program.write_text("#!/bin/sh\nexec " + str(tar) + ' "$@"\n')
    program.chmod(0o755)
    launcher.write_text('#!/bin/sh\nexec "$0.runtime/run" "$@"\n')
    launcher.chmod(0o755)
elif sys.argv[1] == "payload":
    with tarfile.open(sys.argv[2], "w", format=tarfile.USTAR_FORMAT) as archive:
        for path, contents, mode in [
            ("usr/share/closure/payload.txt", b"independent tar payload\n", 0o755),
            ("usr/bin/closure-probe", b"#!/bin/sh\nexit 0\n", 0o755),
        ]:
            member = tarfile.TarInfo(path)
            member.mode = mode
            member.size = len(contents)
            archive.addfile(member, io.BytesIO(contents))
else:
    raise SystemExit("unknown fixture operation")
