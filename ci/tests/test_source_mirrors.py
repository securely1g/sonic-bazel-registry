"""Fetch unchanged BCR archives and exercise ordered mirror fallback with Bazel."""
from __future__ import annotations

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
CI_SPEC = importlib.util.spec_from_file_location("registry_ci_source_mirrors", ROOT / "ci/registry_ci.py")
assert CI_SPEC is not None and CI_SPEC.loader is not None
REGISTRY_CI = importlib.util.module_from_spec(CI_SPEC)
CI_SPEC.loader.exec_module(REGISTRY_CI)
PIGZ_SHA256 = "eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0"
PIGZ_MODULE = "https://bcr.bazel.build/modules/pigz/2.8.bcr.2/MODULE.bazel"
ARM_ARCHIVES = (
    ("ape", "1.0.1", "sha512-YHlfxYHiCxzrifn5ywADS59XhmTk5u0rW/1fPepfk1C6/bXn3uwSADixLkvee6rAP9u2sulmHX0igt5F5+eqTA=="),
    ("download_utils", "1.0.1", "sha512-nsUJrJJjUWKzTQA187uWHhnBSqPA7t8Q6Rqry83Sj63Kf09L6xEFCR7thlnRUtbRbzabIKGr7JreouFdjjdarw=="),
    ("rules_coreutils", "1.0.1", "sha512-ViXfJnpIYJ/rhVAcq/WIc/SwekMKubAFS/1cVrziq9NoHkLBtXbf977l/fEknU1ElXtteVDtxOfgi8vcM+34Qg=="),
    ("rules_gzip", "1.0.0", "sha512-KK1A/NSvOaixXftdIRSBHt+QSPEk1ZorO2HtKY6o5KRP/i8KQ1hsDQPVwbCCi0++6pE529idMytTL/3SmhNmCQ=="),
    ("toolchain_utils", "1.0.2", "sha512-AXqtA9CzczVUdS5dw0dX332eaXZQhFcEZmf1iKALwsoKoT9Mboah7/j1JN9hZpzq6B5X7gpe83TPpya6yJZ6Lw=="),
)
ARM_RELEASE = "https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104"
GAWK_SHA256 = "f8c3486509de705192138b00ef2c00bbbdd0e84c30d5c07d23fc73a9dc4cc9cc"
GAWK_MIRROR = "https://distfiles.macports.org/gawk/gawk-5.3.2.tar.xz"
GAWK_HOSTS = ("mirrors.kernel.org", "ftp.gnu.org", "ftpmirror.gnu.org")
LIBSFRAME_SNAPSHOT = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb"
LIBAUDIT_SNAPSHOT = "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb"
LIBAUDIT_CONTENT_URL = "https://snapshot.debian.org/file/930f8fe502ed2d1b79243a03d1e1318c1bf30524"
# The libyang-python@3.1.0.sonic.6 generated APT lock pins these exact package bytes.
LIBSFRAME_SHA256 = "38f625dfdc582717029ac3a3e97c51d994ec2e7a0e9b230c6b44e40d1276311f"
DEBIAN_RELEASE_PACKAGES = (
    ("libcap2_2.75-10+deb13u1+b1_amd64.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/libc/libcap2/libcap2_2.75-10+deb13u1+b1_amd64.deb"),
    ("libpcre2-8-0_10.46-1.deb13u1_armhf.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/pcre2/libpcre2-8-0_10.46-1~deb13u1_armhf.deb"),
    ("libcap2_2.75-10+deb13u1+b1_arm64.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/libc/libcap2/libcap2_2.75-10+deb13u1+b1_arm64.deb"),
    ("bash_5.2.37-2+b9_arm64.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/b/bash/bash_5.2.37-2+b9_arm64.deb"),
    ("libcap-dev_2.75-10+deb13u1+b1_armhf.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/libc/libcap2/libcap-dev_2.75-10+deb13u1+b1_armhf.deb"),
    ("libsqlite3-0_3.46.1-7+deb13u1_amd64.deb",
     "https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/s/sqlite3/libsqlite3-0_3.46.1-7+deb13u1_amd64.deb"),
)
# Generated APT locks from native ARM validation and the cross-build survey
# preserve these exact bytes, including declared build-tool dependencies.
# Each tuple is (original URL, content locator, locked SHA256, size, optional CDN).
# A locator may include the optional filename after the content SHA1.
DEBIAN_CONTENT_PACKAGES = (
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libkrb5-3_1.21.3-5+deb13u1_amd64.deb",
     "53d94056269d541890f7e1bc61b4face03061af6",
     "47d71d6a7f2e59b9bae5f89602397594805113b95889ad18fa703cd53abafc97", 326056, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/pcre2/libpcre2-32-0_10.46-1~deb13u1_amd64.deb",
     "1d5504c88eac3e34bd38523ed6986c68ab5e205b",
     "db210bcfa7853c59b1a68863ca7d499122d413d4d368ffcc72c08b26203c3c15", 268056, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/t/tzdata/tzdata_2026b-0+deb13u1_all.deb",
     "47cec4da0609fa1ba1b38b6705c07b8578027cb6",
     "306013b77311e875620e89f43c447765a6c72b7b398e0baa8e5721bcbbdf66cf", 264316, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libk5crypto3_1.21.3-5+deb13u1_arm64.deb",
     "d747ad6e5b95660c1ca90228b55886aa814a51db",
     "2453e8d4fa3b91b868d5bc10e84a15ad9c7bc4e4cb49379cb1f560bdce50db4a", 81416, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/util-linux_2.41-5_arm64.deb",
     "e76be3e653327f16f37ab2c460e45d19b04e79dd",
     "d336901e4c1aedf268837d41a4e1004faa9b7ad4f1e6763f01711b487a4c18ce", 1191312, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/gzip/gzip_1.13-1_arm64.deb",
     "12136dd88ce463df2f49cdfa4a33666076228318",
     "cd46c9482fd3b96d4ecf282b01185ef9341b0ffcd40816372141f73037ce2c36", 135008, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/c/curl/curl_8.14.1-2+deb13u4_amd64.deb",
     "7ba41bdcd2ca506a7d43c424db9cde0662a868ca/curl_8.14.1-2%2Bdeb13u4_amd64.deb",
     "7bd23df36e65ca32a5bbd81f67ca311b9e0c122212c70d0733f4e45d745789d2", 269904, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/a/aom/libaom3_3.12.1-1_amd64.deb",
     "d8cd6332973da7765c8210e657882014f2c4914d",
     "16321210c4a3e27bf5ad1d56c1f09c9f7958f0c8ec3b8ae894ea1be322c5d055", 1871136, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/glibc/libc-dev-bin_2.41-12+deb13u3_amd64.deb",
     "4a63880454e8cdb1c0fb13d23f472d8244039aad",
     "2eb5db4cb16a42850ed9d3ca8b2b1aeda91dd00d248f6068f49d641321748308", 59836, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_armhf.deb",
     "dc490b3ef1fd8c6f403b161ae66e52dcf3eb0302",
     "3a5d421b22e2e0495ceaa5ed130dd6f4a35578fbf333873a7f79e2e115c11f61", 84264, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/e2fsprogs/comerr-dev_2.1-1.47.2-3+b11_armhf.deb",
     "c2d2e96220996d61738dcc91ebdf879e9ee2e046",
     "76c50d945fc5dd8d79fdfd6b63d03149689327f4385840deb7d7491c2826c41c", 56184, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/glibc/libc-bin_2.41-12+deb13u3_arm64.deb",
     "2f97c88e63e698b86775350598dea8efb421df45",
     "02f366115bea79b87fe26c7dec4dc444f9fdcc76440905d88cc26dbef075511b", 551364, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/uuid-dev_2.41-5_amd64.deb",
     "05b9652f442e9b33da16bb41cc69283e2a9b7c33",
     "fbc76c5c549192f52e7a03949108cdf28b1dc0751261495b7ef17cb8bf39dd8d", 48836, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/c/c-ares/libc-ares-dev_1.34.5-1+deb13u1_arm64.deb",
     "109d7800bf370139268bea60e2ea7e2699cc3d48",
     "40d2336fb01e4b707ad8a6bfbad522fc7ddff3b057d16ee981237fb7cef5d95c", 224912,
     "https://deb.debian.org/debian-security/pool/updates/main/c/c-ares/libc-ares-dev_1.34.5-1+deb13u1_arm64.deb"),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/openssl-provider-legacy_3.5.6-1~deb13u2_arm64.deb",
     "d5a41e70f8551fb076606ed0b1c0dab7fa9bc32d",
     "b099729f6a38d7d57f7f442f0f836c862673b9bb0ee65d757da6e3cdebbfd2a4", 310184, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/openssl_3.5.6-1~deb13u2_arm64.deb",
     "4b411e66ee3d3106570389d5d1e022b15c1975a8",
     "1ee735e2480519bd1fd5f6576a879243bc81b9773059e1fa1ec8b8943c84e77c", 1466984, None),
)
SURVEY_CONTENT_PACKAGES = (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/libuuid1_2.41-5_amd64.deb",
     "69561687e45ee4833a59400e51976ff05cf71c0d",
     "10247744737c1bb574f9667b3f06a3b43a5055c67bdfcc1945803451cc036db3", 37612, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/x/xapian-core/libxapian30_1.4.29-3_arm64.deb",
     "b3cef6d6dfd6511f04a77442026f81811313012e",
     "1652525c1c605b2169b3b27beecd01cbaa0e5abd7ec4d2029cbae2084dbde012", 1055832, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl-dev_3.5.6-1~deb13u2_armhf.deb",
     "a6e3b3b45aaf7799d6ab6ad71e09218a813866c8",
     "fc167d04049dfcf91ccff8687222a186be681cac2298ae89cf8523518ad04c88", 2570728, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libgssrpc4t64_1.21.3-5+deb13u1_amd64.deb",
     "3e0610e3b6f6d57539344d7a1f95da1ed442fd48",
     "ff88e52a6b6599851f3d44f7223f15123d9e5a0b02ed9a308c05c31fa88f7d73", 60132, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/libblkid1_2.41-5_amd64.deb",
     "8413cb58799327072dd69a418e41fc05009cfd03",
     "bed93f11942524e5338074c46cce376197740635bf0745ccb7d259e0f6ce7117", 171276, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/g/glibc/libc6_2.41-12+deb13u3_arm64.deb",
     "8dd0cfbe0f5bd2c3923c8252c00c868bc6ac945e",
     "ff529924782d3286181188fc265a6a92e7fe28975fb3a925dc0e05c0ca66e52f", 2489480, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/python3.13/libpython3.13-dev_3.13.5-2+deb13u4_arm64.deb",
     "f0907e7116933f0437ac671e9946e4740fcef10b",
     "fd62da71db387aba934e4bd17cceaf0db1454ae9e1eae378c4d8329fbe856883", 4924800, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/t/tiff/libtiff6_4.7.0-3+deb13u3_amd64.deb",
     "faa5bddd33fff3675e7b76863c6ef140347fb3b2",
     "6bb2038f36817ae1ee6d33df03917b21835dcc2e0f3e3e80a71390e83c171173", 345492, None),
)
SURVEY_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl-dev_3.5.6-1~deb13u2_amd64.deb",
     "ed4549f189f5faa3929d51268c16419c2ee87616",
     "04250d9e51fc87ef6d539f36cf0b66668dd34beec101af56dc35198ea99cef00", 2959032, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl-dev_3.5.6-1~deb13u2_arm64.deb",
     "e00e42b454c6acfd3a11622bc8aca25e8b4a232b",
     "afdd9c57261502a3a434ba606ddfd1e8fd0f288c663f2dc4f7570ce927867651", 3392872, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl3t64_3.5.6-1~deb13u2_amd64.deb",
     "fa81f709727b16de2a82710bbe0556b58f2b3f50",
     "b2dab3fe29c1fcb82ef58c2db0ff4bd830a442cf37b9a8b730b7b6ce87181349", 2447924, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl3t64_3.5.6-1~deb13u2_arm64.deb",
     "6e3fe344496850bb946e702685bacc5df1332dab",
     "f7e09a12ccb2d6bd28bcc87a6e2462a0558dcb3cc34d56f90ee86fbd3402d8ba", 2760128, None),
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/o/openssl/libssl3t64_3.5.6-1~deb13u2_armhf.deb",
     "70634fafccf8dee1bbccd0091a321e81f8983755",
     "b574fdbc1ac7a50df51f382a23847a68687892ceb06dcf0b1bc1ed4730109c28", 1994220, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/expat/libexpat1_2.7.1-2_amd64.deb",
     "2df60d569f5ba6703427c701e3707c04cd958a03",
     "f875f56675be5b074da877f9a93b09d47dc2eb4e679951d36e2943b8d4843344", 108204, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/expat/libexpat1_2.7.1-2_arm64.deb",
     "48585a6c3fab8508da2a2702d18a16f3c605b9ab",
     "7f6868227f4893a11123e43b9ed291950b550c7dc209905b2fb871c74678d1bf", 93320, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/expat/libexpat1_2.7.1-2_armhf.deb",
     "565675e8541721cdfa011219b0eba6efebf6f2d7",
     "1c82e8bb5d628ca8f8343975b26578d0894b8a1c33b54bc7741a6bfa8d880654", 85708, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/python3.13/libpython3.13-dev_3.13.5-2+deb13u4_amd64.deb",
     "3cb20569f34ff9c1f8537215183f7ce639a343f7",
     "dabada7ca12f95a17a31d19c3be4a8708a6a37207ac3b46cd1c344503825b0ee", 5275756, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/libuuid1_2.41-5_arm64.deb",
     "0cc7ca3341253904256e5dc4296786ce151e51eb",
     "85b7d04605f9d423d5699b3c07f027e8380649fd164a51e0712cded0cc56eced", 37412, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/libuuid1_2.41-5_armhf.deb",
     "5563fcda49878ea86b02546db7c47c42af9a0a72",
     "1a4b6e94cbc26e03e791f7a6e5ae714adc03ee5fe5b24c01651d1194d9de3a3c", 36408, None),
)
SURVEY_CONTENT_PACKAGES += (
    ('https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/f/freetype/libfreetype6_2.13.3+dfsg-1+deb13u1_amd64.deb',
     '2602e72ebeb8d5aa36eb1cc60f1cabfbd7558f43',
     'e4947f3291528f03d574f2b01d5c5fc45c58c47480f32888a5cdf0f231ab584e', 452308,
     'https://deb.debian.org/debian-security/pool/updates/main/f/freetype/libfreetype6_2.13.3+dfsg-1+deb13u1_amd64.deb'),
    ('https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/f/freetype/libfreetype6_2.13.3+dfsg-1+deb13u1_arm64.deb',
     '218fd3daa2391ba367cdd38ff4f8f79f6b3757e1',
     '0c426e83f1af816b9a4df9056fd2238463d1cd07969ee640965da9fb6ecaf107', 422284,
     'https://deb.debian.org/debian-security/pool/updates/main/f/freetype/libfreetype6_2.13.3+dfsg-1+deb13u1_arm64.deb'),
)
SURVEY_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/t/tiff/libtiff6_4.7.0-3+deb13u3_arm64.deb",
     "5e4fec5c53e730725b92a01b3e6663878562fa79",
     "208e9fdc14ed88a30f31fdfb993d1e8ab19f9ab29f3cd8546ffb4ea3f74f5a3f", 325232,
     "https://deb.debian.org/debian-security/pool/updates/main/t/tiff/libtiff6_4.7.0-3+deb13u3_arm64.deb"),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/libmount1_2.41-5_arm64.deb",
     "81aee071e0a7fff9504c0ec2cbf6acf665ebf0bb",
     "2e791f8faf7bbbc94d354cf7b6c3728dc303b7aa327dfe7a2aa6954320977c8f", 198880, None),
)
DEBIAN_CONTENT_PACKAGES += SURVEY_CONTENT_PACKAGES
# FRR AMD64 jobs selected these unchanged package inputs.
DEBIAN_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/perl/libperl5.40_5.40.1-6_amd64.deb",
     "115f4cbe17c3706c068bab13e8659621c15591f2",
     "f20aa427c3f56f430b7b58b73222edcb8cda40fa9c3b25365b20cd53eddd51a9", 4341332, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/u/util-linux/uuid-dev_2.41-5_arm64.deb",
     "cb5244c39df10c7ce2573dbf21944fe03d8a436b",
     "142f2c809a9c239b94a1a09dccc02a49cc4b20990da687b60f849cda84dd580a", 49472, None),
)
# Eventd AMD64 tests import the exact locked private Redis package.
DEBIAN_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/r/redis/redis-server_8.0.2-3+deb13u2_amd64.deb",
     "c502f81818978156937bce72be28acac56cf8da6",
     "0edc72458f66c68f2d4ccd0c9959a85a81f4ec7de410a28861cde4a2059f245c", 66576, None),
)
# Exact five observed PR195 inputs; see retained lock and official metadata evidence.
DEBIAN_CONTENT_PACKAGES += (
    ('https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libkrb5-dev_1.21.3-5+deb13u1_amd64.deb',
     '4fef5fafa9bcf0df24e4cc6ad971283da129ffa7',
     '62c3dbd746163878e73e22206d1dcc01f0f5296d3ca4ece5fb8cb7cb80396e4f', 16204, None),
    ('https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/pcre2/libpcre2-8-0_10.46-1~deb13u1_amd64.deb',
     '1594986c3db12e53c6d738df0926766b852e8e9d',
     '6aa452af6a07e34498bf8e734e8789c9dd602fb34f12572e62dc1bba4889a60e', 298536, None),
    ('https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/pcre2/libpcre2-dev_10.46-1~deb13u1_amd64.deb',
     '648dd0b86870e854e02868553a2246b3470b96dd',
     'b5cb023bfaad356053583af384f7b75caec3ac127a197f889164ef4d96397cef', 852668, None),
    ('https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/pcre2/libpcre2-dev_10.46-1~deb13u1_arm64.deb',
     'f114a29adbd36f6c0b136ab62613226f066e1fbf',
     'cf70657d734060bad45def0c67208e2afb1e165a5640d53b3bfe2264a3ada932', 750500, None),
    ('https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/p/pcre2/libpcre2-dev_10.46-1~deb13u1_armhf.deb',
     'e4ad4f9737d3906da5f6cdbb819176ee0ac0ad57',
     'a9210d107c63761a88847c0fdfcb7b15bcf7cd1fc443b91a25e58805a6f4f83d', 756112, None),
)
# Source-base AMD64 analysis selects this unchanged rsyslog RELP package.
DEBIAN_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/r/rsyslog/rsyslog-relp_8.2504.0-1_amd64.deb",
     "c16b59f13516c30140c256c1127b3be80899aff7",
     "8b58d38a801e33182b5bf66382f012830e8cd8b234358f76657eb946741a87ae", 316252, None),
)
# Exact JQ/ss-dev identities from SWSS and FRR image analysis failures.
DEBIAN_CONTENT_PACKAGES += (
    ('https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/j/jq/libjq1_1.7.1-6+deb13u2_amd64.deb',
     'b8b613de6336c793442ca724edcb30be97ee3de0',
     '140ac37e4b35370c3f34c95407cba75b35570e0be4bb9eebbf40bd72d182257c', 164336, None),
    ('https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/e2fsprogs/ss-dev_2.0-1.47.2-3+b11_armhf.deb',
     'e2267362c7557b71bcdc844929316ebfe8256dc3',
     '6792fc1b77c4335e780cf93fe5830a7930b392af2be0577cf25cb583bb4c1d48', 34996, None),
)
# Exact libexpat development identity from SWSS AMD64 analysis.
DEBIAN_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/expat/libexpat1-dev_2.7.1-2_amd64.deb",
     "d718845c00344d7965787ca08877a6d1bc51ef71",
     "ac1e7f8ad81578b61bc7c54c725ec639b06684e560766eac278490a1b2064372", 160568, None),
)
# Exact warning identities; the ARM64 package is selected during AMD64 analysis.
DEBIAN_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libkrb5support0_1.21.3-5+deb13u1_amd64.deb",
     "fdcbf424c12036172b67ed2d13d14fa441fb3736",
     "3a0acd8b37955c0e102c756b52c97df2a31f67b96453c35dab70df218d309117", 33124, None),
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/e/e2fsprogs/comerr-dev_2.1-1.47.2-3+b11_arm64.deb",
     "9ba5541a96f7de01c0d343e78296b07e2672051f",
     "490511f32afe59303e1fa2b4c54fd174de0d98f5f3cf9702e0f2784b834792e4", 56944, None),
)
# Exact Framework analysis input; ARM64 package resolution is not ARM execution.
DEBIAN_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/libc/libcap2/libcap-dev_2.75-10+deb13u1+b1_arm64.deb",
     "a5c6a45aae0d443be8f13ebc6eddfb3e83e23b55",
     "f1c0687bb0f6ad192b9cbe64429fc76029ce2a11939b155051139caf1683b447", 470800, None),
)
# Exact Sysmgr source-image runtime input; distinct from rsyslog-relp.
DEBIAN_CONTENT_PACKAGES += (
    ("https://snapshot.debian.org/archive/debian/20260727T143429Z/pool/main/r/rsyslog/rsyslog_8.2504.0-1_amd64.deb",
     "3745d404bae6227eb2142ce4aa8baeb8b0cad14d",
     "815203243b9eb17c72c0229fe26afb525542b867719ab36413ab8e514159a26b", 758296, None),
)
# Exact four observed ARMHF inputs; only libkadm5clnt-mit12 was the fatal fetch.
DEBIAN_CONTENT_PACKAGES += (
    ('https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libkadm5clnt-mit12_1.21.3-5+deb13u1_armhf.deb',
     '79a0f5873bc04d427cd972471105e1fcf64dd089',
     '166c0b71c91257d725d624ac8bbf345104dce0038451fb6104a0e7eea89278bb', 37844, None),
    ('https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/krb5-multidev_1.21.3-5+deb13u1_armhf.deb',
     '20d0dda5ff37855ff607673ee54c7c9608bd9d7b',
     '1e9476397e2ee8a749286e60d42fe08abfa0cc4b59703567821fff3d40b66559', 126412, None),
    ('https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libkrb5-3_1.21.3-5+deb13u1_armhf.deb',
     'c05801948acf5d6932a3ba59a52413725b1ead42',
     '988151350dfb736c7bb461ffb24bf136aeae72842838270f44d482b7f70d8167', 284480, None),
    ('https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/k/krb5/libgssapi-krb5-2_1.21.3-5+deb13u1_armhf.deb',
     'b52a9657c1c4c021218236cd2c58c2db7b85d55c',
     'df4ca163a4d682caac2e1fca14d83b6fac3899829856f62fe81f45dc578c7c70', 115712, None),
)
# BusyBox package inputs pinned by BCR rules_coreutils@1.0.1's MODULE.bazel.
BUSYBOX_PACKAGES = (
    ("amd64", "d161cd711fcf0d21a53dd7b9665933463de9fa6a37718e78ffee4d7732e1e02a", 937460),
    ("arm64", "76e03728f35dcc63b40ad52e5273c888ffd8eed254c0c9f871d5b4e31a485150", 830700),
)
BUSYBOX_SNAPSHOT_PREFIX = "https://snapshot-cloudflare.debian.org/archive/debian/20240210T223313Z/pool/main/b/busybox/"


