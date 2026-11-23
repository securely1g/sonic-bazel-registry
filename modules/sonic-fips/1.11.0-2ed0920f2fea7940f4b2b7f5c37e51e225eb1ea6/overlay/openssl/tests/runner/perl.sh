#!/bin/sh
# TAP exports its module path through PERL5LIB, which managed Perl resets.
# Keep this component's declared modules in explicit arguments for every child.
set -eu
exec "$OPENSSL_SUITE_MANAGED_PERL" \
    "-I$OPENSSL_SOURCE_ROOT/util/perl" \
    "-I$OPENSSL_SUITE_PERL_MODULES" \
    -MSonicFipsOpenSSLTestPerl "$@"
