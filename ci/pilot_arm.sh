#!/usr/bin/env bash
# Run a complete ARM64 CI command in the runner's pod-local Debian Trixie root.
set -euo pipefail

guest=/opt/sonic-arm64-rootfs
script=$(readlink -f "$0")
case "${1:-}" in
    shell)
        if [[ "${PILOT_EMULATED_ARM:-false}" == true ]]; then
            exec "$script" run bash --noprofile --norc -eo pipefail "$2"
        fi
        exec bash --noprofile --norc -eo pipefail "$2"
        ;;
    prepare|run)
        if (( EUID != 0 )); then
            exec sudo -n -E -- "$script" "$@"
        fi
        : "${GITHUB_WORKSPACE:?}" "${RUNNER_TEMP:?}"
        if [[ "$1" == prepare ]]; then
            bazel="$RUNNER_TEMP/bazel-8.5.1-linux-arm64"
            curl --fail --location --retry 3 --output "$bazel" \
                https://releases.bazel.build/8.5.1/release/bazel-8.5.1-linux-arm64
            printf '%s  %s\n' b7f2a85595e8a87d54843bc656c1e379fd9b8c1b5f783dc41717c1d7eb7cc49f "$bazel" | sha256sum --check --strict
            install -m 0755 "$bazel" "$guest/usr/local/lib/bazel-8.5.1"
            # The embedded JDK otherwise misses the worker's CA, including in
            # registry tests that deliberately ignore every Bazel RC file.
            cat > "$guest/usr/local/bin/bazel" <<'LAUNCHER'
#!/bin/sh
if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then
    exec /usr/local/lib/bazel-8.5.1 --version
fi
exec /usr/local/lib/bazel-8.5.1 \
    --host_jvm_args=-Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts \
    --host_jvm_args=-Xmx2g "$@"
LAUNCHER
            chmod 0755 "$guest/usr/local/bin/bazel"
            set -- run bash -ec '
                test "$(dpkg --print-architecture)" = arm64
                test "$(uname -m)" = aarch64
                # rules_distroless runs zstd with argv[0]=gzip when it writes
                # content.tar.gz from a Debian package. Verify the same pipeline.
                test "$(printf pilot | (exec -a gzip /usr/bin/zstd -n) | gzip -dc)" = pilot
                # Actions checks out files as the runner account. The Debian
                # module job executes as root, so trust this checkout only.
                git -C / config --global --add safe.directory "$GITHUB_WORKSPACE"
                apt-get -o APT::Update::Error-Mode=any update
                apt-get install -y --no-install-recommends libxml2 libzstd-dev zlib1g-dev
                bazel --version
            '
        fi
        shift
        exec unshare --mount --propagation private -- "$script" mounts "$@"
        ;;
    mounts)
        shift
        # Bind only the checkout, job scratch and OS interfaces used by builds.
        # The resolver and CA bundles match the worker that accepted this job.
        for path in "$GITHUB_WORKSPACE" "$RUNNER_TEMP" /dev /sys /etc/hosts \
                /etc/resolv.conf /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/java/cacerts; do
            if [[ -d "$path" ]]; then
                mkdir -p "$guest$path"
            else
                mkdir -p "$(dirname "$guest$path")"
                touch "$guest$path"
            fi
            mount --rbind "$path" "$guest$path"
        done
        touch "$guest/.dockerenv"
        # Compare the superblocks before writing any emulator registration. An
        # old kernel without per-user-namespace binfmt_misc must fail closed.
        binfmt="$RUNNER_TEMP/pilot-arm-binfmt"
        mkdir -p "$binfmt"
        mount -t binfmt_misc binfmt_misc "$binfmt"
        parent_device=$(stat -c %d "$binfmt")
        exec unshare --user --map-users=0:0:65536 --map-groups=0:0:65536 \
            --mount --pid --fork --kill-child --mount-proc \
            "$script" guest "$binfmt" "$parent_device" "$@"
        ;;
    guest)
        shift
        binfmt=$1
        parent_device=$2
        shift 2
        mount -t binfmt_misc binfmt_misc "$binfmt"
        [[ $(stat -c %d "$binfmt") != "$parent_device" ]]
        # ELF64, little-endian, ET_EXEC/ET_DYN, EM_AARCH64. F opens the
        # static QEMU interpreter before chroot. P and the packaged -binfmt-P
        # alias preserve argv[0] for programs that select behavior by name.
        magic='\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\xb7\x00'
        mask='\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff'
        printf ':pilot-aarch64:M::%s:%s:/usr/libexec/qemu-binfmt/aarch64-binfmt-P:PF\n' "$magic" "$mask" > "$binfmt/register"
        mount --bind /proc "$guest/proc"
        mkdir -p "$guest/root"
        # The Actions temporary script and repository have the same absolute
        # paths in both environments. All inherited build flags remain visible.
        exec chroot "$guest" /usr/bin/env HOME=/root \
            PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
            /bin/bash -c 'cd -- "$1" || exit; shift; exec "$@"' bash "$PWD" "$@"
        ;;
    *) echo "Usage: $0 prepare | run COMMAND [ARG ...] | shell FILE" >&2; exit 2 ;;
esac
