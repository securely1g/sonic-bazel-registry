/* The installed public API promises protocol-name maps without a daemon. */
#include <lldpctl.h>
#include <lldp-const.h>
#include <string.h>

int main(void) {
    lldpctl_map_t *map = lldpctl_key_get_map(lldpctl_k_port_protocol);
    if (!map) return 1;
    for (; map->string; map++)
        if (map->value == LLDPD_MODE_LLDP && strcmp(map->string, "LLDP") == 0)
            return 0;
    return 2;
}
