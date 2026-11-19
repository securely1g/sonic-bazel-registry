"""Create tiny, deterministic DEBs that exercise the real native importer.

The overlay wrapper deliberately has the same include/include_next distinction
as libc compatibility header packages. It is safe only with its .pc definition.
"""

import hashlib
import io
from pathlib import Path
import tarfile


def archive(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz", format=tarfile.USTAR_FORMAT) as tar:
        for name, text in sorted(files.items()):
            data = text.encode()
            entry = tarfile.TarInfo("./" + name)
            entry.size = len(data)
            entry.mode = 0o644
            entry.mtime = 0
            tar.addfile(entry, io.BytesIO(data))
    return output.getvalue()


def deb(name, files):
    members = {
        "debian-binary": b"2.0\n",
        "control.tar.xz": archive({"control": "Package: %s\nVersion: 1\nArchitecture: all\nMaintainer: Fixture <fixture@example.invalid>\nDescription: Native header integration fixture\n" % name}),
        "data.tar.xz": archive(files),
    }
    output = bytearray(b"!<arch>\n")
    for member, data in members.items():
        header = f"{member + '/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(data):<10}`\n"
        output.extend(header.encode())
        output.extend(data)
        if len(data) % 2:
            output.extend(b"\n")
    Path(name + ".deb").write_bytes(output)
    Path(name + ".sha256").write_text(hashlib.sha256(output).hexdigest() + "\n")


def pc(name, flags):
    return "prefix=/usr\nName: %s\nDescription: Header namespace fixture\nVersion: 1\nCflags: %s\nLibs:\n" % (name, flags)


deb("libvariant-dev", {
    "usr/include/variant/base.h": "#define VARIANT_BASE 42\n",
    "usr/include/overlay/stdio.h": """/* Overlay selection requires its matching pkg-config definition. */
#ifdef HEADER_OVERLAY
#include_next <stdio.h>
#define HEADER_OVERLAY_SEEN 1
#else
#include <stdio.h>
#endif
""",
    "usr/lib/pkgconfig/libvariant.pc": pc("libvariant", "-I${prefix}/include"),
    "usr/lib/pkgconfig/libvariant-overlay.pc": pc("libvariant-overlay", "-I${prefix}/include/overlay -DHEADER_OVERLAY"),
})
deb("libmiddle-dev", {
    "usr/include/middle.h": "#include <variant/base.h>\n#define MIDDLE_BASE VARIANT_BASE\n",
})
deb("plain-dev", {
    "usr/include/plain/value.h": "#define PLAIN_VALUE 42\n",
})
deb("unmatched-dev", {
    "usr/include/alpha/alpha_api.h": "#define ALPHA_VALUE 20\n",
    "usr/include/beta/beta_api.h": "#define BETA_VALUE 22\n",
    "usr/lib/pkgconfig/alpha.pc": pc("alpha", "-I${prefix}/include/alpha"),
    "usr/lib/pkgconfig/beta.pc": pc("beta", "-I${prefix}/include/beta"),
})
