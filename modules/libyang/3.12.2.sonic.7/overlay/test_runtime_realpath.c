/* Keep the original target binary's RPATH origin without interpreter startup. */
#define _XOPEN_SOURCE 700
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }
    char *resolved = realpath(argv[1], NULL);
    if (resolved == NULL) {
        perror("realpath");
        return 1;
    }
    int status = puts(resolved) == EOF ? 1 : 0;
    free(resolved);
    return status;
}
