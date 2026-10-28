#include <netlink/cli/utils.h>
#include <netlink/route/pktloc.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "config")) {
        struct rtnl_pktloc *location = NULL;
        rtnl_pktloc_lookup("ip.ttl", &location);
        if (location) rtnl_pktloc_put(location);
        return 0;
    }
    if (!strcmp(argv[1], "plugin")) {
        /* A missing module exposes the actual default dlopen path safely. */
        nl_cli_load_module("cli/qdisc", "__libnl3_missing_path_probe__");
        return 3;
    }
    return 2;
}
