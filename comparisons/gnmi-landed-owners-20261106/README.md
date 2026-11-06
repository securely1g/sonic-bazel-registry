# Complete gNMI first-registration comparison

No published gNMI predecessor exists at maintained main `e3f311112387394e42cfead34716896724e3a719`. Candidate `a5829f922eb7bedb27a79786daeae260dfa71098` registers `0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366`.

[Download the complete patch](registry182.patch). SHA-256 `8041f300298efe1f831e7b7d3569178db78966246c42fa3417d1792cb8d8a1e6`; 21,659 bytes. In a clean baseline checkout with no `modules/sonic-gnmi`, run `git apply --check registry182.patch` then `git apply --index registry182.patch`. The full resulting Git tree is `2a784858981688247882fd76f549d734ece454bc`; all2,113 baseline files and modes are preserved. This was verified in a fresh isolated checkout. Native validation is separate and pending.

```diff
Complete initial sonic-gnmi registration; no published predecessor.
Baseline: e3f311112387394e42cfead34716896724e3a719
Candidate: a5829f922eb7bedb27a79786daeae260dfa71098
Version: 0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366
Apply in a clean checkout of the baseline, where modules/sonic-gnmi does not exist:
  git apply --check registry182.patch
  git apply --index registry182.patch
Expected complete tree: 2a784858981688247882fd76f549d734ece454bc
Source changes: https://github.com/securely1g/sonic-gnmi/compare/6a854f16f9a63a4357b5f2db6969f5c9c00cbdde...83a7de8d7760f7cac9690f5e304d94a9171f2366

diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/MODULE.bazel b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/MODULE.bazel
new file mode 100644
index 0000000000000000000000000000000000000000..7122ccfeb168eb703114557590edc069faf22904
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/MODULE.bazel
@@ -0,0 +1,170 @@
+module(
+    name = "sonic-gnmi",
+    version = "0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366",
+    bazel_compatibility = [
+        ">=8.5.1",
+        "<=8.5.1",
+    ],
+)
+
+bazel_dep(name = "sonic-mgmt-common", version = "1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b", repo_name = "sonic_mgmt_common")
+bazel_dep(name = "gazelle", version = "0.54.0")
+bazel_dep(name = "openconfig_goyang", version = "0.0.0.sonic.1-20200309174518-a00bece872fc", repo_name = "com_github_openconfig_goyang")
+bazel_dep(name = "openconfig_ygot", version = "0.7.1.sonic.1", repo_name = "com_github_openconfig_ygot")
+bazel_dep(name = "rules_go", version = "0.64.1-sonic.1", repo_name = "io_bazel_rules_go")
+bazel_dep(name = "sonic-build-infra", version = "0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e", repo_name = "sonic_build_infra")
+
+go_deps = use_extension("@gazelle//:extensions.bzl", "go_deps")
+go_deps.from_file(go_work = "//:go.bazel.work")
+
+use_repo(go_deps, "cc_mvdan_sh_v3", "com_github_agiledragon_gomonkey_v2", "com_github_alicebob_miniredis_v2", "com_github_c9s_goprocinfo", "com_github_dgrijalva_jwt_go", "com_github_fsnotify_fsnotify", "com_github_go_redis_redismock_v9", "com_github_godbus_dbus_v5", "com_github_gogo_protobuf", "com_github_golang_glog", "com_github_golang_mock", "com_github_golang_protobuf", "com_github_google_gnxi", "com_github_google_go_cmp", "com_github_google_shlex", "com_github_kylelemons_godebug", "com_github_maruel_natural", "com_github_msteinert_pam", "com_github_openconfig_gnmi", "com_github_openconfig_gnoi", "com_github_openconfig_gnsi", "com_github_opencontainers_go_digest", "com_github_opencontainers_image_spec", "com_github_redis_go_redis_v9", "com_github_stretchr_testify", "com_github_workiva_go_datastructures", "in_gopkg_yaml_v2", "in_gopkg_yaml_v3", "land_oras_oras_go_v2", "org_golang_google_grpc", "org_golang_google_grpc_security_advancedtls", "org_golang_google_protobuf", "org_golang_x_crypto", "org_golang_x_net", "org_golang_x_term", "org_golang_x_time")
+
+go_patches = use_extension("@gazelle//:extensions.bzl", "go_deps", dev_dependency = True)
+
+# The public goyang/ygot owners supply the same Go types as Management
+# Common. Keep the remaining upstream Go dependency settings unchanged.
+go_patches.gazelle_override(
+    directives = ["gazelle:proto disable_global"],
+    path = "github.com/openconfig/gnmi",
+)
+
+# These modules ship C++/proto Bazel files for their own workspace. Generate
+# their checked-in Go bindings as native Go packages for this consuming graph.
+[go_patches.gazelle_override(
+    build_file_generation = "clean",
+    directives = ["gazelle:proto disable_global"],
+    path = path,
+) for path in [
+    "github.com/openconfig/gnoi",
+    "github.com/openconfig/gnsi",
+]]
+
+# These are the existing Make/vendor patches, applied to isolated dependency
+# repositories. Build actions never modify go.mod, vendor, or the checkout.
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic_mgmt_common//patches:jsonquery.patch"],
+    path = "github.com/antchfx/jsonquery",
+)
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic_mgmt_common//patches:xmlquery.patch"],
+    path = "github.com/antchfx/xmlquery",
+)
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic_mgmt_common//patches:xpath.patch"],
+    path = "github.com/antchfx/xpath",
+)
+
+[go_patches.module_override(
+    patch_strip = 1,
+    patches = ["//patches/bazel:" + patch] + (["//patches/bazel:" + {
+        "0001-gnxi.patch": "0005-gnxi-build.patch",
+        "0002-gnmi.patch": "0006-gnmi-build.patch",
+    }[patch]] if path in [
+        "github.com/google/gnxi",
+        "github.com/openconfig/gnmi",
+    ] else []),
+    path = path,
+) for path, patch in [
+    ("github.com/google/gnxi", "0001-gnxi.patch"),
+    ("github.com/openconfig/gnmi", "0002-gnmi.patch"),
+    ("github.com/fsnotify/fsnotify", "0003-fsnotify.patch"),
+    ("google.golang.org/grpc/security/advancedtls", "0004-advancedtls.patch"),
+]]
+# Native gNMI deliberately omits Common's glog.patch for glog v1.2.4.
+
+# Match the owner generators and source toolchain in this consuming root.
+bazel_dep(name = "rules_python", version = "1.9.0")
+
+python = use_extension("@rules_python//python/extensions:python.bzl", "python")
+python.toolchain(python_version = "3.13")
+
+go_sdk = use_extension("@io_bazel_rules_go//go:extensions.bzl", "go_sdk", dev_dependency = True)
+go_sdk.download(
+    name = "go_sdk",
+    version = "1.25.9",
+)
+
+bazel_dep(name = "sonic-swss-common", version = "0.0.8-a0450924719a9f706125cc44a07dc88934935003", repo_name = "sonic_swss_common")
+# CodeQL stages the public native libraries required by Common.
+bazel_dep(name = "libnl3", version = "3.7.0.sonic.7", dev_dependency = True)
+bazel_dep(name = "bazel_skylib", version = "1.9.2")
+bazel_dep(name = "platforms", version = "1.1.0")
+bazel_dep(name = "rules_cc", version = "0.2.22")
+bazel_dep(name = "rules_distroless", version = "0.9.4.sonic.14")
+bazel_dep(name = "rules_pkg", version = "1.1.0")
+bazel_dep(name = "rules_shell", version = "0.8.0")
+bazel_dep(name = "tar.bzl", version = "0.10.5.sonic.1")
+
+gcc = use_extension("@sonic_build_infra//toolchains/gcc:extensions.bzl", "gcc")
+use_repo(gcc, "gcc_toolchains")
+
+register_toolchains("@gcc_toolchains//:all")
+
+tar_toolchains = use_extension("@tar.bzl//tar:extensions.bzl", "toolchains")
+use_repo(tar_toolchains, "bsd_tar_toolchains")
+
+register_toolchains("@bsd_tar_toolchains//:all")
+
+# Common registers the Rust toolchain extension even for a Go-only consumer.
+bazel_dep(name = "rules_rs", version = "0.1.0")
+
+rules_rust = use_extension("@rules_rs//rs:rules_rust.bzl", "rules_rust")
+use_repo(rules_rust, "rules_rust")
+
+rust = use_extension("@rules_rs//rs:rules_rust_reexported_extensions.bzl", "rust", dev_dependency = True)
+rust.toolchain(
+    edition = "2021",
+    versions = ["1.90.0"],
+)
+use_repo(rust, "rust_toolchains")
+
+register_toolchains(
+    "@rust_toolchains//:all",
+    dev_dependency = True,
+)
+
+pip = use_extension("@rules_python//python/extensions:pip.bzl", "pip")
+pip.parse(
+    hub_name = "gnmi_pip",
+    python_version = "3.13",
+    requirements_lock = "//:requirements_lock.txt",
+)
+use_repo(pip, "gnmi_pip", "mgmt_pip")
+
+# Upstream proto rules require protoc29 options absent from Trixie protoc3.21.
+# Keep the existing upstream source compiler and the legacy Go plugin versions.
+bazel_dep(name = "protobuf", version = "29.1", repo_name = "com_google_protobuf")
+
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["//patches/bazel:0007-gnoi-build.patch"],
+    path = "github.com/openconfig/gnoi",
+)
+
+# Reuse the shared target APT set for the native Python embedding and PAM APIs.
+apt = use_extension("@rules_distroless//apt:extensions.bzl", "apt")
+apt.install(
+    dependency_set = "trixie",
+    packages = [
+        "libpam0g:amd64",
+        "libpam0g-dev:amd64",
+    ],
+    suites = [
+        "trixie",
+        "trixie-updates",
+        "trixie-security",
+    ],
+)
+use_repo(apt, "trixie")
+
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["//patches/bazel:0008-pam-build.patch"],
+    path = "github.com/msteinert/pam",
+)
+
+bazel_dep(name = "patchelf", version = "0.18.0.bcr.1")
+bazel_dep(name = "libyang", version = "3.12.2.sonic.5")
diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/README.md b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/README.md
new file mode 100644
index 0000000000000000000000000000000000000000..af0874c07ed85395e5f8e0c18d4317bb37fe8dff
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/README.md
@@ -0,0 +1,24 @@
+# Native AMD64 gNMI runtime and source TARs
+
+Register public gNMI commit `83a7de8d7760f7cac9690f5e304d94a9171f2366` from [gNMI #2](https://github.com/securely1g/sonic-gnmi/pull/2), including [the subscription fixes](https://github.com/securely1g/sonic-gnmi/pull/1), for [buildimage #148](https://github.com/securely1g/sonic-buildimage/pull/148) and [issue #126](https://github.com/securely1g/sonic-buildimage/issues/126).
+
+The owner builds the existing nine telemetry, dialout and gNMI/gNOI programs and exports runtime TARs, matching debug symbols, component sources and runtime metadata. SWSS Common owns the CGo binding; Management Common owns generated schemas and Go interfaces. No DEB producer is selected.
+
+| Input | Before | After |
+| --- | --- | --- |
+| Management Common | Unlanded `1.0.1-24211db5...` copied into the review branch | Maintained `1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b` from [#216](https://github.com/securely1g/sonic-bazel-registry/pull/216) |
+| gNMI source | `6a854f16...` | `83a7de8d7760f7cac9690f5e304d94a9171f2366`, whose root and separate consumer select the landed owner |
+| Shared Go types | Public goyang and ygot | The same published [goyang #212](https://github.com/securely1g/sonic-bazel-registry/pull/212) and [ygot #214](https://github.com/securely1g/sonic-bazel-registry/pull/214) entries |
+
+The registered MODULE is the source MODULE with only its immutable version changed. The ordinary consumer retains SWSS Common `0.0.8-a0450924719a9f706125cc44a07dc88934935003`, infrastructure `0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e`, `rules_go@0.64.1-sonic.1`, Go 1.25.9, its existing Go workspace and Distroless `.16`. It uses public owner mappings without source overrides or duplicate goyang/ygot patches.
+
+All six build targets and three tests are unchanged: the separate consumer, runtime/debug/metadata/source TARs and generated YANG server, plus package/source contracts and installed telemetry against private Redis. Source CI separately owns the original suites, CodeQL and compiler canaries. The archive was verified against every source Git blob and mode; that check does not establish native acceptance. The source native dispatch was rejected by GitHub with HTTP 422: Actions disabled, despite enabled settings. Source native/CodeQL evidence is missing; registry native validation remains pending. Historical receipts retain their original source/catalog identities.
+
+This initial registration targets native AMD64 Trixie. Keep Draft until gNMI #2 lands and current registry/consumer CI passes. ARM, ASAN and full VS installer acceptance are outside this registration.
+
+<details>
+<summary>Historical dependency review links</summary>
+
+Earlier dependency iterations: [SWSS Common #199](https://github.com/securely1g/sonic-bazel-registry/pull/199), [infrastructure #218](https://github.com/securely1g/sonic-bazel-registry/pull/218), [Management Common #219](https://github.com/securely1g/sonic-bazel-registry/pull/219), [libnl #181](https://github.com/securely1g/sonic-bazel-registry/pull/181), and [Distroless #200](https://github.com/securely1g/sonic-bazel-registry/pull/200).
+
+</details>
diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/patches/0001-module-version.patch b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/patches/0001-module-version.patch
new file mode 100644
index 0000000000000000000000000000000000000000..353ccc98797f6775bb24bb394c3943099a9da73b
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/patches/0001-module-version.patch
@@ -0,0 +1,16 @@
+From: Guohan Lu <securely1g@gmail.com>
+Subject: [PATCH] Record the immutable gNMI registry version
+
+The source is the reviewed public gNMI commit 83a7de8d7760f7cac9690f5e304d94a9171f2366.
+Only the registry module version differs from the source declaration.
+
+--- a/MODULE.bazel
++++ b/MODULE.bazel
+@@ -1,6 +1,6 @@
+ module(
+     name = "sonic-gnmi",
+-    version = "0.1.0",
++    version = "0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366",
+     bazel_compatibility = [
+         ">=8.5.1",
+         "<=8.5.1",
diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/presubmit.json b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/presubmit.json
new file mode 100644
index 0000000000000000000000000000000000000000..44068a7ca6748381fa231f455958c1d9afaafb19
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/presubmit.json
@@ -0,0 +1,26 @@
+{
+  "architectures": [
+    "amd64"
+  ],
+  "consumer_deps": [],
+  "platforms": {
+    "amd64": "@sonic_build_infra//platforms:x86_64_trixie"
+  },
+  "build_targets": [
+    "//:consumer",
+    "@sonic-gnmi//dist:runtime",
+    "@sonic-gnmi//dist:runtime.debug_symbols",
+    "@sonic-gnmi//dist:runtime_packages.json",
+    "@sonic-gnmi//dist:sources",
+    "@sonic-gnmi//gnoi_yang:server"
+  ],
+  "test_targets": [
+    "@sonic-gnmi//dist:package_test",
+    "@sonic-gnmi//dist:source_test",
+    "@sonic-gnmi//dist:installed_runtime_test"
+  ],
+  "integration_test_module": "tests/consumer",
+  "host_platforms": {
+    "amd64": "@sonic_build_infra//platforms:x86_64_trixie"
+  }
+}
diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/source.json b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/source.json
new file mode 100644
index 0000000000000000000000000000000000000000..17d6c047e73a8d54fcca0c78ac15511dc2bb681e
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/source.json
@@ -0,0 +1,9 @@
+{
+  "url": "https://github.com/securely1g/sonic-gnmi/archive/83a7de8d7760f7cac9690f5e304d94a9171f2366.tar.gz",
+  "strip_prefix": "sonic-gnmi-83a7de8d7760f7cac9690f5e304d94a9171f2366",
+  "integrity": "sha256-JmMlQZb3jW/PaGJLHNSFdcKxIPf0VkHoARcektVRjPQ=",
+  "patches": {
+    "0001-module-version.patch": "sha256-Vv5w9kPVdM09PYlcdaFc+EmkCQscO5xLIf8HhKBUReg="
+  },
+  "patch_strip": 1
+}
diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/BUILD.bazel b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/BUILD.bazel
new file mode 100644
index 0000000000000000000000000000000000000000..99b68eb73520234843b671f908369a7fe42ea90f
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/BUILD.bazel
@@ -0,0 +1,14 @@
+load("@io_bazel_rules_go//go:def.bzl", "go_binary")
+
+go_binary(
+    name = "consumer",
+    srcs = ["main.go"],
+    gotags = [
+        "gnmi_translib_write",
+        "gnmi_native_write",
+    ],
+    deps = [
+        "@sonic-gnmi//gnmi_server",
+        "@sonic-gnmi//sonic_db_config",
+    ],
+)
diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/MODULE.bazel b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/MODULE.bazel
new file mode 100644
index 0000000000000000000000000000000000000000..0927e4513d0e1682089bc942b98cef919e8c8302
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/MODULE.bazel
@@ -0,0 +1,107 @@
+module(name = "gnmi_external_consumer")
+
+bazel_dep(name = "sonic-gnmi", version = "0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366")
+bazel_dep(name = "sonic-mgmt-common", version = "1.0.1-05f83dcab8fe2e1a0e0fc37ac172b289d6968e2b", repo_name = "sonic_mgmt_common")
+bazel_dep(name = "sonic-swss-common", version = "0.0.8-a0450924719a9f706125cc44a07dc88934935003", repo_name = "sonic_swss_common")
+bazel_dep(name = "sonic-build-infra", version = "0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e", repo_name = "sonic_build_infra")
+bazel_dep(name = "gazelle", version = "0.54.0")
+bazel_dep(name = "openconfig_goyang", version = "0.0.0.sonic.1-20200309174518-a00bece872fc", repo_name = "com_github_openconfig_goyang")
+bazel_dep(name = "openconfig_ygot", version = "0.7.1.sonic.1", repo_name = "com_github_openconfig_ygot")
+bazel_dep(name = "rules_go", version = "0.64.1-sonic.1", repo_name = "io_bazel_rules_go")
+bazel_dep(name = "rules_cc", version = "0.2.22")
+bazel_dep(name = "rules_python", version = "1.9.0")
+bazel_dep(name = "rules_rs", version = "0.1.0")
+bazel_dep(name = "tar.bzl", version = "0.10.5.sonic.1")
+
+go_sdk = use_extension("@io_bazel_rules_go//go:extensions.bzl", "go_sdk")
+go_sdk.download(version = "1.25.9")
+
+python = use_extension("@rules_python//python/extensions:python.bzl", "python")
+python.toolchain(
+    is_default = True,
+    python_version = "3.13",
+)
+
+rules_rust = use_extension("@rules_rs//rs:rules_rust.bzl", "rules_rust")
+use_repo(rules_rust, "rules_rust")
+
+rust = use_extension("@rules_rs//rs:rules_rust_reexported_extensions.bzl", "rust")
+rust.toolchain(
+    edition = "2021",
+    versions = ["1.90.0"],
+)
+use_repo(rust, "rust_toolchains")
+
+register_toolchains("@rust_toolchains//:all")
+
+go_deps = use_extension("@gazelle//:extensions.bzl", "go_deps")
+go_deps.from_file(go_work = "@sonic-gnmi//:go.bazel.work")
+
+go_patches = use_extension("@gazelle//:extensions.bzl", "go_deps", dev_dependency = True)
+
+# The public goyang/ygot owners supply the same Go types as Management
+# Common. Keep the remaining upstream Go dependency settings unchanged.
+go_patches.gazelle_override(
+    directives = ["gazelle:proto disable_global"],
+    path = "github.com/openconfig/gnmi",
+)
+
+# These modules ship C++/proto Bazel files for their own workspace. Generate
+# their checked-in Go bindings as native Go packages for this consuming graph.
+[go_patches.gazelle_override(
+    build_file_generation = "clean",
+    directives = ["gazelle:proto disable_global"],
+    path = path,
+) for path in [
+    "github.com/openconfig/gnoi",
+    "github.com/openconfig/gnsi",
+]]
+
+# These are the existing Make/vendor patches, applied to isolated dependency
+# repositories. Build actions never modify go.mod, vendor, or the checkout.
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic_mgmt_common//patches:jsonquery.patch"],
+    path = "github.com/antchfx/jsonquery",
+)
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic_mgmt_common//patches:xmlquery.patch"],
+    path = "github.com/antchfx/xmlquery",
+)
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic_mgmt_common//patches:xpath.patch"],
+    path = "github.com/antchfx/xpath",
+)
+
+[go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic-gnmi//patches/bazel:" + patch] + (["@sonic-gnmi//patches/bazel:" + {
+        "0001-gnxi.patch": "0005-gnxi-build.patch",
+        "0002-gnmi.patch": "0006-gnmi-build.patch",
+    }[patch]] if path in [
+        "github.com/google/gnxi",
+        "github.com/openconfig/gnmi",
+    ] else []),
+    path = path,
+) for path, patch in [
+    ("github.com/google/gnxi", "0001-gnxi.patch"),
+    ("github.com/openconfig/gnmi", "0002-gnmi.patch"),
+    ("github.com/fsnotify/fsnotify", "0003-fsnotify.patch"),
+    ("google.golang.org/grpc/security/advancedtls", "0004-advancedtls.patch"),
+]]
+# Native gNMI deliberately omits Common's glog.patch for glog v1.2.4.
+
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic-gnmi//patches/bazel:0007-gnoi-build.patch"],
+    path = "github.com/openconfig/gnoi",
+)
+go_patches.module_override(
+    patch_strip = 1,
+    patches = ["@sonic-gnmi//patches/bazel:0008-pam-build.patch"],
+    path = "github.com/msteinert/pam",
+)
+
+bazel_dep(name = "rules_distroless", version = "0.9.4.sonic.16")
diff --git a/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/main.go b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/main.go
new file mode 100644
index 0000000000000000000000000000000000000000..c361799a5b8264b97c7a7f21f787535f334ae8ab
--- /dev/null
+++ b/modules/sonic-gnmi/0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366/tests/consumer/main.go
@@ -0,0 +1,16 @@
+package main
+
+import (
+	"fmt"
+	server "github.com/sonic-net/sonic-gnmi/gnmi_server"
+	dbconfig "github.com/sonic-net/sonic-gnmi/sonic_db_config"
+)
+
+func main() {
+	config := server.Config{Port: 8080}
+	namespace, err := dbconfig.GetDbDefaultNamespace()
+	if err != nil {
+		panic(err)
+	}
+	fmt.Printf("public gNMI config port=%d default_namespace=%q\n", config.Port, namespace)
+}
diff --git a/modules/sonic-gnmi/metadata.json b/modules/sonic-gnmi/metadata.json
new file mode 100644
index 0000000000000000000000000000000000000000..a2b4061c41cafb0376111abf955a8947d9364cdb
--- /dev/null
+++ b/modules/sonic-gnmi/metadata.json
@@ -0,0 +1,6 @@
+{
+  "homepage": "https://github.com/sonic-net/sonic-gnmi",
+  "versions": [
+    "0.1.0-83a7de8d7760f7cac9690f5e304d94a9171f2366"
+  ]
+}
```
