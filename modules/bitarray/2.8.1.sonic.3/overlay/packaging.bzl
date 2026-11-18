"""Shared distribution declaration for the wheel and direct installation TAR."""
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@sonic_build_infra//python:site_packages.bzl", "site_packages")

_METADATA = dict(
    distribution = "bitarray",
    version = "2.8.1",
    python_tag = "cp313",
    abi = "cp313",
    platform = "linux_x86_64",
    author = "Ilan Schnell",
    author_email = "ilanschnell@gmail.com",
    homepage = "https://github.com/ilanschnell/bitarray",
    license = "PSF",
    summary = "efficient arrays of booleans -- C extension",
    description_file = "README.rst",
    classifiers = [
        "License :: OSI Approved :: Python Software Foundation License",
        "Development Status :: 6 - Mature",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: C",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Utilities"
    ],
    license_files = ["LICENSE"],
    extra_distinfo_files = {"LICENSE": "licenses/LICENSE"},
    regular_file_mode = "0644",
)

def bitarray_packages(supported):
    py_wheel(
        name = "whl",
        deps = [":_wheel_payload"],
        stamp = 0,
        target_compatible_with = supported,
        **_METADATA
    )
    site_packages(
        name = "bitarray.runtime",
        files = {
            "bitarray/__init__.py": "bitarray/__init__.py",
            "bitarray/test_bitarray.py": "bitarray/test_bitarray.py",
            "bitarray/test_util.py": "bitarray/test_util.py",
            "bitarray/util.py": "bitarray/util.py",
            "bitarray/__init__.pyi": "bitarray/__init__.pyi",
            "bitarray/bitarray.h": "bitarray/bitarray.h",
            "bitarray/py.typed": "bitarray/py.typed",
            "bitarray/pythoncapi_compat.h": "bitarray/pythoncapi_compat.h",
            "bitarray/test_150.pickle": "bitarray/test_150.pickle",
            "bitarray/test_281.pickle": "bitarray/test_281.pickle",
            "bitarray/util.pyi": "bitarray/util.pyi",
            ":bitarray/_bitarray.cpython-313-x86_64-linux-gnu.so": "bitarray/_bitarray.cpython-313-x86_64-linux-gnu.so",
            ":bitarray/_util.cpython-313-x86_64-linux-gnu.so": "bitarray/_util.cpython-313-x86_64-linux-gnu.so",
        },
        site_packages = "/usr/local/lib/python3.13/dist-packages",
        scripts = "/usr/local/bin",
        headers = "/usr/local/include/python3.13",
        data_prefix = "/usr/local",
        interpreter = "/usr/bin/python3",
        target_compatible_with = supported,
        **_METADATA
    )
    native.filegroup(
        name = "bitarray.runtime_metadata",
        srcs = [":bitarray.runtime"],
        output_group = "metadata",
        target_compatible_with = supported,
    )
