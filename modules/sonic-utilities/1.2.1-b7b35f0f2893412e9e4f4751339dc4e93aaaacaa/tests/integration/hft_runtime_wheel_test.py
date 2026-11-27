"""Check the HFT host CLI installed by the VS Make reference image."""

import hashlib
import sys
import zipfile


# Files from src/sonic-utilities at buildimage gitlink 7f28a11d, also
# verified in the filesystem of the VS Make installer.
HFT_FILES = {
    "config/hft.py": "bd380588726c808079001a3a7114580525e48402585c0a43ea0bcbbb06aadcae",
    "show/hft.py": "f1aee3b97d93ace34b2f8a9f14cc86b519ff32fc220e6a0f1b47c8dff5cfa3c2",
    "utilities_common/hft.py": "c769bbaf7660b81d86319cf00c758a7fc4ffb68ee4f73cb2c788c0cd51381dd9",
}


def check_wheel(path):
    with zipfile.ZipFile(path) as wheel:
        for filename, expected in HFT_FILES.items():
            actual = hashlib.sha256(wheel.read(filename)).hexdigest()
            if actual != expected:
                raise ValueError(f"{filename}: expected {expected}, got {actual}")


if __name__ == "__main__":
    check_wheel(sys.argv[1])