def arm_urls(name, version):
    return (f"{ARM_RELEASE}/{name}-v{version}.tar.gz",
            f"https://gitlab.arm.com/bazel/{name}/-/releases/v{version}/downloads/src.tar.gz")


def debian_release_url(filename):
    return f"{ARM_RELEASE}/{quote(filename, safe='')}"


class ArmSourceMirrorScopeTest(unittest.TestCase):
    def test_only_exact_pinned_arm_urls_get_github_then_upstream_candidates(self):
        rewrites = [line.split()[1:] for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
                    if line.startswith("rewrite ")]
        for name, version, _integrity in ARM_ARCHIVES:
            github, upstream = arm_urls(name, version)
            candidates = [replacement for pattern, replacement in rewrites
                          if re.fullmatch(pattern, upstream.removeprefix("https://"))]
            self.assertEqual(candidates, [github, upstream])
            for other in (upstream + "?query", upstream + ".other", upstream.replace(version, "9.9.9"),
                          upstream.replace("gitlab.arm.com", "another.example"),
                          upstream.replace("/downloads/", "/different/")):
                self.assertFalse(any(re.fullmatch(pattern, other.removeprefix("https://"))
                                     for pattern, _replacement in rewrites), other)

    def test_gawk_candidates_preserve_each_original_url_and_exact_version(self):
        rewrites = [line.split()[1:] for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
                    if line.startswith("rewrite ")]
        for host in GAWK_HOSTS:
            upstream = f"https://{host}/gnu/gawk/gawk-5.3.2.tar.xz"
            candidates = [replacement for pattern, replacement in rewrites
                          if re.fullmatch(pattern, upstream.removeprefix("https://"))]
            self.assertEqual(candidates, [GAWK_MIRROR, upstream])
            for other in (upstream.replace("5.3.2", "5.3.3"), upstream + "?query", upstream + ".sig"):
                self.assertFalse(any(re.fullmatch(pattern, other.removeprefix("https://"))
                                     for pattern, _replacement in rewrites), other)


