#!/usr/bin/env python3
"""Check SDK timestamps, gzip headers and GDB lookup without native execution."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("package_test", Path(__file__).with_name("package_test.py"))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class DevelopmentTimestampTest(unittest.TestCase):
    def archive(self, directory, *, mtime=0, pax_mtime=None, empty=False):
        path = Path(directory) / "sdk.tar"
        with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as archive:
            if not empty:
                entry = tarfile.TarInfo("usr/lib/x86_64-linux-gnu/pkgconfig/libteam.pc")
                contents = b"prefix=/usr\n"
                entry.size = len(contents)
                entry.mtime = mtime
                if pax_mtime is not None:
                    entry.pax_headers = {"mtime": pax_mtime}
                archive.addfile(entry, io.BytesIO(contents))
                link = tarfile.TarInfo("usr/lib/x86_64-linux-gnu/libteam.so")
                link.type = tarfile.SYMTYPE
                link.linkname = "libteam.so.5.6.1"
                archive.addfile(link)
        return path

    def test_zero_timestamp_files_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(VERIFY.verify_development_timestamps(self.archive(directory)), 2)

    def test_rejects_build_time_and_pax_override(self):
        for options in ({"mtime": 1793813010}, {"mtime": -1}, {"pax_mtime": "1793813010.5"}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "non-reproducible development timestamp: .*libteam.pc"):
                    VERIFY.verify_development_timestamps(self.archive(directory, **options))

    def test_rejects_empty_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "empty development archive"):
                VERIFY.verify_development_timestamps(self.archive(directory, empty=True))


class GzipHeaderTest(unittest.TestCase):
    # A fixed empty gzip stream; tests edit bytes, never invoke compression.
    GZIP = bytes.fromhex('1f8b080000000000020303000000000000000000')
    PATH = 'usr/share/man/man5/teamd.conf.5.gz'

    def archive(self, directory, rows):
        path = Path(directory) / 'runtime.tar'
        with tarfile.open(path, 'w') as archive:
            for name, data, kind in rows:
                member = tarfile.TarInfo(name)
                member.type = kind
                if kind == tarfile.REGTYPE:
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
                else:
                    member.linkname = 'elsewhere.gz'
                    archive.addfile(member)
        return path

    def test_records_zero_time_and_no_optional_header_fields(self):
        other = 'usr/share/doc/libteam-utils/changelog.Debian.gz'
        with tempfile.TemporaryDirectory() as directory:
            archive = self.archive(directory, [(self.PATH, self.GZIP, tarfile.REGTYPE),
                                                (other, self.GZIP, tarfile.REGTYPE),
                                                ('usr/share/doc/libteam-utils/copyright', b'notice', tarfile.REGTYPE)])
            self.assertEqual(VERIFY.verify_gzip_headers(archive, [self.PATH, other]),
                             [{'path': name, 'flags': 0, 'mtime': 0} for name in sorted([self.PATH, other])])

    def test_rejects_source_or_build_timestamp(self):
        for mtime in (1595757494, 1793877384):
            data = self.GZIP[:4] + mtime.to_bytes(4, 'little') + self.GZIP[8:]
            with self.subTest(mtime=mtime), tempfile.TemporaryDirectory() as directory:
                archive = self.archive(directory, [(self.PATH, data, tarfile.REGTYPE)])
                with self.assertRaisesRegex(ValueError, 'non-reproducible gzip header'):
                    VERIFY.verify_gzip_headers(archive, [self.PATH])

    def test_rejects_filename_comment_extra_and_other_flags(self):
        for flags in (1, 2, 4, 8, 16, 32, 64, 128):
            data = self.GZIP[:3] + bytes([flags]) + self.GZIP[4:]
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as directory:
                archive = self.archive(directory, [(self.PATH, data, tarfile.REGTYPE)])
                with self.assertRaisesRegex(ValueError, 'non-reproducible gzip header'):
                    VERIFY.verify_gzip_headers(archive, [self.PATH])

    def test_rejects_truncation_magic_and_compression_method(self):
        for data in (self.GZIP[:9], self.GZIP[:17], b'bad' + self.GZIP[3:],
                     self.GZIP[:2] + b'\x00' + self.GZIP[3:]):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                archive = self.archive(directory, [(self.PATH, data, tarfile.REGTYPE)])
                with self.assertRaisesRegex(ValueError, 'invalid gzip (member|header)'):
                    VERIFY.verify_gzip_headers(archive, [self.PATH])

    def test_rejects_missing_extra_duplicate_and_link_members(self):
        row = (self.PATH, self.GZIP, tarfile.REGTYPE)
        cases = [[], [row, ('unexpected.gz', self.GZIP, tarfile.REGTYPE)], [row, row],
                 [(self.PATH, b'', tarfile.SYMTYPE)], [(self.PATH, b'', tarfile.LNKTYPE)]]
        for rows in cases:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as directory:
                archive = self.archive(directory, rows)
                with self.assertRaisesRegex(ValueError, '(unexpected gzip member set|invalid gzip member)'):
                    VERIFY.verify_gzip_headers(archive, [self.PATH])


class DebugLookupTest(unittest.TestCase):
    def run_script(self, gdb):
        script = VERIFY.GDB_SCRIPT.replace('__SONIC_DEBUG_SYMBOL__', repr('main'))
        output = io.StringIO()
        # Execute only the Python portion with a fake GDB API; no debugger or
        # packaged program runs in these regression cases.
        with mock.patch.dict(sys.modules, {'gdb': gdb}), contextlib.redirect_stdout(output):
            exec(script.removeprefix('python\n').removesuffix('end\n'), {})
        return json.loads(output.getvalue().removeprefix('SONIC_DEBUG_LOOKUP='))

    def test_stripped_main_is_a_missing_symbol_result(self):
        class MissingSymbolError(Exception):
            pass

        gdb = types.SimpleNamespace(decode_line=mock.Mock(side_effect=MissingSymbolError('No symbol table is loaded.')))
        self.assertEqual(self.run_script(gdb), {'found': False})
        gdb.decode_line.assert_called_once_with('main')

    def test_packaged_debug_data_retains_function_source_and_line(self):
        function_type = mock.Mock(code=42)
        function_type.fields.return_value = []
        function = types.SimpleNamespace(name='main', type=function_type)
        location = types.SimpleNamespace(symtab=types.SimpleNamespace(filename='teamd/teamd.c'), line=1784, pc=256)
        gdb = types.SimpleNamespace(
            decode_line=mock.Mock(return_value=(None, [location])), TYPE_CODE_FUNC=42,
            block_for_pc=mock.Mock(return_value=types.SimpleNamespace(function=function)))
        result = self.run_script(gdb)
        self.assertTrue(result['found'])
        self.assertEqual((result['function'], result['source'], result['line']), ('main', 'teamd/teamd.c', 1784))

    def test_symbol_without_source_line_is_not_debug_acceptance(self):
        for location in (types.SimpleNamespace(symtab=None, line=0),
                         types.SimpleNamespace(symtab=object(), line=0)):
            with self.subTest(location=location):
                gdb = types.SimpleNamespace(decode_line=mock.Mock(return_value=(None, [location])))
                self.assertEqual(self.run_script(gdb), {'found': False})

    def test_lookup_requires_success_and_one_record_and_disables_external_sources(self):
        for found in (False, True):
            record = {'found': found, 'source': 'teamd.c', 'line': 1784}
            def run(argv, **kwargs):
                script = Path(argv[-1])
                self.assertEqual(script.read_text(), VERIFY.GDB_SCRIPT.replace('__SONIC_DEBUG_SYMBOL__', repr('main')))
                self.assertIn('set auto-load off', argv)
                self.assertIn('set debuginfod enabled off', argv)
                self.assertIn('set debug-file-directory /tmp/empty symbols', argv)
                self.assertIn('file "/tmp/isolated path/teamd"', argv)
                self.assertEqual(kwargs['env']['LC_ALL'], 'C')
                self.assertEqual(kwargs['env']['DEBUGINFOD_URLS'], '')
                self.assertEqual(kwargs['timeout'], 300)
                return subprocess.CompletedProcess(argv, 0, 'banner\nSONIC_DEBUG_LOOKUP=' + json.dumps(record) + '\n', '')
            with self.subTest(found=found), mock.patch.object(VERIFY.subprocess, 'run', side_effect=run) as mocked:
                self.assertEqual(VERIFY.gdb_lookup(Path('/tmp/isolated path/teamd'), Path('/tmp/empty symbols'), 'main'), record)
                mocked.assert_called_once()

    def test_gdb_errors_are_not_accepted_as_missing_symbols(self):
        record = 'SONIC_DEBUG_LOOKUP={"found": false}\n'
        cases = [(1, record, 'file could not be read'), (-11, record, 'debugger crashed'),
                 (0, '', ''), (0, record + record, ''),
                 (0, 'SONIC_DEBUG_LOOKUP={"found": false, "error": "broken API"}\n', ''),
                 (0, 'SONIC_DEBUG_LOOKUP={"found": "false"}\n', ''),
                 (0, 'SONIC_DEBUG_LOOKUP=invalid-json\n', '')]
        for status, stdout, stderr in cases:
            with self.subTest(status=status, stdout=stdout), mock.patch.object(
                    VERIFY.subprocess, 'run', return_value=subprocess.CompletedProcess([], status, stdout, stderr)):
                with self.assertRaises(ValueError) as raised:
                    VERIFY.gdb_lookup(Path('/tmp/teamd'), Path('/tmp/empty'), 'main')
                if stderr:
                    self.assertIn(stderr, str(raised.exception))
        for error in (FileNotFoundError('gdb is missing'), subprocess.TimeoutExpired('gdb', 300)):
            with self.subTest(error=error), mock.patch.object(VERIFY.subprocess, 'run', side_effect=error):
                with self.assertRaises(type(error)):
                    VERIFY.gdb_lookup(Path('/tmp/teamd'), Path('/tmp/empty'), 'main')


if __name__ == "__main__":
    unittest.main()
