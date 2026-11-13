# bitarray 2.8.1.sonic.1

This entry builds bitarray 2.8.1 from the immutable upstream GitHub commit
`eb1f7014446ef5ce0afddd86d2e929975ec7b4f9`. Its fresh approved GitHub archive is
176,591 bytes, SHA256 `95a6d1fdc1699e6c905b153739af1f210f9394402aa7c4b577cc239c5948682e`.
It is a distinct source archive from the historical PyPI sdist. No earlier PyPI
acquisition is used for this entry, its tests, or a mirror seed. Required source,
header, Python, typing, pickle, license and test files match the immutable Git tree.

The public targets are `@bitarray//:pkg` and `@bitarray//:whl`. The two C
extensions are ordinary rules_cc shared-library actions. Public versioned
`@python_3_13//:python_headers` supplies their declared CPython 3.13 headers.
This entry supports native AMD64 Linux/glibc and the ordinary CPython 3.13 ABI;
free-threaded, other architectures and other Python ABIs are not promised.
The component does not change a consuming root's default interpreter. Its Python
consumers must select 3.13, as both existing sonic-config-engine consumers do.

The selected upstream `py_package` and `py_wheel` own packaging. The wheel is
`bitarray-2.8.1-cp313-cp313-linux_x86_64.whl`, with Root-Is-Purelib false.
All original package Python files, both full upstream test modules, headers,
pickle fixtures and typing data are included. The two repository development
notes `architecture.txt` and `copy_n.txt` are excluded, matching upstream setup.
License bytes and the original metadata values are retained. The selected writer
emits Core Metadata 2.4 and puts the license in `.dist-info/licenses/LICENSE`.

Regular wheel files are explicitly 0644. This deliberately changes the original
extensions' 0755 execute bits; shared extensions are loaded from readable files.
The real existing wheel_layer installation test imports both extensions and runs
the complete upstream suite. No wheel byte or mode equivalence is claimed.
Both shared binaries and the wheel explicitly set stamp=0, independent of a consuming root's --stamp.
No source is stripped or normalized, and no `-g0` or custom repacking action is
introduced. Compiler debug settings remain controlled by the selected C toolchain.

`upstream_test` runs the exact two original class lists through TestLoader,
replacing only the removed unittest.makeSuite harness API. No test method,
expectation, skip condition or upstream source file is changed.
`wheel_contract_test` checks the entire file set, source hashes, ELF ABI, metadata,
license, modes and RECORD. The separate integration module uses the existing
sonic-build-infra wheel_layer and runs both extensions/full tests from its output.
The component's production dependencies do not include sonic-build-infra.

Run the maintained registry validator with the declared AMD64 presubmit targets.
Generate overlay/MODULE.bazel only with the existing `ci/registry_ci.py sync-module`
owner; the module declaration above that overlay remains the sole maintained copy.
Real compilation, installed tests, action graph and cache evidence remain required.

Consumer integration changes only the two actual whl/pkg callers and adds a
versioned dependency with a per-module reviewed registry commit override. The
global e6 catalog, other selected modules, pip requirements and generated lock stay
unchanged. Qualification must prove supported image/config-engine test graphs do
not reach the old pip bitarray repository compilation. Broad fetch-all or sync-all
of the unchanged pip lock is outside that graph claim. The new registry PR is an
explicit dependency; replace the inert registry placeholder before any consumer run.
