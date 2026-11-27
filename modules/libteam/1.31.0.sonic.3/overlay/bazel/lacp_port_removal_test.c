#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "teamd/teamd_runner_lacp.c"

/* Observe the handler's first side effect without running a daemon or sending
 * packets. Only an initialized LACP port may disable its receive callback. */
static struct lacp_port existing_port;
static struct lacp_port *lookup_result;

void *teamd_get_first_port_priv_by_creator(struct teamd_port *port, void *creator)
{
	(void)port;
	(void)creator;
	return lookup_result;
}

int teamd_loop_callback_disable(struct teamd_context *ctx, const char *name,
				void *priv)
{
	(void)ctx;
	if (!priv || priv != lookup_result || strcmp(name, LACP_SOCKET_CB_NAME)) {
		fputs("unexpected LACP callback disable\n", stderr);
		exit(EXIT_FAILURE);
	}
	exit(EXIT_SUCCESS);
}

int main(void)
{
	struct teamd_context context = {};
	struct lacp lacp = {};
	struct teamd_port port = { .ifname = "fixture" };

	/* Missing private data must return without disabling a callback. */
	lacp_event_watch_port_removing(&context, &port, &lacp);

	/* The disable hook exits successfully only for the existing port. */
	lookup_result = &existing_port;
	lacp_event_watch_port_removing(&context, &port, &lacp);
	fputs("initialized LACP port did not disable its callback\n", stderr);
	return EXIT_FAILURE;
}
