/* Exercise the imported kernel ABI, including the syscall used by AF_ALG. */
#include <asm/unistd.h>

#if defined(__x86_64__)
_Static_assert(__NR_io_setup == 206, "AMD64 must use AMD64 kernel headers");
_Static_assert(__NR_read == 0, "AMD64 read syscall number");
#elif defined(__aarch64__)
_Static_assert(__NR_io_setup == 0, "ARM64 must use ARM64 kernel headers");
_Static_assert(__NR_read == 63, "ARM64 read syscall number");
#else
#error "Run this native regression on AMD64 or ARM64"
#endif

#include <errno.h>
#include <linux/aio_abi.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    aio_context_t context = 0;
    if (syscall(__NR_io_setup, 1, &context) != 0) {
        perror("io_setup from imported Linux headers");
        return 1;
    }
    if (syscall(__NR_io_destroy, context) != 0) {
        perror("io_destroy from imported Linux headers");
        return 1;
    }
    printf("io_setup=%d io_destroy=%d: native AIO context created and destroyed\n",
           __NR_io_setup, __NR_io_destroy);
    return 0;
}
