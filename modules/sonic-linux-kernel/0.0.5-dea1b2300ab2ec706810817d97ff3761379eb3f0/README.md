# sonic-linux-kernel 0.0.5

The source archive includes the SONiC configuration and patch series for Debian
Linux 6.12.94-1. The registry overlay carries the split compilation, installation
and packaging targets used by the VS installer from release 0.0.4. The source
repository provides the Make recipe, SONiC configuration and patches. Its Bazel
package target alone does not export the runtime TAR and control archive that
buildimage consumes.

Both AMD64 and ARM64 builds use the archive checksums from Debian's
[6.12.94-1 source package](https://snapshot.debian.org/package/linux/6.12.94-1/).
The registry presubmit builds the runtime, debug, headers and kbuild Debian
packages, the runtime TAR, package metadata, control archive and boot files.
It also runs the producer, installer and tool generation tests.
