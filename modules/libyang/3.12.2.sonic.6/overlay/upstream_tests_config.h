/* Runtime relocation of tests/tests_config.h.in; production configuration is unchanged. */
#ifndef LYTEST_CONFIG_H_
#define LYTEST_CONFIG_H_
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TESTS_SRC getenv("LIBYANG_TESTS_SRC")
#define TESTS_BIN getenv("LIBYANG_TESTS_BIN")
/* Release does not enable Callgrind. */
struct ly_tests_path {
    struct ly_tests_path *next;
    char value[];
};
static struct ly_tests_path *ly_tests_paths;
static inline void ly_tests_free_paths(void)
{
    while (ly_tests_paths) {
        struct ly_tests_path *next = ly_tests_paths->next;
        free(ly_tests_paths);
        ly_tests_paths = next;
    }
}
static inline const char *ly_tests_join_path(size_t count, ...)
{
    va_list values;
    size_t size = 1;
    va_start(values, count);
    for (size_t i = 0; i < count; ++i) {
        const char *value = va_arg(values, const char *);
        if (!value) { fprintf(stderr, "Missing declared libyang test fixture directory\n"); abort(); }
        size += strlen(value);
    }
    va_end(values);
    struct ly_tests_path *entry = malloc(sizeof(*entry) + size);
    if (!entry) abort();
    if (!ly_tests_paths && atexit(ly_tests_free_paths)) abort();
    entry->next = ly_tests_paths;
    ly_tests_paths = entry;
    char *result = entry->value;
    result[0] = 0;
    va_start(values, count);
    for (size_t i = 0; i < count; ++i) strcat(result, va_arg(values, const char *));
    va_end(values);
    return result;
}
#define TESTS_DIR_MODULES_YANG ly_tests_join_path(2, TESTS_SRC, "/modules/yang")
#endif
