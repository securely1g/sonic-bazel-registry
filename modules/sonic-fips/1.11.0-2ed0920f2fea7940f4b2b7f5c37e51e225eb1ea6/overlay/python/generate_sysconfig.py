"""Generate installed target metadata using the fixed CPython sysconfig helpers.

The installed Debian metadata takes its configuration from the shared build.
The Makefile input has already received debian/rules sysconfig_substflags.
"""
import sys

makefile, config_header, output, source_lib = sys.argv[1:]
sys.path[:] = [source_lib]
from sysconfig import parse_config_h
from sysconfig.__main__ import _parse_makefile, _print_config_dict

variables = {}
_parse_makefile(makefile, variables)
with open(config_header, encoding="utf-8") as stream:
    parse_config_h(stream, variables)
# This is the Linux build-tree branch of _generate_posix_vars in the fixed
# Lib/sysconfig/__main__.py. Darwin/AIX branches do not apply to this target.
variables["BLDSHARED"] = variables["LDSHARED"]
with open(output, "w", encoding="utf-8") as stream:
    stream.write("# system configuration generated and used by the sysconfig module\n")
    stream.write("build_time_vars = ")
    _print_config_dict(variables, stream)
