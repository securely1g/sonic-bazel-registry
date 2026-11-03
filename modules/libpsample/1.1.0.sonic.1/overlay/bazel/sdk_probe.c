/* Link and exercise the selected upstream public interface. */
#include <errno.h>
#include <stddef.h>
#include <psample.h>
int main(void) {
    psample_set_log_level(PSAMPLE_LOG_NONE);
    psample_close(NULL);
    return psample_bind_group(NULL, 7) != -EINVAL ||
        psample_dispatch(NULL, NULL, NULL, NULL, NULL, false) != -ENOMEM;
}