class DebianPoolMirrorScopeTest(unittest.TestCase):
    def candidates(self, url):
        rewrites = [line.split()[1:] for line in (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
                    if line.startswith("rewrite ")]
        result = []
        for pattern, replacement in rewrites:
            matched = re.fullmatch(pattern, url.removeprefix("https://"))
            if matched:
                result.append(re.sub(r"\$(\d+)", lambda ref: matched.group(int(ref[1])), replacement))
        return result

    def test_only_timestamped_debian_binary_pool_paths_are_rewritten(self):
        for upstream in (LIBSFRAME_SNAPSHOT,
                         "https://snapshot.debian.org/archive/debian/20250101T010203Z/pool/main/f/foo/foo_2%3a1.0~rc1+dfsg-3_arm64.deb"):
            pool_path = upstream.split("/pool/", 1)[1]
            self.assertEqual(self.candidates(upstream), ["https://deb.debian.org/debian/pool/" + pool_path, upstream])
        for other in (
            LIBSFRAME_SNAPSHOT.replace("snapshot.debian.org", "snapshot.example.org"),
            LIBSFRAME_SNAPSHOT.replace("/archive/debian/", "/archive/debian-security/"),
            LIBSFRAME_SNAPSHOT.replace("20260727T143429Z/", ""),
            LIBSFRAME_SNAPSHOT.replace("20260727T143429Z", "latest"),
            LIBSFRAME_SNAPSHOT.replace("pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                                      "dists/trixie/main/binary-amd64/Packages.xz"),
            LIBSFRAME_SNAPSHOT.removesuffix(".deb") + ".tar.xz",
            LIBSFRAME_SNAPSHOT.removesuffix(".deb") + ".dsc",
            LIBSFRAME_SNAPSHOT.replace("/main/", "/../"),
            LIBSFRAME_SNAPSHOT + "?query", LIBSFRAME_SNAPSHOT + ".sha256",
        ):
            self.assertEqual(self.candidates(other), [], other)

        # Exact verified indexes must not broaden the generic pool rules.
        indexes = {
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/dists/trixie-updates/main/binary-arm64/Packages.xz":
                "https://snapshot.debian.org/file/c9d85a145fcc34817defe65c818ded141ea2c95f",
            "https://snapshot.debian.org/archive/debian/20260727T143429Z/dists/trixie-updates/main/binary-armhf/Packages.xz":
                "https://snapshot.debian.org/file/ba24766d03291a7cbebe54ae2238ccec3c7861ea",
            "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/dists/trixie-security/main/binary-amd64/Packages.xz":
                "https://snapshot.debian.org/file/8c7898c09763411a9bff9e68bab2c6f08a6b14b4",
        }
        for upstream, content in indexes.items():
            self.assertEqual(self.candidates(upstream), [content, upstream])
            for architecture in ("amd64", "arm64", "armhf", "riscv64"):
                sibling = re.sub(r"binary-(amd64|arm64|armhf)", "binary-" + architecture, upstream)
                expected = [indexes[sibling], sibling] if sibling in indexes else []
                self.assertEqual(self.candidates(sibling), expected, sibling)
            for other in (
                upstream.replace("202607", "202608"),
                upstream.replace("trixie-updates", "trixie").replace("trixie-security", "trixie"),
                upstream.replace("/main/", "/contrib/"),
                upstream.replace("Packages.xz", "Packages.gz"),
                upstream.replace("Packages.xz", "Packages.bz2"),
                upstream.replace("Packages.xz", "Packages"),
                upstream.replace("snapshot.debian.org", "snapshot-cloudflare.debian.org"),
                upstream.replace("snapshot.debian.org", "another.example"),
                upstream.replace("/archive/debian/", "/archive/debian-security/") if "/archive/debian/" in upstream
                else upstream.replace("/archive/debian-security/", "/archive/debian/"),
                upstream + "?query", upstream + "#fragment", upstream + ".sha256",
            ):
                self.assertNotEqual(other, upstream)
                self.assertEqual(self.candidates(other), [], other)

        # One verified security CDN exception preserves the exact dated fallback.
        for upstream, cdn in (
            ("https://snapshot.debian.org/archive/debian-security/20260726T121236Z/pool/updates/main/libg/libgcrypt20/libgcrypt20_1.11.0-7+deb13u1_amd64.deb",
             "https://deb.debian.org/debian-security/pool/updates/main/libg/libgcrypt20/libgcrypt20_1.11.0-7+deb13u1_amd64.deb"),
        ):
            self.assertEqual(self.candidates(upstream), [cdn, upstream])
            for other in (
                upstream.replace("20260726T121236Z", "20260727T121236Z"),
                upstream.replace("1.11.0-7+deb13u1", "1.11.0-7+deb13u2"),
                upstream.replace("_amd64.deb", "_arm64.deb"),
                upstream.replace("_amd64.deb", "_armhf.deb"),
                upstream.replace("libgcrypt20_", "libgcrypt20-dev_"),
                upstream.replace("snapshot.debian.org", "snapshot-cloudflare.debian.org"),
                upstream.replace("snapshot.debian.org", "another.example"),
                upstream.replace("/archive/debian-security/", "/archive/debian/"),
                upstream + "?query", upstream + "#fragment", upstream + ".sha256",
            ):
                self.assertNotIn(cdn, self.candidates(other), other)

    def test_socat_patch_archive_has_one_exact_content_exception(self):
        upstream = "https://snapshot.debian.org/archive/debian/20241222T205329Z/pool/main/s/socat/socat_1.8.0.2-1.debian.tar.xz"
        content = "https://snapshot.debian.org/file/0475522901bd85478b944520b23e01e3f3c7d339"
        self.assertEqual(self.candidates(upstream), [content, upstream])
        for other in (
            upstream.replace("20241222T205329Z", "20241223T205329Z"),
            upstream.replace("1.8.0.2-1.debian", "1.8.0.2-2.debian"),
            upstream.replace("1.8.0.2-1.debian.tar.xz", "1.8.0.2.orig.tar.bz2"),
            upstream.replace("snapshot.debian.org", "snapshot-cloudflare.debian.org"),
            upstream.replace("snapshot.debian.org", "another.example"),
            upstream.replace("/archive/debian/", "/archive/debian-security/"),
            upstream.replace("/pool/main/s/socat/", "/pool/main/s/../"),
            upstream.replace("pool/main/s/socat/socat_1.8.0.2-1.debian.tar.xz",
                             "dists/trixie/main/source/Sources.xz"),
            upstream + "?query", upstream + "#fragment", upstream + ".sha256",
        ):
            self.assertEqual(self.candidates(other), [], other)

    def test_libaudit_content_address_is_limited_to_the_exact_pinned_package(self):
        self.assertEqual(self.candidates(LIBAUDIT_SNAPSHOT), [
            LIBAUDIT_CONTENT_URL,
            "https://deb.debian.org/debian/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
            LIBAUDIT_SNAPSHOT,
        ])
        for other in (
            LIBAUDIT_SNAPSHOT.replace("20260727T143429Z", "20260728T143429Z"),
            LIBAUDIT_SNAPSHOT.replace("4.0.2-2+b2", "4.0.2-2+b3"),
            LIBAUDIT_SNAPSHOT.replace("amd64", "arm64"),
            LIBAUDIT_SNAPSHOT.replace("snapshot.debian.org", "another.example"),
            LIBAUDIT_SNAPSHOT + "?query", LIBAUDIT_SNAPSHOT + ".sha256",
        ):
            self.assertNotIn(LIBAUDIT_CONTENT_URL, self.candidates(other), other)

    def test_debian_release_mirrors_are_limited_to_exact_locked_inputs(self):
        for filename, upstream in DEBIAN_RELEASE_PACKAGES:
            mirror = debian_release_url(filename)
            self.assertEqual(self.candidates(upstream), [
                mirror,
                "https://deb.debian.org/debian/pool/" + upstream.split("/pool/", 1)[1],
                upstream,
            ])
            for other in (
                upstream.replace("20260727T143429Z", "20260728T143429Z"),
                re.sub(r"([+~])", r"\1changed", upstream, count=1),
                re.sub(r"_(amd64|arm64|armhf)\.deb$",
                       "_arm64.deb" if upstream.endswith("_amd64.deb") else "_amd64.deb", upstream),
                upstream.replace("snapshot.debian.org", "another.example"),
                upstream + "?query", upstream + ".sha256",
            ):
                self.assertNotEqual(other, upstream)
                self.assertNotIn(mirror, self.candidates(other), other)

    def test_content_candidates_are_limited_to_exact_locked_packages(self):
        for upstream, locator, _checksum, _size, security_cdn in DEBIAN_CONTENT_PACKAGES:
            content = "https://snapshot.debian.org/file/" + locator
            expected = [content]
            if "/archive/debian/" in upstream:
                expected.append("https://deb.debian.org/debian/pool/" + upstream.split("/pool/", 1)[1])
            if security_cdn:
                expected.append(security_cdn)
            expected.append(upstream)
            self.assertEqual(self.candidates(upstream), expected)
            for other in (
                upstream.replace("202607", "202608"),
                upstream.replace(".deb", "+changed.deb"),
                re.sub(r"_(amd64|arm64|armhf|all)\.deb$",
                       "_arm64.deb" if upstream.endswith("_amd64.deb") else "_amd64.deb", upstream),
                re.sub(r"_(amd64|arm64|armhf|all)\.deb$", "_riscv64.deb", upstream),
                upstream.replace("snapshot.debian.org", "another.example"),
                upstream.replace("/pool/", "/different/"),
                upstream + "?query", upstream + ".sha256",
            ):
                self.assertNotEqual(other, upstream)
                self.assertNotIn(content, self.candidates(other), other)
                if security_cdn:
                    self.assertNotIn(security_cdn, self.candidates(other), other)

    def test_cloudflare_package_candidates_keep_standard_and_original_snapshots(self):
        for architecture, _checksum, _size in BUSYBOX_PACKAGES:
            upstream = BUSYBOX_SNAPSHOT_PREFIX + f"busybox-static_1.36.1-6_{architecture}.deb"
            self.assertEqual(self.candidates(upstream), [
                "https://deb.debian.org/debian/pool/main/b/busybox/" + upstream.rsplit("/", 1)[1],
                upstream.replace("snapshot-cloudflare.debian.org", "snapshot.debian.org"), upstream,
            ])
            for other in (
                upstream.replace("/archive/debian/", "/archive/debian-security/"),
                upstream.replace("20240210T223313Z/", ""),
                upstream.replace("pool/main/b/busybox/" + upstream.rsplit("/", 1)[1],
                                 "dists/bookworm/main/binary-amd64/Packages.xz"),
                upstream.removesuffix(".deb") + ".tar.xz", upstream + "?query",
                upstream.replace("snapshot-cloudflare.debian.org", "other.debian.org"),
            ):
                self.assertEqual(self.candidates(other), [], other)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to exercise real Bazel downloads")
class ArchiveFetchTestCase(unittest.TestCase):
    def fetch(self, work, module_text, repo, config):
        consumer = work / "consumer"
        consumer.mkdir()
        (consumer / "MODULE.bazel").write_text(module_text)
        (consumer / "BUILD.bazel").write_text("")
        cache = work / "repository-cache"
        cache.mkdir()
        self.assertEqual(list(cache.iterdir()), [])
        repos = [repo] if isinstance(repo, str) else repo
        command = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                   "--output_user_root=" + str(work / "bazel"), "--output_base=" + str(work / "output"),
                   "fetch", *("--repo=@" + name for name in repos), "--registry=https://bcr.bazel.build/",
                   "--repository_cache=" + str(cache), "--lockfile_mode=update",
                   *REGISTRY_CI.HTTP_DOWNLOAD_FLAGS,
                   "--experimental_downloader_config=" + str(config)]
        artifacts = work / "artifacts"
        artifacts.mkdir()
        (artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        try:
            with (artifacts / "fetch.log").open("w") as log:
                result = subprocess.run(command, cwd=consumer, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        finally:
            destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
            if destination:
                shutil.copytree(artifacts, Path(destination) / work.name)
        transcript = (artifacts / "fetch.log").read_text()
        return result, transcript, cache


class ArmSourceMirrorIntegrationTest(ArchiveFetchTestCase):
    def test_github_archives_match_original_bcr_recipes_with_empty_cache(self):
        for name, version, integrity in ARM_ARCHIVES:
            with self.subTest(module=name), tempfile.TemporaryDirectory(prefix="registry-arm-mirror-") as temporary:
                work = Path(temporary)
                github, upstream = arm_urls(name, version)
                metadata = f"https://bcr.bazel.build/modules/{name}/{version}"
                with urlopen(metadata + "/source.json", timeout=60) as response:
                    source = json.load(response)
                self.assertEqual(source["url"], upstream)
                self.assertEqual(source["integrity"], integrity)
                checksum = base64.b64decode(integrity.removeprefix("sha512-")).hex()
                with urlopen(github, timeout=60) as response:
                    self.assertEqual(hashlib.sha512(response.read()).hexdigest(), checksum)
                # Exercise the real release asset, never silently pass via upstream.
                config = work / "github-only.cfg"
                config.write_text((ROOT / "ci/source_mirrors.cfg").read_text() + "\nblock gitlab.arm.com\n")
                result, transcript, cache = self.fetch(
                    work, f'module(name = "arm_mirror_consumer")\nbazel_dep(name = "{name}", version = "{version}")\n',
                    name, config)
                self.assertEqual(result.returncode, 0, transcript)
                archive = cache / "content_addressable/sha512" / checksum / "file"
                self.assertEqual(hashlib.sha512(archive.read_bytes()).hexdigest(), checksum)
                fetched = list((work / "output/external").glob(name + "+*/MODULE.bazel"))
                self.assertEqual(len(fetched), 1, fetched)
                with urlopen(metadata + "/MODULE.bazel", timeout=60) as response:
                    self.assertEqual(fetched[0].read_bytes(), response.read())

    def test_rewrite_order_fallback_and_integrity_with_local_sources(self):
        original = b"original fixture bytes\n"
        integrity = "sha512-" + base64.b64encode(hashlib.sha512(original).digest()).decode()
        checksum = hashlib.sha512(original).hexdigest()
        github, upstream = arm_urls("ape", "1.0.1")
        for primary, fallback in (("valid", "valid"), ("missing", "valid"),
                                  ("corrupt", "valid"), ("corrupt", "corrupt")):
            with self.subTest(primary=primary, fallback=fallback), \
                    tempfile.TemporaryDirectory(prefix="registry-arm-fallback-") as temporary:
                work = Path(temporary)
                requests = []

                class ArchiveSource(BaseHTTPRequestHandler):
                    def do_GET(self):
                        requests.append(self.path)
                        behavior = primary if self.path == "/primary" else fallback
                        if behavior == "missing":
                            self.send_error(404)
                            return
                        payload = original if behavior == "valid" else b"changed fixture bytes\n"
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), ArchiveSource)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    config = work / "local.cfg"
                    config.write_text((ROOT / "ci/source_mirrors.cfg").read_text()
                                      .replace(github, f"http://127.0.0.1:{server.server_port}/primary")
                                      .replace(upstream, f"http://127.0.0.1:{server.server_port}/upstream"))
                    result, transcript, cache = self.fetch(work,
                        'module(name = "fallback_consumer")\n'
                        'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                        f'http_file(name = "archive_fixture", urls = [{upstream!r}], integrity = {integrity!r})\n',
                        "archive_fixture", config)
                    # Repeated HTTP attempts are allowed, but candidate order is fixed.
                    self.assertEqual(list(dict.fromkeys(requests)),
                                     ["/primary"] if primary == "valid" else ["/primary", "/upstream"])
                    archive = cache / "content_addressable/sha512" / checksum / "file"
                    if fallback == "corrupt":
                        self.assertNotEqual(result.returncode, 0, transcript)
                        self.assertFalse(archive.exists(), "Corrupt bytes entered the verified cache")
                    else:
                        self.assertEqual(result.returncode, 0, transcript)
                        self.assertEqual(archive.read_bytes(), original)
                    if primary == "corrupt":
                        self.assertIn("Checksum", transcript)
                finally:
                    server.shutdown()
                    server.server_close()


class GawkSourceMirrorIntegrationTest(ArchiveFetchTestCase):
    def test_gawk_mirror_preserves_published_integrity_with_empty_cache(self):
        source = json.loads((ROOT / "modules/gawk/5.3.2.sonic.1/source.json").read_text())
        self.assertEqual(base64.b64decode(source["integrity"].removeprefix("sha256-")).hex(), GAWK_SHA256)
        urls = [source["url"], *source["mirror_urls"]]
        self.assertEqual(urls, [f"https://{host}/gnu/gawk/gawk-5.3.2.tar.xz" for host in GAWK_HOSTS])
        with tempfile.TemporaryDirectory(prefix="registry-gawk-mirror-") as temporary:
            work = Path(temporary)
            config = work / "macports-only.cfg"
            # The regression must fetch the mirror, not silently succeed upstream.
            config.write_text((ROOT / "ci/source_mirrors.cfg").read_text()
                              + "\n" + "\n".join("block " + host for host in GAWK_HOSTS) + "\n")
            result, transcript, cache = self.fetch(work,
                'module(name = "gawk_mirror_consumer")\n'
                'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                f'http_file(name = "gawk_archive", urls = {urls!r}, integrity = {source["integrity"]!r})\n',
                "gawk_archive", config)
            self.assertEqual(result.returncode, 0, transcript)
            archive = cache / "content_addressable/sha256" / GAWK_SHA256 / "file"
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), GAWK_SHA256)


