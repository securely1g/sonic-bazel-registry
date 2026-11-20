"""Direct installation of the mainline-patched Debian ifupdown2 recipe."""
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@bazel_skylib//rules:expand_template.bzl", "expand_template")
load("@rules_python//python:defs.bzl", "py_binary", "py_test")
load("@sonic_build_infra//tools/build_tools:defs.bzl", "build_tool")
load("@sonic_build_infra//oci:runtime_packages.bzl", "runtime_packages")
load("@sonic_build_infra//python:source_package.bzl", "PythonRuntimeInfo")
load("@tar.bzl//tar:tar.bzl", "tar")
load("@sonic_build_infra//oci:source_controls.bzl", "source_package_controls")

# setup.py find_packages(), audited against the fixed source archive + six patches.
_PYTHON_FILES = [
    'ifupdown2/__init__.py',
    'ifupdown2/__main__.py',
    'ifupdown2/addons/__init__.py',
    'ifupdown2/addons/address.py',
    'ifupdown2/addons/addressvirtual.py',
    'ifupdown2/addons/batman_adv.py',
    'ifupdown2/addons/bond.py',
    'ifupdown2/addons/bridge.py',
    'ifupdown2/addons/bridgevlan.py',
    'ifupdown2/addons/dhcp.py',
    'ifupdown2/addons/ethtool.py',
    'ifupdown2/addons/link.py',
    'ifupdown2/addons/mstpctl.py',
    'ifupdown2/addons/openvswitch.py',
    'ifupdown2/addons/openvswitch_port.py',
    'ifupdown2/addons/ppp.py',
    'ifupdown2/addons/tunnel.py',
    'ifupdown2/addons/usercmds.py',
    'ifupdown2/addons/vlan.py',
    'ifupdown2/addons/vrf.py',
    'ifupdown2/addons/vrrpd.py',
    'ifupdown2/addons/vxlan.py',
    'ifupdown2/addons/xfrm.py',
    'ifupdown2/ifupdown/__init__.py',
    'ifupdown2/ifupdown/argv.py',
    'ifupdown2/ifupdown/client.py',
    'ifupdown2/ifupdown/config.py',
    'ifupdown2/ifupdown/exceptions.py',
    'ifupdown2/ifupdown/graph.py',
    'ifupdown2/ifupdown/iface.py',
    'ifupdown2/ifupdown/ifupdownconfig.py',
    'ifupdown2/ifupdown/ifupdownflags.py',
    'ifupdown2/ifupdown/ifupdownmain.py',
    'ifupdown2/ifupdown/main.py',
    'ifupdown2/ifupdown/networkinterfaces.py',
    'ifupdown2/ifupdown/policymanager.py',
    'ifupdown2/ifupdown/scheduler.py',
    'ifupdown2/ifupdown/statemanager.py',
    'ifupdown2/ifupdown/template.py',
    'ifupdown2/ifupdown/utils.py',
    'ifupdown2/ifupdownaddons/__init__.py',
    'ifupdown2/ifupdownaddons/cache.py',
    'ifupdown2/ifupdownaddons/dhclient.py',
    'ifupdown2/ifupdownaddons/modulebase.py',
    'ifupdown2/ifupdownaddons/mstpctlutil.py',
    'ifupdown2/ifupdownaddons/systemutils.py',
    'ifupdown2/ifupdownaddons/utilsbase.py',
    'ifupdown2/lib/__init__.py',
    'ifupdown2/lib/addon.py',
    'ifupdown2/lib/base_objects.py',
    'ifupdown2/lib/dry_run.py',
    'ifupdown2/lib/exceptions.py',
    'ifupdown2/lib/io.py',
    'ifupdown2/lib/iproute2.py',
    'ifupdown2/lib/log.py',
    'ifupdown2/lib/nlcache.py',
    'ifupdown2/lib/status.py',
    'ifupdown2/lib/sysfs.py',
    'ifupdown2/nlmanager/__init__.py',
    'ifupdown2/nlmanager/ipnetwork.py',
    'ifupdown2/nlmanager/nllistener.py',
    'ifupdown2/nlmanager/nlmanager.py',
    'ifupdown2/nlmanager/nlpacket.py',
]
_EXAMPLES = [
    ('docs/examples/batman_adv/configure_batman_adv.sh', 493),
    ('docs/examples/batman_adv/interfaces_batman', 420),
    ('docs/examples/generate_interfaces.py', 493),
    ('docs/examples/interfaces', 420),
    ('docs/examples/interfaces_bridge_igmp_mstp', 420),
    ('docs/examples/interfaces_bridge_template_func', 420),
    ('docs/examples/interfaces_bridge_vlan_bond_vxlan_vrf', 420),
    ('docs/examples/interfaces_with_template', 420),
    ('docs/examples/mgmt-vrf', 420),
    ('docs/examples/vlan_aware_bridges/interfaces.basic', 420),
    ('docs/examples/vlan_aware_bridges/interfaces.vlan_prune_and_access_ports', 420),
    ('docs/examples/vlan_aware_bridges/interfaces.with_bonds', 420),
    ('docs/examples/vlan_aware_bridges/interfaces.with_clag', 420),
]
_MANPAGES = ["ifup.8", "ifdown.8", "ifquery.8", "ifreload.8", "ifupdown-addons-interfaces.5", "interfaces.5"]
_EPOCH = "1596577362"  # debian/changelog's 3.0.0-1 timestamp.
_PYTHON_METADATA = {
    "distribution": "ifupdown2", "version": "3.0.0", "requires_python": "",
    "requires_dist": [], "extras": [], "entry_points": {},
    "python_tag": "py3", "abi": "none", "platform": "any",
}

