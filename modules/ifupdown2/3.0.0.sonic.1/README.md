# ifupdown2 3.0.0

This module installs the SONiC Make-selected 3.0.0-1 upstream source and the six SONiC patches in their original order. The source wrapper and patches come from the fixed sonic-buildimage archive in source.json.

`@ifupdown2//:ifupdown2.runtime` provides a raw installation TAR with the private Python package, original configuration, command links, systemd units, examples, documentation and egg metadata. `@ifupdown2//:ifupdown2.runtime_metadata` derives the Debian package identity and maintainer controls from the original packaging and actual TAR. `@ifupdown2//:ifupdown2.control` projects those controls through the shared source-package interface.

Documentation uses the declared APT docutils environment and pigz for its final gzip files. The installation TAR remains uncompressed. The producer does not run service activation or modify host networking. The image owner applies the original package installation effects.

`@ifupdown2//:runtime_test` verifies the archive and control formats, original setup metadata, command help and original interface parser. It performs no live network configuration.
