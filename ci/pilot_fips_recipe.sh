#!/bin/sh
# Keep OpenSSL's declared recipe Perl and use the bundled ARM kernel for AF_ALG.
set -eu
for arg do
    case ${arg##*/} in
        30-test_afalg.t)
            exec /usr/local/bin/sonic-arm64-kernel --bind "$SONIC_PILOT_FIPS_WORK" \
                --cwd "$PWD" --timeout 180 -- \
                "$SONIC_TEST_PERL" -I"$SONIC_TEST_PERL_LIB" "$@"
            ;;
    esac
done
exec "$SONIC_TEST_PERL" -I"$SONIC_TEST_PERL_LIB" "$@"
