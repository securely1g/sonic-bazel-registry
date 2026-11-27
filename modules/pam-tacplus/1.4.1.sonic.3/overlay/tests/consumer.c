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
    char trace_id[248];
    memset(trace_id, 'x', sizeof(trace_id) - 1);
    trace_id[sizeof(trace_id) - 1] = '\0';
    tac_add_attrib_pair(&attributes, "traceid", '*', trace_id);
    const struct tac_attrib *trace = attributes->next;
    if (!trace || trace->attr_len != 255 || trace->next ||
        memcmp(trace->attr, "traceid*", 8) || strcmp(trace->attr + 8, trace_id)) {
        return 1;
    }
    char secret[256] = {0};
    if (!(_pam_parse_arg("traceid_authorization", secret, sizeof(secret)) &
          TRACE_ID_AUTHORIZATION_FLAG)) {
        return 1;
    }
    tac_free_attrib(&attributes);
    return attributes != 0;
}
