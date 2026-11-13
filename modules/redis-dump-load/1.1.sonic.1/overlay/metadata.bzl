load("@rules_python//python:packaging.bzl", "py_wheel")
load("@sonic_build_infra//python:site_packages.bzl", "site_packages")

# setup.py is the authority for both distribution and installation metadata.
_METADATA = dict(
    distribution = "redis-dump-load",
    version = "1.1",
    python_tag = "py3",
    requires = ["redis"],
    entry_points = {"console_scripts": [
        "redis-load = redisdl:main",
        "redis-dump = redisdl:main",
    ]},
    summary = "Dump and load redis databases",
    author = "Oleg Pudeyev",
    author_email = "oleg@bsdpower.com",
    homepage = "http://github.com/p/redis-dump-load",
    license = "BSD",
)

def distribution_targets():
    py_wheel(
        name = "wheel",
        deps = [":redisdl"],
        data_files = {
            "LICENSE": "data/share/doc/redis-dump-load/LICENSE",
            "README.rst": "data/share/doc/redis-dump-load/README.rst",
        },
        **_METADATA
    )

    site_packages(
        name = "install",
        files = {
            "redisdl.py": "redisdl.py",
            "LICENSE": "redis_dump_load-1.1.data/data/share/doc/redis-dump-load/LICENSE",
            "README.rst": "redis_dump_load-1.1.data/data/share/doc/redis-dump-load/README.rst",
        },
        site_packages = "/usr/local/lib/python3.13/dist-packages",
        scripts = "/usr/local/bin",
        headers = "/usr/local/include",
        data_prefix = "/usr/local",
        interpreter = "/usr/bin/python3",
        **_METADATA
    )
