#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dlfcn.h>
#include <netlink/addr.h>
#include <netlink/msg.h>
#include <netlink/route/link.h>
#include <netlink/route/route.h>
#include <netlink/socket.h>
#include <linux/if_link.h>
#include <linux/rtnetlink.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

/* This Trixie UAPI attribute is absent from libnl's private kernel headers.
 * A consumer must see the toolchain headers through the public libnl targets. */
_Static_assert(IFLA_PROP_LIST > IFLA_MAX_MTU, "libnl private kernel headers leaked to a consumer");

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "Check failed at line %d: %s\n", __LINE__, #condition); \
        goto cleanup; \
    } \
} while (0)

static int check_library_origin(void *symbol, const char *library) {
    const char *directory = getenv("LIBNL3_EXPECTED_LIBRARY_DIR");
    if (!directory) return 0;

    Dl_info info;
    if (!dladdr(symbol, &info) || !info.dli_fname) return 1;
    char *expected_path = NULL;
    if (asprintf(&expected_path, "%s/%s", directory, library) < 0) return 1;
    char *expected = realpath(expected_path, NULL);
    char *actual = realpath(info.dli_fname, NULL);
    int failed = !expected || !actual || strcmp(expected, actual);
    if (failed) fprintf(stderr, "Expected %s, loaded %s\n", expected_path, info.dli_fname);
    free(actual);
    free(expected);
    free(expected_path);
    return failed;
}

int main(void) {
    int result = 1;
    struct nl_sock *socket = nl_socket_alloc();
    struct rtnl_route *route = rtnl_route_alloc();
    struct rtnl_route *parsed = NULL;
    struct nl_addr *destination = NULL;
    struct nl_msg *message = NULL;
    CHECK(socket && route);

    nl_socket_set_local_port(socket, 12345);
    CHECK(nl_socket_get_local_port(socket) == 12345);
    CHECK(!nl_addr_parse("192.0.2.0/24", AF_INET, &destination));
    CHECK(!rtnl_route_set_family(route, AF_INET));
    CHECK(!rtnl_route_set_type(route, RTN_UNICAST));
    CHECK(!rtnl_route_set_dst(route, destination));
    rtnl_route_set_table(route, RT_TABLE_MAIN);
    rtnl_route_set_protocol(route, RTPROT_STATIC);
    rtnl_route_set_scope(route, RT_SCOPE_UNIVERSE);
    rtnl_route_set_nh_id(route, 42);
    CHECK(!rtnl_route_build_add_request(route, 0, &message));
    CHECK(!rtnl_route_parse(nlmsg_hdr(message), &parsed));
    CHECK(rtnl_route_get_nh_id(parsed) == 42);
    CHECK(rtnl_route_get_table(parsed) == RT_TABLE_MAIN);
    CHECK(!nl_addr_cmp(rtnl_route_get_dst(parsed), destination));
    CHECK(!check_library_origin((void *)nl_socket_alloc, "libnl-3.so.200"));
    CHECK(!check_library_origin((void *)rtnl_route_alloc, "libnl-route-3.so.200"));
    result = 0;

cleanup:
    if (message) nlmsg_free(message);
    if (destination) nl_addr_put(destination);
    if (parsed) rtnl_route_put(parsed);
    if (route) rtnl_route_put(route);
    if (socket) nl_socket_free(socket);
    return result;
}
