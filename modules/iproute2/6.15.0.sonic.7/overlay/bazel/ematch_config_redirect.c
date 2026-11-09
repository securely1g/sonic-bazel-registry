/* Test-only relocation of tc's ematch map into the extracted runtime TAR. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef FILE *(*fopen_function)(const char *, const char *);

static FILE *open_map(const char *symbol, const char *path, const char *mode)
{
    const int redirect = !strcmp(path, "/etc/iproute2/ematch_map") ||
                         !strcmp(path, "/usr/share/iproute2/ematch_map");
    fopen_function real_open = (fopen_function)dlsym(RTLD_NEXT, symbol);
    FILE *result;

    if (!real_open) {
        fprintf(stderr, "iproute2 test: cannot resolve %s\n", symbol);
        errno = ENOSYS;
        return NULL;
    }
    if (redirect) {
        path = getenv("IPROUTE2_TEST_EMATCH_MAP");
        if (!path || path[0] != '/' || strcmp(mode, "r")) {
            fputs("iproute2 test: ematch map requires an absolute staged path and read mode\n", stderr);
            errno = EINVAL;
            return NULL;
        }
    }
    result = real_open(path, mode);
    if (redirect && !result) {
        const int error = errno;
        fprintf(stderr, "iproute2 test: Unable to open staged ematch map %s: %s\n",
                path, strerror(error));
        errno = error;
    }
    return result;
}

FILE *fopen(const char *path, const char *mode)
{
    return open_map("fopen", path, mode);
}

/* iproute2 enables large-file support, which can redirect fopen to fopen64. */
FILE *fopen64(const char *path, const char *mode)
{
    return open_map("fopen64", path, mode);
}