class DebianPoolMirrorIntegrationTest(ArchiveFetchTestCase):
    def test_survey_content_candidates_preserve_locked_bytes_without_other_fallbacks(self):
        # Exercise only each production content candidate: an available original
        # snapshot must not hide a broken alternative in this cold-download proof.
        rules = (ROOT / "ci/source_mirrors.cfg").read_text().splitlines()
        with tempfile.TemporaryDirectory(prefix="registry-survey-content-") as temporary:
            work = Path(temporary)
            module = ('module(name = "survey_content_consumer")\n'
                      'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n')
            selected_rules, repos = [], []
            for index, (upstream, locator, checksum, _size, _cdn) in enumerate(SURVEY_CONTENT_PACKAGES):
                matching = []
                for line in rules:
                    if not line.startswith("rewrite "):
                        continue
                    _directive, pattern, replacement = line.split(None, 2)
                    if (re.fullmatch(pattern, upstream.removeprefix("https://"))
                            and replacement == "https://snapshot.debian.org/file/" + locator):
                        matching.append(line)
                self.assertEqual(len(matching), 1, upstream)
                selected_rules.extend(matching)
                repo = f"survey_package_{index}"
                repos.append(repo)
                module += f'http_file(name = {repo!r}, urls = [{upstream!r}], sha256 = {checksum!r})\n'
            config = work / "content-only.cfg"
            config.write_text("\n".join(selected_rules) + "\n")
            result, transcript, cache = self.fetch(work, module, repos, config)
            self.assertEqual(result.returncode, 0, transcript)
            for _upstream, _locator, checksum, size, _cdn in SURVEY_CONTENT_PACKAGES:
                package = cache / "content_addressable/sha256" / checksum / "file"
                self.assertEqual(package.stat().st_size, size)
                self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), checksum)

    def test_content_package_candidates_preserve_all_locked_hashes_with_empty_cache(self):
        with tempfile.TemporaryDirectory(prefix="registry-debian-content-") as temporary:
            work = Path(temporary)
            module = ('module(name = "debian_content_consumer")\n'
                      'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n')
            repos = []
            for index, (upstream, _locator, checksum, _size, _cdn) in enumerate(DEBIAN_CONTENT_PACKAGES):
                repo = f"locked_package_{index}"
                repos.append(repo)
                module += f'http_file(name = {repo!r}, urls = [{upstream!r}], sha256 = {checksum!r})\n'
            result, transcript, cache = self.fetch(work, module, repos, ROOT / "ci/source_mirrors.cfg")
            self.assertEqual(result.returncode, 0, transcript)
            for upstream, _locator, checksum, size, _cdn in DEBIAN_CONTENT_PACKAGES:
                with self.subTest(package=upstream):
                    package = cache / "content_addressable/sha256" / checksum / "file"
                    self.assertEqual(package.stat().st_size, size)
                    self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), checksum)

    def test_exact_content_candidates_satisfy_original_snapshot_requests(self):
        for upstream, locator, _checksum, _size, _cdn in DEBIAN_CONTENT_PACKAGES:
            with self.subTest(package=upstream):
                self.exercise_snapshot_fallback(upstream, ["/content/" + locator])

    def test_exact_content_candidates_keep_all_original_fallbacks(self):
        for upstream, locator, _checksum, _size, security_cdn in DEBIAN_CONTENT_PACKAGES:
            with self.subTest(package=upstream):
                expected = ["/content/" + locator]
                if "/archive/debian/" in upstream:
                    expected.append("/cdn/pool/" + upstream.split("/pool/", 1)[1])
                    expected.append("/snapshot/" + upstream.split("/archive/debian/", 1)[1])
                else:
                    if security_cdn:
                        expected.append("/security-cdn/pool/" + upstream.split("/pool/", 1)[1])
                    expected.append("/snapshot-security/" + upstream.split("/archive/debian-security/", 1)[1])
                self.exercise_snapshot_fallback(upstream, expected)

    def test_corrupt_security_content_candidate_falls_back_with_original_integrity(self):
        security_packages = [package for package in DEBIAN_CONTENT_PACKAGES
                             if package[0] == (
                                 "https://snapshot.debian.org/archive/debian-security/20260726T121236Z/"
                                 "pool/updates/main/c/c-ares/libc-ares-dev_1.34.5-1+deb13u1_arm64.deb")]
        self.assertEqual(len(security_packages), 1)
        upstream, locator, _checksum, _size, _cdn = security_packages[0]
        self.exercise_snapshot_fallback(upstream, [
            "/content/" + locator,
            "/security-cdn/pool/" + upstream.split("/pool/", 1)[1],
            "/snapshot-security/" + upstream.split("/archive/debian-security/", 1)[1],
        ], corrupt_primary=True)

    def test_pool_candidates_preserve_locked_package_hash_with_empty_cache(self):
        with tempfile.TemporaryDirectory(prefix="registry-debian-pool-") as temporary:
            work = Path(temporary)
            # Old versions may leave the CDN pool; keep the production snapshot fallback.
            config = ROOT / "ci/source_mirrors.cfg"
            result, transcript, cache = self.fetch(work,
                'module(name = "debian_pool_consumer")\n'
                'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                f'http_file(name = "libsframe_package", urls = [{LIBSFRAME_SNAPSHOT!r}], sha256 = {LIBSFRAME_SHA256!r})\n',
                "libsframe_package", config)
            self.assertEqual(result.returncode, 0, transcript)
            package = cache / "content_addressable/sha256" / LIBSFRAME_SHA256 / "file"
            self.assertEqual(package.stat().st_size, 78360)
            self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), LIBSFRAME_SHA256)

    def test_busybox_candidates_preserve_both_architecture_hashes_with_empty_caches(self):
        for architecture, checksum, size in BUSYBOX_PACKAGES:
            with self.subTest(architecture=architecture), \
                    tempfile.TemporaryDirectory(prefix="registry-busybox-pool-") as temporary:
                work = Path(temporary)
                upstream = BUSYBOX_SNAPSHOT_PREFIX + f"busybox-static_1.36.1-6_{architecture}.deb"
                result, transcript, cache = self.fetch(work,
                    'module(name = "busybox_pool_consumer")\n'
                    'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                    f'http_file(name = "busybox_package", urls = [{upstream!r}], sha256 = {checksum!r})\n',
                    "busybox_package", ROOT / "ci/source_mirrors.cfg")
                self.assertEqual(result.returncode, 0, transcript)
                package = cache / "content_addressable/sha256" / checksum / "file"
                self.assertEqual(package.stat().st_size, size)
                self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), checksum)

    def test_release_mirrors_satisfy_original_snapshot_fetches(self):
        for filename, upstream in DEBIAN_RELEASE_PACKAGES:
            with self.subTest(package=filename):
                self.exercise_snapshot_fallback(upstream, ["/mirror/" + filename])

    def test_unavailable_release_mirrors_keep_original_fallbacks(self):
        for filename, upstream in DEBIAN_RELEASE_PACKAGES:
            with self.subTest(package=filename):
                self.exercise_snapshot_fallback(upstream, [
                    "/mirror/" + filename,
                    "/cdn/pool/" + upstream.split("/pool/", 1)[1],
                    "/snapshot/" + upstream.split("/archive/debian/", 1)[1],
                ])

    def test_content_addressed_file_satisfies_the_original_snapshot_fetch(self):
        self.exercise_snapshot_fallback(LIBAUDIT_SNAPSHOT, ["/content/libaudit"])

    def test_unavailable_content_address_keeps_cdn_and_snapshot_fallbacks(self):
        self.exercise_snapshot_fallback(LIBAUDIT_SNAPSHOT, [
            "/content/libaudit",
            "/cdn/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
            "/snapshot/20260727T143429Z/pool/main/a/audit/libaudit-dev_4.0.2-2+b2_amd64.deb",
        ])

    def test_missing_pool_version_falls_back_to_exact_snapshot_path(self):
        self.exercise_snapshot_fallback(LIBSFRAME_SNAPSHOT, [
            "/cdn/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
            "/snapshot/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
        ])

    def test_cloudflare_original_is_retained_when_both_alternatives_are_missing(self):
        self.exercise_snapshot_fallback(
            LIBSFRAME_SNAPSHOT.replace("snapshot.debian.org", "snapshot-cloudflare.debian.org"), [
                "/cdn/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                "/snapshot/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
                "/cloudflare/20260727T143429Z/pool/main/b/binutils/libsframe1_2.44-3_amd64.deb",
            ])

    def exercise_snapshot_fallback(self, upstream, expected_requests, *, corrupt_primary=False):
        payload = b"locked Debian package fixture\n"
        checksum = hashlib.sha256(payload).hexdigest()
        requests = []

        class PackageSource(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                corrupt = corrupt_primary and self.path == expected_requests[0]
                if self.path != expected_requests[-1] and not corrupt:
                    self.send_error(404)
                    return
                body = b"corrupt package bytes\n" if corrupt else payload
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), PackageSource)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix="registry-debian-fallback-") as temporary:
                work = Path(temporary)
                config = work / "local.cfg"
                config_text = ((ROOT / "ci/source_mirrors.cfg").read_text()
                               .replace(LIBAUDIT_CONTENT_URL, f"http://127.0.0.1:{server.server_port}/content/libaudit")
                               .replace("https://deb.debian.org/debian/$2", f"http://127.0.0.1:{server.server_port}/cdn/$2")
                               .replace("https://snapshot.debian.org/archive/debian/$1/$2",
                                        f"http://127.0.0.1:{server.server_port}/snapshot/$1/$2")
                               .replace("https://snapshot-cloudflare.debian.org/archive/debian/$1/$2",
                                        f"http://127.0.0.1:{server.server_port}/cloudflare/$1/$2"))
                for filename, _upstream in DEBIAN_RELEASE_PACKAGES:
                    config_text = config_text.replace(debian_release_url(filename),
                                                      f"http://127.0.0.1:{server.server_port}/mirror/{filename}")
                for snapshot, locator, _checksum, _size, cdn in DEBIAN_CONTENT_PACKAGES:
                    config_text = config_text.replace("https://snapshot.debian.org/file/" + locator,
                                                      f"http://127.0.0.1:{server.server_port}/content/{locator}")
                    if "/archive/debian-security/" in snapshot:
                        suffix = snapshot.split("/archive/debian-security/", 1)[1]
                        config_text = config_text.replace(snapshot,
                            f"http://127.0.0.1:{server.server_port}/snapshot-security/{suffix}")
                    if cdn:
                        config_text = config_text.replace(cdn,
                            f"http://127.0.0.1:{server.server_port}/security-cdn/pool/" + cdn.split("/pool/", 1)[1])
                config.write_text(config_text)
                result, transcript, cache = self.fetch(work,
                    'module(name = "debian_fallback_consumer")\n'
                    'http_file = use_repo_rule("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")\n'
                    f'http_file(name = "package_fixture", urls = [{upstream!r}], sha256 = {checksum!r})\n',
                    "package_fixture", config)
                self.assertEqual(result.returncode, 0, transcript)
                self.assertEqual(list(dict.fromkeys(requests)), expected_requests)
                self.assertEqual((cache / "content_addressable/sha256" / checksum / "file").read_bytes(), payload)
                if corrupt_primary:
                    self.assertIn("Checksum", transcript)
        finally:
            server.shutdown()
            server.server_close()


