"""Run upstream packet-capture tests with their declared Trixie loader and libraries."""

load("@rules_cc//cc:cc_binary.bzl", "cc_binary")
load("@sonic_build_infra//cc:runtime_test.bzl", "native_runtime_test")

def pcap_runtime_test(name, data, tags = [], **kwargs):
    """Build the upstream test binary and run it with the target libpcap closure."""
    cc_binary(
        name = name + "_elf",
        testonly = True,
        data = data,
        **kwargs
    )
    native_runtime_test(
        name = name,
        binary = ":" + name + "_elf",
        runtime_payloads = ["@bmv2_deps//:packages", "@p4lang_pi//:p4lang-pi.runtime", ":p4lang-bmv2.runtime"],
        data = data,
        tags = tags,
    )
