#include "precedence.h"
#if HEADER_CHOICE != 1
#error quote lookup lost precedence
#endif
#undef HEADER_CHOICE
#include <precedence.h>
#if HEADER_CHOICE != 2
#error ordinary angle lookup lost precedence
#endif
#include "quote_only.h"
int value() { return QUOTE_ONLY; }
