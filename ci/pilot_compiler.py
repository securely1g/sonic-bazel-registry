#!/usr/bin/python3 -IS
"""Give the libtool fixture's oversized GCC invocations a real ARM64 kernel."""
import os
import shutil
import signal
import subprocess
import sys
import tempfile


def driver(arguments):
    # The declared launcher locates ld.so, GCC and its libraries relative to $0.
    return ["/bin/sh", "-c", '. "$SONIC_PILOT_GCC_ORIGINALS/${0##*/}"', sys.argv[0], *arguments]


def needs_kernel(arguments):
    # Small configure probes go directly to the compiler. For the fixture's
    # long commands, ask that same GCC what it would pass to its children.
    if "-###" in arguments or sum(len(os.fsencode(arg)) + 1 for arg in arguments) < 65536:
        return False
    preview = subprocess.run(
        driver(["-###", *arguments]), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    fields = (b"COLLECT_GCC_OPTIONS=", b"LIBRARY_PATH=", b"COMPILER_PATH=")
    limit = 32 * os.sysconf("SC_PAGE_SIZE")
    return preview.returncode == 0 and any(
        len(line) + 1 > limit for line in preview.stderr.splitlines() if line.startswith(fields)
    )


def run_in_kernel(command):
    # The bundled VM is noninteractive. Use the private action share to restore
    # stdin before executing the unchanged command; neither stdin nor argv is logged.
    with tempfile.NamedTemporaryFile(dir=os.environ["SONIC_PILOT_GCC_ORIGINALS"]) as source:
        shutil.copyfileobj(sys.stdin.buffer, source)
        source.flush()
        guest = [
            "/usr/local/bin/sonic-arm64-kernel", "--bind", os.environ["SONIC_PILOT_INFRA_WORK"],
            "--cwd", os.getcwd(), "--", "/bin/sh", "-c", 'input=$1; shift; exec "$@" < "$input"',
            "restore-compiler-stdin", source.name, *command,
        ]
        status = subprocess.run(guest).returncode
    if status < 0:
        signum = -status
        if signum not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
    return status


if __name__ == "__main__":
    args = sys.argv[1:]
    command = driver(args)
    if needs_kernel(args):
        sys.exit(run_in_kernel(command))
    os.execv(command[0], command)
