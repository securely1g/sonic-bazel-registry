# redis-dump-load 1.1.sonic.1

This entry preserves SONiC's `REDIS_DUMP_LOAD_PY3` source identity:
upstream commit `758549795174dc6b3be70810e0e4d6308f80f1a3`, whose setup.py
version is `1.1`. The registry version keeps that two-component upstream
version as `1.1.sonic.1`; Python distribution metadata remains `1.1`.

The source recipe applies the two Make patches in their original series order.
The source-owned setup.py metadata is declared once in the metadata.bzl overlay for
both wheel and direct installation. Bazel directly consumes redisdl.py;
it does not invoke setup.py or install the wheel to produce the TAR.

Public interfaces:

- `:redisdl`: Python source library. Executing consumers supply the `redis`
  dependency, matching the unbounded upstream Requires-Dist declaration.
- `:wheel`: pure Python `redis_dump_load-1.1-py3-none-any.whl`.
- `:install`: installation TAR and PythonRuntimeInfo for Python 3.13 consumers.
  It installs redisdl.py and dist-info under
  `/usr/local/lib/python3.13/dist-packages`, redis-load and redis-dump under
  `/usr/local/bin`, and documentation under `/usr/local/share/doc/redis-dump-load`.
- `:runtime_metadata`: the same installation's generated runtime JSON.

Runtime resolution belongs to the image/rootfs consumer; the component preserves
`Requires-Dist: redis`. The Make recipe disables upstream tests (`_TEST = n`). The registry integration
test separately checks setup.py distribution contents, metadata, documentation,
entry points, and wheel/installed RECORD hashes, without requiring a Redis server.
Python 2's synthetic Make dependency only serializes writes to a shared Make
source tree; Bazel's isolated actions do not consume a Python 2 wheel.
