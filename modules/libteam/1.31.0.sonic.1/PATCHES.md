# SONiC libteam patch series

The 16 active entries below are copied from the exact Make series in
[buildimage233bde22](https://github.com/securely1g/sonic-buildimage/blob/233bde227dc62712bb3324ab4249cfbf145de893/src/libteam/patch/series).
The gaps are intentional: commented-out legacy patches stay inactive. Original
filenames, application order, authorship, messages and complete diff bodies are
preserved. Added notes explain purpose and provenance; prepared source equality
is checked separately. These are SONiC integration patches, not Debian-owned copies.

| Order | Existing patch | Purpose |
|---|---|---|
| 1 | [0001-libteam-Temporarily-remove-redundant-debug-messages.patch](patches/0001-libteam-Temporarily-remove-redundant-debug-messages.patch) | Remove two redundant LACP debug messages. This keeps the selected SONiC logging behavior without changing the state transitions around those messages. |
| 2 | [0002-teamd-lacp-runner-will-send-lacp-update-right-after-.patch](patches/0002-teamd-lacp-runner-will-send-lacp-update-right-after-.patch) | Notify the LACP runner when teamd receives its termination signal, so it can send the final LACP update before shutdown rather than waiting for normal periodic transmission. |
| 3 | [0003-libteam-Add-fallback-support-for-single-member-port-.patch](patches/0003-libteam-Add-fallback-support-for-single-member-port-.patch) | Retain SONiC fallback for a single-member LAG when its peer does not complete LACP negotiation; replacing this source with unpatched upstream would remove that configured behavior. |
| 4 | [0005-Increase-default-buffer-size-from-98304-to-2097152.patch](patches/0005-Increase-default-buffer-size-from-98304-to-2097152.patch) | Increase both default netlink socket buffers from 98,304 to 2,097,152 bytes, preserving the buffering selected for SONiC interface-event workloads. |
| 5 | [0006-teamd-Administratively-shutdown-port-channel-has-mem.patch](patches/0006-teamd-Administratively-shutdown-port-channel-has-mem.patch) | Ignore received LACP frames while the team interface is administratively down. Incoming frames must not reselect member ports and restore forwarding after administrative shutdown. |
| 6 | [0008-libteam-Add-warm_reboot-mode.patch](patches/0008-libteam-Add-warm_reboot-mode.patch) | Preserve SONiC's teamd warm-reboot procedure and its LACP state handoff. The native source build must retain the same restart and port-state handling as the Make patch series. |
| 7 | [0011-Remove-extensive-debug-output.patch](patches/0011-Remove-extensive-debug-output.patch) | Suppress the Unix-control-socket debug message printed for every method call. The request and response behavior remains unchanged while repeated control calls no longer emit that message. |
| 8 | [0012-Increase-min_ports-upper-limit-to -1024.patch](patches/0012-Increase-min_ports-upper-limit-to -1024.patch) | Allow runner.min_ports values through 1024 instead of the upstream UCHAR_MAX limit, and update the man page to match. SONiC configurations above 255 must not fail the upstream range check. |
| 9 | [0013-set-port-to-disabled-state-during-removal.patch](patches/0013-set-port-to-disabled-state-during-removal.patch) | Disable a port before removing it so the partner can receive the final LACP state. |
| 10 | [0014-dont-move-the-port-state-from-disabled-when-admin-state-is-down.patch](patches/0014-dont-move-the-port-state-from-disabled-when-admin-state-is-down.patch) | Keep ports disabled while the team administrative state is down. |
| 11 | [0015-add-support-for-custom-retry.patch](patches/0015-add-support-for-custom-retry.patch) | Support custom LACP retry counts for longer session timeouts. |
| 12 | [0016-block-retry-count-changes.patch](patches/0016-block-retry-count-changes.patch) | Hold a configured custom retry count for 60 seconds despite ordinary incoming packets. |
| 13 | [0017-Specify-netlink-recv-buffer-size-to-avoid-a-syscall.patch](patches/0017-Specify-netlink-recv-buffer-size-to-avoid-a-syscall.patch) | Use fixed netlink receive buffers to avoid an extra peek syscall per message. |
| 14 | [0018-Replace-FD_SET-select-with-poll-to-avoid-FD_SETSIZE-abort.patch](patches/0018-Replace-FD_SET-select-with-poll-to-avoid-FD_SETSIZE-abort.patch) | Use poll instead of FD_SET/select so control and event handling accepts descriptors above 1023. |
| 15 | [0019-fix-event-fd-init-and-free.patch](patches/0019-fix-event-fd-init-and-free.patch) | Initialize event_fd to -1 and close it only when valid, avoiding accidental closure of stdin or another handle. |
| 16 | [0020-Extend-LACP-fallback-support-to-multiple-ports.patch](patches/0020-Extend-LACP-fallback-support-to-multiple-ports.patch) | Extend the earlier single-port LACP fallback to multiple configured ports, retaining the existing teamd state selection and teamdctl reporting changes for that SONiC mode. |

The upstream archive is libteam 1.31. The separate Debian 1.31-1 archive supplies
control/changelog/symbols/copyright data and contains no Debian patch series.
No package fields or Debian-owned patches are fabricated or copied into this entry.
