# libyang 3.12.2.sonic.8

This entry preserves the published `.sonic.7` upstream 3.12.2 archive, SONiC patch, native C targets, prepared CLI runtimes, original test selection and five-second interactive deadlines. It adds the original Debian `dh_makeshlibs` and `dh_installdeb` effects to runtime package metadata. The projected control TAR contains the generated shlibs, symbols and ldconfig trigger; the existing metadata test verifies these files and their package identity.

The recipe selects published `sonic-build-infra@0.0.37-d31541a95fdf477302f1b109f2105eee81c86617` and `rules_distroless@0.9.4.sonic.21`. It retains the original fixed APT package identities, source archive, patch and build flags. Published `.sonic.7` inputs remain unchanged; `.sonic.8` is a new packaging revision under the registry's publication policy.

## Interfaces

The seven public build targets remain `:libyang_pkg`, `:libyang_pkg.debug_symbols`, `:tools_pkg`, `:tools_pkg.debug_symbols`, `:runtime_packages.json`, `:upstream_test_binaries` and `:development_pkg`. Image consumers use the runtime TAR and producer metadata; matching debug outputs remain separate.

The five presubmit tests remain `:libyang_test`, `:libyang_package_test`, `:upstream_check`, `:runtime_metadata_test` and `:libyang_installed_test`. AMD64 and ARM64 retain their declared Trixie platform routes. Prepared runtime wrappers execute the genuine target loader and binaries; original source, Tcl subprocess behavior, PTY exit handling, cases and assertions remain intact.

## Validation

A fresh AMD64 registry consumer with no source overrides passed all seven build targets and five uncached tests, exit 0 in 318.702 seconds. All 63 original upstream execution records passed. The fetched MODULE and every overlay matched the declared recipe, and 71 output files were hashed. The host was Ubuntu; the compiler, sysroot and runtime closure were declared Trixie inputs. Hosted ARM64 validation remains separate. Logs, XML, upstream results and hashes were retained before `bazel clean`.

From the registry root:

```sh
python3 ci/registry_ci.py run \
  --module libyang --version 3.12.2.sonic.8 --architecture amd64 \
  --work-dir /tmp/registry-ci-libyang-amd64 \
  --artifacts /tmp/registry-ci-libyang-amd64-artifacts
```

The retained standalone PTY, Tcl interpreter and prepared-runtime regressions under `tests/` supplement the real upstream execution tests; they do not replace them.
