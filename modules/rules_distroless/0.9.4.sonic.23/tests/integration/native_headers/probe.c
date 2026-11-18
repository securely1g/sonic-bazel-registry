#include <stdio.h>

#if HEADER_CASE == 3
#ifndef HEADER_OVERLAY
#error explicit overlay lost its compiler definition
#endif
#ifndef HEADER_OVERLAY_SEEN
#error explicit overlay header was not used
#endif
#else
#ifdef HEADER_OVERLAY
#error ordinary dependency opted into overlay mode
#endif
#ifdef HEADER_OVERLAY_SEEN
#error ordinary dependency included the overlay header
#endif
#endif

#if HEADER_CASE == 1
#include <variant/base.h>
#define RESULT VARIANT_BASE
#elif HEADER_CASE == 2
#include <middle.h>
#define RESULT MIDDLE_BASE
#elif HEADER_CASE == 3
#define RESULT 42
#elif HEADER_CASE == 4
#include <plain/value.h>
#define RESULT PLAIN_VALUE
#elif HEADER_CASE == 5
#include <alpha_api.h>
#include <beta_api.h>
#define RESULT (ALPHA_VALUE + BETA_VALUE)
#endif

int header_probe(void) {
    FILE *stream = stdout;
    return stream != NULL ? RESULT : 0;
}