def _runtime_impl(ctx):
    info = PythonRuntimeInfo(
        packages = depset([struct(distribution = "ifupdown2", version = "3.0.0", producer = str(ctx.label), tar = ctx.file.tar, metadata = ctx.file.metadata)]),
        tars = depset([ctx.file.tar]), metadata = depset([ctx.file.metadata]),
    )
    return [DefaultInfo(files = depset([ctx.file.tar])), info, OutputGroupInfo(python_metadata = info.metadata)]

_runtime = rule(implementation = _runtime_impl, attrs = {
    "tar": attr.label(allow_single_file = True, mandatory = True),
    "metadata": attr.label(allow_single_file = True, mandatory = True),
})

def ifupdown2_targets(source_prefix = ":"):
    """Use source-prefixed labels locally, or original archive files in registry."""
    def_source = source_prefix
    build_tool(name = "_documentation_python", runtime = "@sonic_build_infra//tools/build_tools:manual_runtime", tool = "python3")
    py_binary(name = "_changelog", srcs = ["changelog.py"], main = "changelog.py", deps = ["@sonic_build_infra//oci:runtime_packages_lib"])
    arch = select({"@platforms//cpu:x86_64": "amd64", "@platforms//cpu:aarch64": "arm64"})
    expand_template(
        name = "_main", template = def_source + "ifupdown2/__main__.py", out = "generated/__main__.py",
        substitutions = {"#!/usr/bin/env python3": "#!/usr/bin/python3"},
    )
    # Native pybuild's private installation metadata; Debian mode has no entry points.
    write_file(name = "_pkg_info", out = "egg-info/PKG-INFO", content = [
        "Metadata-Version: 2.1", "Name: ifupdown2", "Version: 3.0.0",
        "Summary: interface network manager", "Home-page: https://github.com/CumulusNetworks/ifupdown2",
        "Author: Julien Fortin", "Author-email: julien@cumulusnetworks.com",
        "Maintainer: Julien Fortin", "Maintainer-email: julien@cumulusnetworks.com",
        "License: GNU General Public License v2", "Keywords: ifupdown2",
        "Classifier: Development Status :: 5 - Production/Stable", "Classifier: Environment :: Console",
        "Classifier: Intended Audience :: System Administrators",
        "Classifier: License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Classifier: Natural Language :: English", "Classifier: Operating System :: POSIX :: Linux",
        "Classifier: Programming Language :: Python :: 3", "Classifier: Topic :: System :: Networking",
        "Classifier: Topic :: System :: Systems Administration", "License-File: LICENSE", "",
    ])
    write_file(name = "_dependency_links", out = "egg-info/dependency_links.txt", content = [""])
    write_file(name = "_top_level", out = "egg-info/top_level.txt", content = ["ifupdown2", ""])
    write_file(name = "_python_metadata", out = "ifupdown2.python-runtime.json", content = [json.encode(_PYTHON_METADATA)])
    write_file(name = "_rtupdate", out = "generated/ifupdown2.rtupdate", content = [
        "#!/bin/sh", "set -e", 'if [ "$1" = rtupdate ]; then',
        "    py3clean -p ifupdown2 /usr/share/ifupdown2", "    py3compile -p ifupdown2 /usr/share/ifupdown2", "fi", "",
    ])
    native.genrule(
        name = "_changelog_gzip",
        srcs = [def_source + path for path in ["debian/control", "debian/changelog", "debian/compat"]] + ["@sonic_build_infra//tools/build_tools:kernel_runtime"],
        tools = [":_changelog", "@sonic_build_infra//tools/build_tools:pigz"],
        outs = ["generated/changelog.Debian.gz"],
        cmd = "$(execpath :_changelog) $(location %sdebian/control) $(location %sdebian/changelog) $(location %sdebian/compat) $(execpath @sonic_build_infra//tools/build_tools:kernel_runtime) $(execpath @sonic_build_infra//tools/build_tools:pigz) $@ " % (def_source, def_source, def_source) + arch,
    )
    docs = []
    for page in _MANPAGES:
        name = "_man_" + page.replace(".", "_")
        source = def_source + "ifupdown2/man/" + page + ".rst"
        native.genrule(
            name = name, srcs = [source, "rst_manpage.py"],
            tools = [":_documentation_python", "@sonic_build_infra//tools/build_tools:pigz"],
            outs = ["generated/" + page + ".gz"],
            cmd = "SOURCE_DATE_EPOCH=%s LC_ALL=C TZ=UTC $(execpath :_documentation_python) $(location rst_manpage.py) $(location %s) $@ $(execpath @sonic_build_infra//tools/build_tools:pigz)" % (_EPOCH, source),
        )
        docs.append((":" + name, "usr/share/man/man" + page[-1] + "/" + page + ".gz", 0o644))
    files = []
    for path in _PYTHON_FILES:
        files.append((":_main" if path == "ifupdown2/__main__.py" else def_source + path, "usr/share/" + path, 0o755 if path == "ifupdown2/__main__.py" else 0o644))
    files += [(def_source + path, path, 0o644) for path in ["etc/default/networking", "etc/network/ifupdown2/addons.conf", "etc/network/ifupdown2/ifupdown2.conf"]]
    files += [
        (def_source + "ifupdown2/sbin/start-networking", "usr/share/ifupdown2/sbin/start-networking", 0o755),
        (def_source + "debian/ifup@.service", "lib/systemd/system/ifup@.service", 0o644),
        (def_source + "debian/ifupdown2.networking.service", "lib/systemd/system/networking.service", 0o644),
        (def_source + "docs/README.rst", "usr/share/doc/ifupdown2/README.rst", 0o644),
        (def_source + "debian/copyright", "usr/share/doc/ifupdown2/copyright", 0o644),
        (def_source + "debian/ifupdown2.lintian-overrides", "usr/share/lintian/overrides/ifupdown2", 0o644),
        (":_changelog_gzip", "usr/share/doc/ifupdown2/changelog.Debian.gz", 0o644),
        (":_rtupdate", "usr/share/python3/runtime.d/ifupdown2.rtupdate", 0o755),
    ]
    files += [(def_source + path, "usr/share/doc/ifupdown2/" + path.removeprefix("docs/"), mode) for path, mode in _EXAMPLES]
    files += [(target, "usr/share/ifupdown2-3.0.0.egg-info/" + name, 0o644) for target, name in [(":_pkg_info", "PKG-INFO"), (":_dependency_links", "dependency_links.txt"), (":_top_level", "top_level.txt")]]
    files += docs
    links = {"usr/share/ifupdown2/ifupdown2": "__main__.py"}
    links.update({"sbin/" + command: "/usr/share/ifupdown2/ifupdown2" for command in ["ifup", "ifdown", "ifquery", "ifreload"]})
    dirs = {path: True for path in ["etc/network/interfaces.d", "etc/network/ifupdown2/policy.d", "var/lib/ifupdown2/hooks", "var/lib/ifupdown2/policy.d"]}
    for path in [destination for _, destination, _ in files] + links.keys() + dirs.keys():
        pieces = path.split("/")
        for count in range(1, len(pieces)):
            dirs["/".join(pieces[:count])] = True
    mtree = [". type=dir uid=0 gid=0 mode=0755 time=" + _EPOCH]
    mtree += ["./" + path + " type=dir uid=0 gid=0 mode=0755 time=" + _EPOCH for path in sorted(dirs)]
    mtree += ["./%s type=file uid=0 gid=0 mode=%s time=%s content=$(location %s)" % (path, "0755" if mode == 0o755 else "0644", _EPOCH, label) for label, path, mode in files]
    mtree += ["./%s type=link uid=0 gid=0 mode=0777 time=%s link=%s" % (path, _EPOCH, target) for path, target in links.items()]
    tar(name = "_runtime_tar", out = "ifupdown2.runtime.tar", srcs = [label for label, _, _ in files], mtree = mtree, compress = None)
    _runtime(name = "ifupdown2.runtime", tar = ":_runtime_tar", metadata = ":_python_metadata")
    runtime_packages(
        name = "ifupdown2.runtime_metadata", module_name = "ifupdown2", architecture = arch,
        control = def_source + "debian/control", changelog = def_source + "debian/changelog",
        packages = {"ifupdown2": ":ifupdown2.runtime"},
        required_paths = {"ifupdown2": ["usr/share/ifupdown2/__main__.py", "sbin/ifup", "lib/systemd/system/networking.service"]},
        debian_files = {name: def_source + "debian/" + name for name in ["compat", "ifupdown2.postinst", "ifupdown2.postrm", "ifupdown2.networking.service"]},
        control_file_helpers = [
            ["dh_python3", "/usr/share/ifupdown2"], ["dh_systemd_enable", "--name=networking"],
            ["dh_systemd_start", "--name=networking", "--no-start"], ["dh_installdeb"],
        ],
    )
    source_package_controls(
        name = "ifupdown2.control",
        metadata = ":ifupdown2.runtime_metadata",
        package = "ifupdown2",
    )
    py_test(
        name = "runtime_test", srcs = ["runtime_test.py"], main = "runtime_test.py",
        python_version = "3.13",
        data = [":ifupdown2.runtime", ":ifupdown2.runtime_metadata", ":ifupdown2.control", def_source + "setup.py"],
        args = ["$(rootpath :ifupdown2.runtime)", "$(rootpath :ifupdown2.runtime_metadata)", "$(rootpath :ifupdown2.control)", "$(rootpath %ssetup.py)" % def_source],
    )
