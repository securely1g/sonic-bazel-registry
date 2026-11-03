"""Selected SONiC host-sFlow build settings, shared by its native targets."""

NATIVE = ["@platforms//os:linux", "@platforms//cpu:x86_64", "@sonic_build_infra//platforms:trixie"]

# SONiC's Debian recipe selects FEATURES="SONIC VPP" and -g -gdwarf-4 -O2.
LINUX_COPTS = [
    "-std=gnu99",
    "-g",
    "-gdwarf-4",
    "-O2",
    "-fPIC",
    "-Wall",
    "-Wstrict-prototypes",
    "-Wunused-value",
    "-Wunused-function",
]
LINUX_DEFINES = [
    "_GNU_SOURCE",
    "HSP_VERSION=2.1.26",
    "GDB=",
    "UTHEAP",
    "HSP_LOAD_SONIC",
    "HSP_OPTICAL_STATS",
    "HSP_REPORT_PFC",
    "SFL_USE_SFDG",
    "SFL_USE_32BIT_INDEX",
    "HSP_MOD_DIR=/etc/hsflowd/modules",
    "PROCFS=/proc",
    "SYSFS=/sys",
    "ETCFS=/etc",
    "VARFS=/var",
]

# Keep the linked ELF intact until the shared deployment rule splits symbols.
KEEP_SYMBOLS = ["-strip_debug_symbols"]
