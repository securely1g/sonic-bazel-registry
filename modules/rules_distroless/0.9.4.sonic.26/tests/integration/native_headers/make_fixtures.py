"""Create tiny, deterministic DEBs that exercise the real native importer.

The overlay wrapper deliberately has the same include/include_next distinction
as libc compatibility header packages. It is safe only with its .pc definition.
"""

import hashlib
import io
import json
from pathlib import Path
import tarfile


def archive(files, symlinks=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz", format=tarfile.USTAR_FORMAT) as tar:
        for name, text in sorted(files.items()):
            data = text.encode()
            entry = tarfile.TarInfo("./" + name)
            entry.size = len(data)
            entry.mode = 0o644
            entry.mtime = 0
            tar.addfile(entry, io.BytesIO(data))
        for name, target in sorted((symlinks or {}).items()):
            entry = tarfile.TarInfo("./" + name)
            entry.type = tarfile.SYMTYPE
            entry.linkname = target
            entry.mode = 0o777
            entry.mtime = 0
            tar.addfile(entry)
    return output.getvalue()


def deb(name, files, symlinks=None):
    members = {
        "debian-binary": b"2.0\n",
        "control.tar.xz": archive({"control": "Package: %s\nVersion: 1\nArchitecture: all\nMaintainer: Fixture <fixture@example.invalid>\nDescription: Native header integration fixture\n" % name}),
        "data.tar.xz": archive(files, symlinks),
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
    Path(name + ".files.json").write_text(json.dumps(sorted(set(files) | set(symlinks or {}))))


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

# A directory alias can span multiple dependency packages, as Tcl/Tk's
# unversioned development packages do. A quoted include also crosses owners.
deb("alias-left-dev", {
    "usr/include/shared/alpha.h": '#include "detail/part.inc"\n#define ALPHA_VALUE (PART_VALUE + 4)\n',
})
deb("alias-right-dev", {
    "usr/include/shared/detail/part.inc": "#define PART_VALUE 13\n",
    "usr/include/shared/beta.hpp": "#define BETA_VALUE 9\n",
    "usr/include/shared/leaf": "#define LEAF_VALUE 16\n",
})
deb("alias-dev", {
    "usr/lib/pkgconfig/alias.pc": pc("alias", "-I${prefix}/include/alias"),
}, {"usr/include/alias": "shared", "usr/include/chain": "alias"})
deb("alias-client-dev", {
    "usr/include/client/use.h": "#include <alpha.h>\n#include <beta.hpp>\n#include <leaf>\n#define CLIENT_VALUE (ALPHA_VALUE + BETA_VALUE + LEAF_VALUE)\n",
    "usr/lib/pkgconfig/client.pc": pc("client", "-I${prefix}/include/client") + "Requires: alias\n",
})