class SourceMirrorWorkflowScopeTest(unittest.TestCase):
    def test_matrix_is_preserved_for_every_branch_and_repository(self):
        workflow = (ROOT / ".github/workflows/registry-ci.yml").read_text()
        script = workflow.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        matrix = {"include": [{"module": "original", "architecture": architecture}
                              for architecture in ("amd64", "arm64")]}
        for branch, repository in (
            ("codex/pigz-source-mirror", "securely1g/sonic-bazel-registry"),
            ("codex/debian-container-runners", "securely1g/sonic-bazel-registry"),
            ("other", "securely1g/sonic-bazel-registry"),
            ("codex/pigz-source-mirror", "another/fork"),
        ):
            with self.subTest(branch=branch, repository=repository):
                with tempfile.TemporaryDirectory(prefix="mirror-workflow-") as temporary:
                    output = Path(temporary) / "output"
                    env = {"EVENT_NAME": "pull_request", "HEAD_REF": branch,
                           "HEAD_REPOSITORY": repository, "GITHUB_OUTPUT": str(output)}
                    with mock.patch.dict(os.environ, env), \
                            mock.patch.object(Path, "read_text", return_value=json.dumps(matrix)):
                        exec(compile(script, "registry-ci-workflow", "exec"), {})
                    lines = output.read_text().splitlines()
                    self.assertEqual(json.loads(lines[0].removeprefix("matrix=")), matrix)
                    self.assertIn("has_jobs=true", lines)
                    self.assertIn("has_amd64_jobs=true", lines)
                    self.assertIn("has_arm64_jobs=true", lines)


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to exercise real Bazel downloads")
class SourceMirrorIntegrationTest(unittest.TestCase):
    def test_original_bcr_archive_and_patches_with_empty_cache(self):
        self.exercise_mirror(corrupt=False)

    def test_mirror_cannot_replace_original_bcr_archive(self):
        self.exercise_mirror(corrupt=True)

    def exercise_mirror(self, *, corrupt):
        with tempfile.TemporaryDirectory(prefix="registry-source-mirror-") as temporary:
            work = Path(temporary)
            consumer = work / "consumer"
            consumer.mkdir()
            artifacts = work / "artifacts"
            artifacts.mkdir()
            (consumer / "MODULE.bazel").write_text(
                'module(name = "pigz_mirror_consumer")\n'
                'bazel_dep(name = "pigz", version = "2.8.bcr.2")\n')
            (consumer / "BUILD.bazel").write_text("")
            config = ROOT / "ci/source_mirrors.cfg"
            server = None
            requests = []
            if corrupt:
                class WrongArchive(BaseHTTPRequestHandler):
                    def do_GET(self):
                        requests.append(self.path)
                        payload = b"not the original pigz source archive\n"
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)

                    def log_message(self, *_args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), WrongArchive)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                config = work / "corrupt.cfg"
                config.write_text((ROOT / "ci/source_mirrors.cfg").read_text().replace(
                    "https://distfiles.macports.org/pigz/pigz-2.8.tar.gz",
                    f"http://127.0.0.1:{server.server_port}/pigz-2.8.tar.gz"))
            cache = work / "repository-cache"
            cache.mkdir()
            self.assertEqual(list(cache.iterdir()), [])
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                      "--output_user_root=" + str(work / "bazel"),
                      "--output_base=" + str(work / "output")]
            command = [*prefix, "fetch", "--repo=@pigz", "--registry=https://bcr.bazel.build/",
                       "--repository_cache=" + str(cache), "--lockfile_mode=update",
                       *REGISTRY_CI.HTTP_DOWNLOAD_FLAGS,
                       "--experimental_downloader_config=" + str(config)]
            try:
                (artifacts / "command.json").write_text(json.dumps(command, indent=2) + "\n")
                with (artifacts / "fetch.log").open("w") as log:
                    result = subprocess.run(command, cwd=consumer, stdout=log,
                                            stderr=subprocess.STDOUT, timeout=300)
                transcript = (artifacts / "fetch.log").read_text()
                archive = cache / "content_addressable/sha256" / PIGZ_SHA256 / "file"
                if corrupt:
                    self.assertNotEqual(result.returncode, 0, transcript)
                    self.assertIn("Checksum", transcript)
                    self.assertTrue(requests, "Bazel did not request the corrupt mirror")
                    self.assertEqual(set(requests), {"/pigz-2.8.tar.gz"})
                    self.assertFalse(archive.exists(), "Corrupt archive entered the verified cache")
                else:
                    self.assertEqual(result.returncode, 0, transcript)
                    self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), PIGZ_SHA256)
                    fetched = list((work / "output/external").glob("pigz*/MODULE.bazel"))
                    self.assertEqual(len(fetched), 1, fetched)
                    with urlopen(PIGZ_MODULE, timeout=60) as response:
                        expected_module = response.read()
                    self.assertEqual(fetched[0].read_bytes(), expected_module)
                    # Successful extraction applies all unchanged BCR patches,
                    # including the upstream BUILD and module declarations.
                    self.assertTrue((fetched[0].parent / "BUILD.bazel").is_file())
                    shutil.copy2(fetched[0], artifacts / "fetched.MODULE.bazel")
                    shutil.copy2(consumer / "MODULE.bazel.lock", artifacts / "MODULE.bazel.lock")
                (artifacts / "result.json").write_text(json.dumps({
                    "corrupt_mirror": corrupt, "status": "passed",
                    "module": "pigz@2.8.bcr.2", "original_archive_sha256": PIGZ_SHA256,
                    "empty_repository_cache": True, "distdir": None,
                    "package_actions_executed": False,
                }, indent=2) + "\n")
            finally:
                if server:
                    server.shutdown()
                    server.server_close()
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
