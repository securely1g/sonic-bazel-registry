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
            # Trust the worker's CA even when a registry test deliberately
            # ignores every Bazel RC file.
            cat > "$guest/usr/local/bin/bazel" <<'LAUNCHER'
#!/bin/sh
if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then
    exec /usr/local/lib/bazel-8.5.1 --version
fi
# Under QEMU the bundled JDK 24 can hang while stopping a Bazel thread pool.
# Use Debian's ARM64 JDK from the pinned runner image and OS-backed threads.
exec /usr/local/lib/bazel-8.5.1 \
    --server_javabase=/usr/lib/jvm/java-21-openjdk-arm64 \
    --host_jvm_args=-XX:+UnlockExperimentalVMOptions \
    --host_jvm_args=-XX:-VMContinuations \
    --host_jvm_args=-Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts \
    --host_jvm_args=-Xmx2g "$@"
LAUNCHER
            chmod 0755 "$guest/usr/local/bin/bazel"
            if [[ ${CI_MODULE:-} == rules_distroless ]]; then
                bash "$(dirname "$script")/pilot_arm_kernel.sh" --prepare "$guest"
            fi
            if [[ ${CI_MODULE:-} == sonic-fips ]]; then
                # #94 already ships the kernel, initrd and executor in this worker.
                # Run its AMD64 system emulator directly from the ARM chroot.
                host_usr=/usr/local/lib/sonic-pilot-host-usr
                install -d "$guest$host_usr" "$guest/usr/local/share" "$guest/opt"
                ln -sfn "$host_usr/local/bin/sonic-arm64-kernel" "$guest/usr/local/bin/sonic-arm64-kernel"
                ln -sfn "$host_usr/local/share/sonic-arm64-kernel" "$guest/usr/local/share/sonic-arm64-kernel"
                ln -sfn / "$guest/opt/sonic-arm64-rootfs"
                install -m 0755 "$(dirname "$script")/pilot_fips_recipe.sh" "$guest/usr/local/bin/sonic-pilot-fips-recipe"
                cat > "$guest/usr/bin/qemu-system-aarch64" <<'EMULATOR'
#!/bin/sh
host_usr=/usr/local/lib/sonic-pilot-host-usr
lib=$host_usr/lib/x86_64-linux-gnu
export QEMU_MODULE_DIR=$lib/qemu
exec "$lib/ld-linux-x86-64.so.2" --library-path "$lib" "$host_usr/bin/qemu-system-aarch64" -L "$host_usr/share/qemu" "$@"
EMULATOR
                chmod 0755 "$guest/usr/bin/qemu-system-aarch64"
            fi
            set -- run bash -ec '
                test "$(dpkg --print-architecture)" = arm64
                test "$(uname -m)" = aarch64
                /usr/lib/jvm/java-21-openjdk-arm64/bin/java -version
                # rules_distroless runs zstd with argv[0]=gzip when it writes
                # content.tar.gz from a Debian package. Verify the same pipeline.
                test "$(printf pilot | (exec -a gzip /usr/bin/zstd -n) | gzip -dc)" = pilot
                # Actions checks out files as the runner account. The Debian
                # module job executes as root, so trust this checkout only.
                git -C / config --global --add safe.directory "$GITHUB_WORKSPACE"
                apt-get -o APT::Update::Error-Mode=any update
                apt-get install -y --no-install-recommends libxml2 libzstd-dev zlib1g-dev tini
                if [[ ${CI_MODULE:-} == rules_distroless ]]; then
                    apt-get install -y --no-install-recommends busybox-static cpio
                    # A failed test must reach Bazel even when QEMU powers off cleanly.
                    result=0
                    TEST_TARGET=@rules_distroless//registry_ci:linux_headers_test \
                        sonic-pilot-arm-kernel-test /bin/dash -c "exit 37" || result=$?
                    test "$result" -eq 37
                fi
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
        if [[ ${CI_MODULE:-} == sonic-fips ]]; then
            host_usr="$guest/usr/local/lib/sonic-pilot-host-usr"
            mount --bind /usr "$host_usr"
            mount -o remount,bind,ro "$host_usr"
        fi
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
        # After prepare installs tini, it becomes PID 1 and reaps detached
        # Bazel servers. A zombie server otherwise looks alive to bazel shutdown.
        init=()
        if [[ -x "$guest/usr/bin/tini" ]]; then
            init=(/usr/bin/tini -g --)
        fi
        exec chroot "$guest" "${init[@]}" /usr/bin/env HOME=/root \
            PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
            /bin/bash -c 'cd -- "$1" || exit; shift; exec "$@"' bash "$PWD" "$@"
        ;;
    *) echo "Usage: $0 prepare | run COMMAND [ARG ...] | shell FILE" >&2; exit 2 ;;
esac
