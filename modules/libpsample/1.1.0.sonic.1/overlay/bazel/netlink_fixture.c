/* Feed protocol messages through the installed library's actual parser.
 * Only the kernel transport boundary is replaced; no psample API is mocked. */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/genetlink.h>
#include <linux/psample.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "mnlg.h"

struct mnlg_socket { int fd; unsigned char command; };
struct mnlg_socket *mnlg_socket_open(const char *family, uint8_t version) {
    assert(strcmp(family, PSAMPLE_GENL_NAME) == 0 && version == 1);
    if (getenv("PSAMPLE_FIXTURE_OPEN_FAIL")) { errno = ENOENT; return NULL; }
    struct mnlg_socket *socket = calloc(1, sizeof(*socket));
    assert(socket != NULL);
    socket->fd = open("/dev/null", O_RDONLY);
    assert(socket->fd >= 0);
    return socket;
}
void mnlg_socket_close(struct mnlg_socket *socket) { close(socket->fd); free(socket); }
int mnlg_socket_get_fd(struct mnlg_socket *socket) { return socket->fd; }
int mnlg_socket_group_add(struct mnlg_socket *socket, const char *group) {
    (void)socket;
    assert(strcmp(group, "config") == 0 || strcmp(group, "packets") == 0);
    return 0;
}
struct nlmsghdr *mnlg_msg_prepare(struct mnlg_socket *socket, uint8_t cmd, uint16_t flags) {
    static char buffer[1024];
    struct nlmsghdr *message = mnl_nlmsg_put_header(buffer);
    message->nlmsg_flags = flags;
    socket->command = cmd;
    return message;
}
int mnlg_socket_send(struct mnlg_socket *socket, const struct nlmsghdr *message) {
    (void)socket;
    return message->nlmsg_len;
}
static int deliver(mnl_cb_t callback, void *data, uint8_t command, uint32_t sequence) {
    char buffer[1024] = {0};
    struct nlmsghdr *message = mnl_nlmsg_put_header(buffer);
    struct genlmsghdr *generic = mnl_nlmsg_put_extra_header(message, sizeof(*generic));
    generic->cmd = command;
    generic->version = 1;
    mnl_attr_put_u32(message, PSAMPLE_ATTR_SAMPLE_GROUP, 7);
    mnl_attr_put_u32(message, PSAMPLE_ATTR_GROUP_SEQ, sequence);
    mnl_attr_put_u32(message, PSAMPLE_ATTR_GROUP_REFCOUNT, 2);
    if (command == PSAMPLE_CMD_SAMPLE) {
        const unsigned char packet[] = {0, 1, 2, 3, 'S', 'O', 'N', 'i', 'C'};
        mnl_attr_put_u16(message, PSAMPLE_ATTR_IIFINDEX, 11);
        mnl_attr_put_u16(message, PSAMPLE_ATTR_OIFINDEX, 12);
        mnl_attr_put_u32(message, PSAMPLE_ATTR_ORIGSIZE, 64);
        mnl_attr_put_u32(message, PSAMPLE_ATTR_SAMPLE_RATE, 1000);
        mnl_attr_put(message, PSAMPLE_ATTR_DATA, sizeof(packet), packet);
    }
    return callback(message, data);
}
int mnlg_socket_recv_run(struct mnlg_socket *socket, mnl_cb_t callback, void *data) {
    if (socket->command == PSAMPLE_CMD_GET_GROUP)
        return deliver(callback, data, PSAMPLE_CMD_NEW_GROUP, 42);
    assert(deliver(callback, data, PSAMPLE_CMD_SAMPLE, 42) == MNL_CB_OK);
    assert(deliver(callback, data, PSAMPLE_CMD_NEW_GROUP, 43) == MNL_CB_OK);
    return deliver(callback, data, PSAMPLE_CMD_DEL_GROUP, 44);
}
