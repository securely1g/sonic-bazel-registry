"""Keep kernel-dependent AF_ALG and ordinary OpenSSL recipes on their intended executors."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("registry_ci", Path(__file__).resolve().parents[1] / "registry_ci.py")
registry_ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry_ci)


class FipsCrossRecipeTests(unittest.TestCase):
    def test_original_recipe_argv_and_backend_status_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            consumer, work, artifacts = (root / n for n in ["consumer", "build space", "artifacts"])
            for folder in (consumer, work, artifacts):
                folder.mkdir()
            for name in ("userspace", "kernel"):
                tool = root / name
                tool.write_text(
                    "#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\n"
                    "if '-MConfig' in sys.argv:\n"
                    " print(json.dumps(dict(archname='aarch64-linux-gnu',version='5.40.1'))); sys.exit(0)\n"
                    f"with Path({str(root / 'calls')!r}).open('a') as f:\n"
                    f" f.write(json.dumps([{name!r},sys.argv[1:], [k for k in "
                    "('PERLLIB','PERL5LIB','PERL5OPT') if k in os.environ]])+'\\n')\n"
                    f"sys.exit({37 if name == 'kernel' else 0})\n")
                tool.chmod(0o755)
            user = [str(root / "userspace"), "--bind", str(work), "--"]
            flag = registry_ci.prepare_fips_recipe_perl(consumer, work, artifacts, user, root / "kernel")
            self.assertIn("recipe_perl=", flag)
            runner = consumer / "fips_recipe_runtime/run"
            env = {**os.environ, "PERLLIB": "host-only", "PERL5LIB": "host-only", "PERL5OPT": "-MHostOnly"}
            for recipe, backend, code in [("80-test_cmp_http.t", "userspace", 0), ("30-test_afalg.t", "kernel", 37)]:
                args = ["-Irelative source", "test/recipes/" + recipe, "original argument"]
                result = subprocess.run([str(runner), *args], cwd=consumer, env=env)
                self.assertEqual(result.returncode, code)
                observed = json.loads((root / "calls").read_text().splitlines()[-1])
                self.assertEqual(observed[0], backend)
                self.assertEqual(observed[1][-len(args) - 1:], ["/usr/bin/perl", *args])
                self.assertEqual(observed[2], [])
            self.assertEqual(len((root / "calls").read_text().splitlines()), 2)
