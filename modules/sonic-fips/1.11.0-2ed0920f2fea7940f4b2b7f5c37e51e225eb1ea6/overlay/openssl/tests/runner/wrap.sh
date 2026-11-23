#!/bin/sh
# The ELF at each upstream program path is a declared native_runtime_binary.
set -eu
export OPENSSL_RUNNING_UNIT_TESTS=yes
case ${1:-} in
    -fips)
        if [ -z "${OPENSSL_CONF:-}" ]; then
            OPENSSL_CONF=$OPENSSL_SOURCE_ROOT/test/fips-and-base.cnf
            export OPENSSL_CONF
        fi
        if [ -z "${OPENSSL_CONF_INCLUDE:-}" ]; then
            OPENSSL_CONF_INCLUDE=$OPENSSL_CONFIG_ROOT/providers
            export OPENSSL_CONF_INCLUDE
        fi
        shift
        ;;
    -jitter)
        if [ -z "${OPENSSL_CONF:-}" ]; then
            OPENSSL_CONF=$OPENSSL_SOURCE_ROOT/test/default-and-jitter.cnf
            export OPENSSL_CONF
        fi
        if [ -z "${OPENSSL_CONF_INCLUDE:-}" ]; then
            OPENSSL_CONF_INCLUDE=$OPENSSL_CONFIG_ROOT/providers
            export OPENSSL_CONF_INCLUDE
        fi
        shift
        ;;
esac
exec "$@"
