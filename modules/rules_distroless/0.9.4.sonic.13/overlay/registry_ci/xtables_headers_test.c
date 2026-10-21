#include <xtables.h>
#include <xtables-version.h>

/* The real development package must export its own headers and include root. */
int main(void)
{
    return sizeof(struct xtables_match) > 0 && sizeof(XTABLES_VERSION) > 1 ? 0 : 1;
}
