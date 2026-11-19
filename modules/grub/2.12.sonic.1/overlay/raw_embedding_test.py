"""Real regular-file BIOS embedding, checked against GPT and GRUB disk formats."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import uuid
import zlib

parser = argparse.ArgumentParser()
for name in ['setup', 'mkimage', 'sgdisk', 'assets']:
    parser.add_argument('--' + name, required=True)
args = parser.parse_args()
paths = {key: Path(value).absolute() for key, value in vars(args).items()}
receipt = {'commands': [], 'scope': 'regular raw-file BIOS embedding only'}

def run(command):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True)
    receipt['commands'].append({'argv': list(map(str, command)), 'exit_code': result.returncode,
                                'stdout': result.stdout, 'stderr': result.stderr})
    print(result.stdout, end='')
    print(result.stderr, end='')
    result.check_returncode()

try:
    with tempfile.TemporaryDirectory(prefix='grub-raw-', dir=os.environ['TEST_TMPDIR']) as temporary:
        root = Path(temporary)
        disk = root / 'disk.raw'
        with disk.open('wb') as stream:
            stream.truncate(32 * 1024 * 1024)
        stage = root / 'grub'
        stage.mkdir()
        (stage / 'boot.img').symlink_to(paths['assets'] / 'boot.img')
        run([paths['sgdisk'], '--clear', '--new=1:2048:4095', '--typecode=1:ef02', disk])
        run([paths['mkimage'], '--format=i386-pc', '--directory=' + str(paths['assets']),
             '--prefix=/boot/grub', '--output=' + str(stage / 'core.img'),
             'biosdisk', 'part_gpt', 'ext2', 'normal', 'configfile'])
        core = (stage / 'core.img').read_bytes()
        receipt['boot_sha256'] = hashlib.sha256((stage / 'boot.img').read_bytes()).hexdigest()
        receipt['core_sha256'] = hashlib.sha256(core).hexdigest()
        run([paths['setup'], '--directory=' + str(stage), '--skip-fs-probe',
             '--device-map=/dev/null', disk])
        with disk.open('rb') as stream:
            mbr = stream.read(512)
            assert mbr[510:] == b'\x55\xaa', 'MBR signature'
            header = bytearray(stream.read(512))
            assert header[:8] == b'EFI PART', 'GPT signature'
            size, checksum = struct.unpack_from('<II', header, 12)
            assert 92 <= size <= 512, 'GPT header size'
            header[16:20] = bytes(4)
            assert zlib.crc32(header[:size]) == checksum, 'GPT header CRC'
            entries_lba = struct.unpack_from('<Q', header, 72)[0]
            stream.seek(entries_lba * 512)
            entry = stream.read(128)
            # GRUB's BIOS Boot Partition type GUID, used by gdisk's EF02 type.
            assert uuid.UUID(bytes_le=entry[:16]) == uuid.UUID('21686148-6449-6e6f-744e-656564454649')
            first, last = struct.unpack_from('<QQ', entry, 32)
            assert (first, last) == (2048, 4095), 'BIOS partition geometry'
            # GRUB2.12 include/grub/i386/pc/boot.h: KERNEL_SECTOR=0x5c.
            core_lba = struct.unpack_from('<Q', mbr, 0x5c)[0]
            assert first <= core_lba <= last, 'embedded core LBA'
            stream.seek(core_lba * 512)
            # setup rewrites trailing diskboot blocklist entries, not its code prefix.
            assert stream.read(256) == core[:256] and any(core[:256]), 'embedded diskboot code'
        receipt.update(status='PASS', core_lba=core_lba, partition=[first, last])
finally:
    output = Path(os.environ['TEST_UNDECLARED_OUTPUTS_DIR']) / 'raw-embedding.json'
    output.write_text(json.dumps(receipt, indent=2) + '\n')
