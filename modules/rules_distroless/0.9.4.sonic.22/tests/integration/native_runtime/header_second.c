#include <variant/base.h>

int first_value(void);

int second_value(void) {
    return first_value() + VARIANT_BASE;
}
