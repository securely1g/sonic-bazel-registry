#!/usr/bin/python3
"""Execute the original OpenSSL TAP recipes with the ARM Perl and matching kernel capability."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def share(qemu, tag, path, readonly=False):
    # QEMU's key/value syntax escapes literal commas by doubling them.
    location = str(path).replace(",", ",,")
    options = f"local,id={tag},path={location},security_model=none"
    if readonly:
        options += ",readonly=on"
    qemu.extend(["-fsdev", options, "-device", f"virtio-9p-pci,fsdev={tag},mount_tag={tag}"])


def kernel_perl(config, args, env):
    kernel = Path(config["kernel_dir"])
    with tempfile.TemporaryDirectory(prefix="fips-afalg-") as directory:
        control = Path(directory)
        mounts = config["mounts"]
        (control / "mounts").write_text("".join(path + "\n" for path in mounts))
        (control / "uid").write_text(str(os.getuid()))
        (control / "gid").write_text(str(os.getgid()))
        env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        command = ["/usr/bin/env", "-i", *(f"{key}={value}" for key, value in env.items()),
                   "/usr/bin/perl", *args]
        (control / "run").write_text(f"set -eu\ncd {shlex.quote(os.getcwd())}\nexec {shlex.join(command)}\n")
        qemu = ["/usr/bin/qemu-system-aarch64", "-machine", "virt", "-accel", "tcg",
                "-cpu", "cortex-a72", "-smp", "1", "-m", "512", "-nographic", "-no-reboot",
                "-nodefaults", "-serial", "stdio", "-nic", "none", "-kernel", str(kernel / "kernel"),
                "-initrd", str(kernel / "initrd.gz"), "-append", "console=ttyAMA0 rdinit=/init panic=-1 loglevel=4"]
        share(qemu, "armroot", config["guest_root"], readonly=True)
        share(qemu, "control", control)
        for index, path in enumerate(mounts):
            share(qemu, f"bind{index}", path)
        guest = subprocess.run(qemu, capture_output=True, timeout=180)
        status = control / "status"
        if guest.returncode or not status.exists():
            sys.stderr.buffer.write(guest.stdout + guest.stderr)
            raise RuntimeError(f"ARM kernel guest ended without the Perl recipe status (QEMU exit {guest.returncode})")
        machine = (control / "machine").read_text().strip()
        release = (control / "kernel").read_text().strip()
        if (machine, release) != ("aarch64", "6.12.107+deb13-arm64"):
            raise RuntimeError(f"Unexpected AF_ALG kernel identity: {machine} {release}")
        print(f"# AF_ALG TAP interpreter: /usr/bin/perl on Linux {release} {machine}", file=sys.stderr, flush=True)
        sys.stdout.buffer.write((control / "stdout").read_bytes())
        sys.stderr.buffer.write((control / "stderr").read_bytes())
        return int(status.read_text())


def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    args = sys.argv[2:]
    env = os.environ.copy()
    for key in ("PERLLIB", "PERL5LIB", "PERL5OPT"):
        env.pop(key, None)
    if any(Path(arg).name == "30-test_afalg.t" for arg in args):
        return kernel_perl(config, args, env)
    guest = config["guest_perl"]
    os.execve(guest[0], [*guest, *args], env)


if __name__ == "__main__":
    sys.exit(main())
