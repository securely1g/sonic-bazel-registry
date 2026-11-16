# SONiC patches

Both patches are copied byte-for-byte from sonic-buildimage's
src/redis-dump-load.patch at buildimage commit
1a8f27c6c0f4f9e495d70e8ac7667cb16f468ede. Apply with strip 1 in this order:

1. 0001-Use-pipelines-when-dumping-52.patch: upstream change
   ed20dced07d8b2d140e2c1d79d506be0e12f339e, enables pipelined dumps.
2. 0002-Fix-setup.py-for-test-and-bdist_wheel.patch: selects setuptools for
   test/wheel support. Preserved as part of the effective SONiC source even
   though native Bazel rules do not execute setup.py.

The source archive predates both patches; the registry applies each exactly once.
