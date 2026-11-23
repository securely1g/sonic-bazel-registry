"""Debian target architecture in the existing helper command path."""
def target_arch_command(command):
    return select({
        "@platforms//cpu:x86_64": command.replace("{DEB_HOST_ARCH}", "amd64"),
        "@platforms//cpu:aarch64": command.replace("{DEB_HOST_ARCH}", "arm64"),
    })
