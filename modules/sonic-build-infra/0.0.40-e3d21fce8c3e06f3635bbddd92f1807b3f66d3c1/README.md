# Assembly preprocessing with sysroot headers and compressed DWARF

Register merged Infra master `e3d21fce8c3e06f3635bbddd92f1807b3f66d3c1` as `0.0.40-e3d21fce8c3e06f3635bbddd92f1807b3f66d3c1`. It gives preprocessed assembly (`.S`) actions `-nostdinc` and the shared sysroot's C include directories, like C compiles (Infra PR #128), and compresses extracted DWARF by default (Infra PR #123).

Preserve the existing registry test overlay and public cross-test visibility patch. The presubmit retains the existing tool and package checks and adds `toolchains/gcc/tests:assembly_include_test`.
