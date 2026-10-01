#!/usr/bin/env python3
"""Exercise SAI's real RunAspell with a selected Perl runtime and fake tools.

Example: python3 test_configurable_aspell.py --style /source/meta/style.pm
         --perl /path/to/perl --perl-option=-I/path/to/perl/runtime
The upstream utils.pm must be beside style.pm. No host Aspell is required.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument("--style", type=Path, default=Path(__file__).with_name("style.pm"))
PARSER.add_argument("--perl")
PARSER.add_argument("--perl-runtime", type=Path)
PARSER.add_argument("--perl-option", action="append", default=[])
CONFIG, TEST_ARGS = PARSER.parse_known_args()
CONFIG.style = CONFIG.style.resolve()
if CONFIG.perl_runtime:
    from python.runfiles import runfiles
    runtime = json.loads(CONFIG.perl_runtime.read_text())
    CONFIG.perl = runfiles.Create().Rlocation(runtime["interpreter"])
    CONFIG.perl_option = runtime["options"] + CONFIG.perl_option
if not CONFIG.perl:
    PARSER.error("--perl must identify a Perl interpreter")
CONFIG.perl = str(Path(CONFIG.perl).resolve())

DRIVER = r'''
use strict;
use warnings;
use File::Basename qw(dirname);
use JSON::PP;
my ($style, $words_file) = @ARGV;
unshift @INC, dirname($style);
require $style;
my @spawned;
{
    no warnings 'redefine';
    my $original = \&style::open3;
    *style::open3 = sub {
        @spawned = @_[3 .. $#_];
        return $original->(@_);
    };
}
open(my $words_input, '<', $words_file) or die $!;
my $words = decode_json(do { local $/; <$words_input> });
style::RunAspell($words);
print "ASPELL_TEST_RESULT ", encode_json({
    errors => $utils::errors, warnings => $utils::warnings, spawned => \@spawned,
}), "\n";
exit($utils::errors ? 1 : 0);
'''

FAKE_TOOL = r'''
import json, os, signal, sys
from pathlib import Path
mode = os.environ.get('ASPELL_TEST_MODE', 'success')
if mode == 'large_output':
    sys.stdout.write('*\n' * 100000)
    sys.stderr.write('\n' * 100000)
    sys.stdout.flush()
    sys.stderr.flush()
words = sys.stdin.read()
Path(os.environ['ASPELL_TEST_RECORD']).write_text(json.dumps({
    'arguments': sys.argv[1:], 'stdin': words, 'cwd': os.getcwd(),
}))
if mode == 'nonzero':
    print('checker failed without the usual keyword', file=sys.stderr)
    sys.exit(7)
if mode == 'stderr_error':
    print('Error: dictionary is unavailable', file=sys.stderr)
elif mode == 'stdout_error':
    print('Error: invalid custom dictionary')
elif mode == 'signalled':
    os.kill(os.getpid(), signal.SIGTERM)
elif mode == 'misspelling':
    print('& incorrect 1 0: correct')
else:
    print('@(#) fake Aspell')
    print('*')
'''


class ConfigurableAspellTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sai aspell test ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.driver = self.root / "driver.pl"
        self.driver.write_text(DRIVER)
        self.fake_program = self.root / "fake.py"
        self.fake_program.write_text(FAKE_TOOL)
        self.tool = self.root / "aspell tool ; echo SHOULD_NOT_EXECUTE"
        self.tool.write_text('#!/bin/sh\nexec "$ASPELL_TEST_PYTHON" "$ASPELL_TEST_PROGRAM" "$@"\n')
        self.tool.chmod(0o755)
        self.record = self.root / "record.json"
        (self.root / "aspell.en.pws").write_text("personal_ws-1.1 en 0\n")

    def run_checker(self, *, mode="success", override=True, words=None, executable=None):
        words = {"hello": "first", "world": "second"} if words is None else words
        words_file = self.root / "words.json"
        words_file.write_text(json.dumps(words))
        environment = dict(os.environ)
        environment.pop("SAI_ASPELL", None)
        if override:
            environment["SAI_ASPELL"] = str(self.tool if executable is None else executable)
        environment.update({
            "ASPELL_TEST_MODE": mode,
            "ASPELL_TEST_PROGRAM": str(self.fake_program),
            "ASPELL_TEST_PYTHON": sys.executable,
            "ASPELL_TEST_RECORD": str(self.record),
            "TMPDIR": str(self.root),
            "LC_ALL": "C",
            "PATH": "",
        })
        result = subprocess.run(
            [CONFIG.perl, *CONFIG.perl_option, str(self.driver), str(CONFIG.style), str(words_file)],
            cwd=self.root, env=environment, capture_output=True, text=True, timeout=20,
        )
        records = [line.removeprefix("ASPELL_TEST_RESULT ")
                   for line in result.stdout.splitlines() if line.startswith("ASPELL_TEST_RESULT ")]
        self.assertEqual(len(records), 1, result.stdout + result.stderr)
        return result, json.loads(records[0])

    def test_override_with_spaces_is_one_executable_and_preserves_input(self):
        words = {"world": "second", "hello": "first", 'x"$(touch SHOULD_NOT_EXECUTE)': "third"}
        result, report = self.run_checker(words=words)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["errors"], 0)
        self.assertEqual(report["spawned"], [str(self.tool), "-l", "en", "-a", "-p", "./aspell.en.pws"])
        record = json.loads(self.record.read_text())
        self.assertEqual(record["arguments"], ["-l", "en", "-a", "-p", "./aspell.en.pws"])
        self.assertEqual(record["stdin"], " ".join(sorted(words)) + "\n")
        self.assertEqual(record["cwd"], str(self.root))
        self.assertFalse((self.root / "SHOULD_NOT_EXECUTE").exists())

    def test_unset_override_uses_original_system_path(self):
        result, report = self.run_checker(override=False)
        if report["spawned"]:
            self.assertEqual(report["spawned"], ["/usr/bin/aspell", "-l", "en", "-a", "-p", "./aspell.en.pws"])
        else:
            self.assertEqual(result.returncode, 1)
            self.assertIn("ASPELL IS NOT PRESENT OR EXECUTABLE: /usr/bin/aspell", result.stdout)

    def test_empty_override_uses_original_system_path(self):
        result, report = self.run_checker(executable="")
        if report["spawned"]:
            self.assertEqual(report["spawned"][0], "/usr/bin/aspell")
        else:
            self.assertEqual(result.returncode, 1)
            self.assertIn("ASPELL IS NOT PRESENT OR EXECUTABLE: /usr/bin/aspell", result.stdout)

    def test_missing_override_is_reported(self):
        result, report = self.run_checker(executable=self.root / "does not exist")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["errors"], 1)
        self.assertEqual(report["spawned"], [])
        self.assertIn("does not exist", result.stdout)

    def test_nonexecutable_override_is_reported(self):
        self.tool.chmod(0o644)
        result, report = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["errors"], 1)
        self.assertEqual(report["spawned"], [])

    def test_exec_failure_is_reported(self):
        self.tool.write_text("#!/missing/aspell-interpreter\n")
        result, report = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["errors"], 1)
        self.assertIn("Cannot launch Aspell", result.stdout)
        self.assertIn(str(self.tool), result.stdout)

    def test_nonzero_exit_cannot_silently_pass(self):
        result, report = self.run_checker(mode="nonzero")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["errors"], 1)
        self.assertIn("exit 7, signal 0", result.stdout)
        self.assertIn("checker failed without the usual keyword", result.stdout)

    def test_signalled_child_is_reported(self):
        result, report = self.run_checker(mode="signalled")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["errors"], 1)
        self.assertIn("signal 15", result.stdout)

    def test_stderr_error_keeps_existing_error_detection(self):
        result, report = self.run_checker(mode="stderr_error")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["errors"], 1)
        self.assertIn("aspell error: Error: dictionary is unavailable", result.stdout)

    def test_stdout_error_keeps_existing_error_detection(self):
        result, report = self.run_checker(mode="stdout_error")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["errors"], 1)
        self.assertIn("aspell error: Error: invalid custom dictionary", result.stdout)

    def test_misspelling_keeps_existing_warning_and_location(self):
        result, report = self.run_checker(mode="misspelling", words={"incorrect": "source.h:123"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["errors"], 0)
        self.assertEqual(report["warnings"], 1)
        self.assertIn("Word 'incorrect' is misspelled source.h:123", result.stdout)

    def test_large_output_before_large_input_does_not_deadlock(self):
        words = {"word" + str(index).zfill(6): "source.h" for index in range(20000)}
        result, report = self.run_checker(mode="large_output", words=words)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["errors"], 0)
        self.assertEqual(json.loads(self.record.read_text())["stdin"], " ".join(sorted(words)) + "\n")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], *TEST_ARGS])
