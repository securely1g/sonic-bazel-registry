"""Exercise the real compiler through the owner configure and recursive Make."""
import errno
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CONFIGURE = Path(sys.argv.pop(1)).resolve()


class ConfigureFlagsTest(unittest.TestCase):
    def test_long_flags_preserve_compiler_and_make_semantics(self):
        compiler, make = shutil.which('gcc'), shutil.which('make')
        self.assertIsNotNone(compiler, 'native registry tests require build-essential')
        self.assertIsNotNone(make, 'native registry tests require GNU Make')
        with tempfile.TemporaryDirectory(prefix='iproute2-flags-') as temporary:
            root = Path(temporary)
            include = root / 'deps/include/usr/include'
            include.mkdir(parents=True)
            (include / 'chosen.h').write_text('#define CHOSEN 41\n')
            (root / 'sub').mkdir()
            (root / 'source').mkdir()
            (root / 'source/chosen.h').write_text('#define CHOSEN 42\n')
            source = '''#include <stdio.h>
#include <chosen.h>
#ifndef MESSAGE
#error missing quoted define
#endif
int main(void) { printf("%d:%s\\n", CHOSEN, MESSAGE); return 0; }
'''
            (root / 'probe.c').write_text(source)
            (root / 'configure').write_text('''#!/bin/sh
set -eu
$CC probe.c -o configure-probe
./configure-probe > configure-result
: > config.mk
''')
            (root / 'configure').chmod(0o755)
            (root / 'Makefile').write_text('all:\n\t$(MAKE) -C sub\n')
            (root / 'sub/Makefile').write_text('''include ../config.mk
all:
	$(CC) -I../source $(CPPFLAGS) $(LDFLAGS) ../probe.c -o ../make-probe
	../make-probe > ../make-result
''')
            base = {**os.environ, 'CC': compiler, 'CFLAGS': '-O2 -g -ffile-prefix-map=' + str(root) + '=.',
                    'EXT_BUILD_ROOT': str(root), 'EXT_BUILD_DEPS': str(root / 'deps'),
                    'BAZEL_PKGCONFIG_FILES': '', 'BAZEL_PKGCONF': '/bin/true',
                    'YACC': '/bin/true', 'LEX': '/bin/true'}
            quoted = "-DMESSAGE='\"quoted value\"'"
            cppflags = quoted + ' -isystem ' + str(include)
            ldflags = '-Wl,--build-id -Wl,--defsym,flag_order=11 -Wl,--defsym,flag_order=29'
            results = []
            for large in (False, True):
                flags, links = cppflags, ldflags
                if large:
                    # Distinct, valid search options; nonexistent directories do
                    # not alter the expected selected headers or linked program.
                    padding = '/'.join(['p' * 70] * 2)
                    flags += ''.join(' -isystem' + str(root / padding / ('headers-' + str(i))) for i in range(470))
                    links += ''.join(' -L' + str(root / padding / ('libs-' + str(i))) for i in range(245))
                    legacy = ' '.join((compiler, base['CFLAGS'], flags, links))
                    self.assertGreater(len(legacy.encode()), 131072)
                    self.assertLess(len(flags.encode()), 131072)
                    self.assertLess(len(links.encode()), 131072)
                    with self.assertRaises(OSError) as error:
                        subprocess.run(['/bin/true'], env={**base, 'CC': legacy}, check=True)
                    self.assertEqual(error.exception.errno, errno.E2BIG)
                env = {**base, 'CPPFLAGS': flags, 'LDFLAGS': links}
                for command in (['/bin/sh', str(CONFIGURE)], [make]):
                    result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((root / 'configure-result').read_text(), '41:quoted value\n')
                # Source UAPI-like -I stays before the declared -isystem input.
                self.assertEqual((root / 'make-result').read_text(), '42:quoted value\n')
                for binary in ('configure-probe', 'make-probe'):
                    symbols = subprocess.check_output(['readelf', '-Ws', str(root / binary)], text=True)
                    value = next(line.split()[1] for line in symbols.splitlines() if line.endswith(' flag_order'))
                    self.assertEqual(int(value, 16), 29, 'linker option order changed')
                    debug = subprocess.check_output(['readelf', '-p', '.debug_line_str', '-p', '.debug_str', str(root / binary)], text=True)
                    self.assertNotIn(str(root), debug, 'response flags lost the debug prefix mapping')
                results.append({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                for name in ('configure-probe', 'make-probe')})
            self.assertEqual(results[0], results[1], 'flag delivery changed the compiled outputs')
            invalid = subprocess.run(['/bin/sh', str(CONFIGURE)], cwd=root,
                                     env={**base, 'CPPFLAGS': '-Wl,--as-needed', 'LDFLAGS': ''},
                                     capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn('CPPFLAGS must contain GCC preprocessor options', invalid.stderr)


if __name__ == '__main__':
    unittest.main()
