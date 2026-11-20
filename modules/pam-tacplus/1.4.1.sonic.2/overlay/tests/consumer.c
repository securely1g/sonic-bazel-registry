/* Installed public libtac/support API, no authentication or I/O. */
#include <sys/types.h>
#include <libtac/cdefs.h>
#include <libtac/tacplus.h>
#include <libtac/libtac.h>
#include <libtac/support.h>
#include <string.h>
int main(void) {
    struct tac_attrib *attributes = 0;
    int (*volatile parser)(const char *) = parse_config_file;
    tac_add_attrib(&attributes, "service", "shell");
    if (!attributes || strcmp(attributes->attr, "service=shell") || !parser) return 1;
    tac_free_attrib(&attributes);
    return attributes != 0;
}
