# GRUB 2.12 hermetic raw-image BIOS setup tool

GNU GRUB2.12 and Debian2.12-9+deb13u2 packaging match the fixed APT boot.img and i386-pc modules. The declared source preparation applies all148 original Debian patches, then one narrow raw-image patch: when the caller explicitly passes --skip-fs-probe, use the already opened destination as root instead of guessing a host device from the staging directory. The ordinary probing branch stays unchanged.

The current locked APT tool opens the raw destination but then fails while guessing the staging directory's backing host device; this is distinct from missing executable/runtime libraries. Native Bazel C/C++ declarations and controlled rules_cc_autoconf probes adapt the existing BCR2.14 implementation to the fixed2.12 sources; no configure/Make wrapper or source-tree copy runs. source_build_tool retains the declared execution closure.

Only native AMD64 grub-bios-setup is claimed. The public raw_embedding_test uses the same regular-file fixture and fixed APT mkimage/resources/sgdisk as the APT comparison, checks GPT CRC/type/geometry, MBR signature, core LBA and actual embedded diskboot code. Version/help checks remain. Guest boot, ARM and other GRUB utilities are outside this module's validation scope.

The producer uses the already published infrastructure 0.0.34 source/tool API. The raw-image test additionally needs the image-tool collection and selects infrastructure 0.0.37-d31541a95fdf477302f1b109f2105eee81c86617 through presubmit.consumer_deps. The producer minimum and source inputs remain unchanged.
