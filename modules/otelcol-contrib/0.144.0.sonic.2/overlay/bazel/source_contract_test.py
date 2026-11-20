"""Compare maintained collector dependencies with the upstream OCB sources."""

import argparse
import ast
from pathlib import Path
import re
import unittest


def module_requirements(text):
    return dict(re.findall(r"^\s*(\S+) (v\S+)(?:\s+// indirect)?$", text, re.M))


def repository_name(module):
    host, *path = module.split("/")
    return re.sub(r"[^a-z0-9_]", "_", "_".join([*host.split(".")[::-1], *path]).lower())


class SourceContract(unittest.TestCase):
    def test_manifest_modules_keep_the_release_versions(self):
        requirements = module_requirements(Path(ARGS.go_mod).read_text())
        manifest = re.findall(r"^\s+- gomod: (\S+) (v\S+)$", Path(ARGS.manifest).read_text(), re.M)
        self.assertEqual(len(manifest), 244)
        self.assertEqual(len(dict(manifest)), len(manifest))
        for module, version in manifest:
            with self.subTest(module=module):
                self.assertEqual(requirements[module], version)

    def test_every_generated_import_has_one_maintained_dependency(self):
        requirements = module_requirements(Path(ARGS.go_mod).read_text())
        imports = set()
        for source in ARGS.source:
            imports.update(path for path in re.findall(
                r'^\s+(?:\w+\s+)?"([^\"]+)"$', Path(source).read_text(), re.M
            ) if "." in path)
        expected = set()
        for path in imports:
            owner = max((m for m in requirements if path == m or path.startswith(m + "/")), key=len)
            expected.add("@" + repository_name(owner) + "//" + path[len(owner):].lstrip("/") + ":go_default_library")
        actual = []
        for statement in ast.parse(Path(ARGS.dependencies).read_text()).body:
            if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.List):
                actual.extend(ast.literal_eval(statement.value))
        self.assertEqual(len(actual), len(set(actual)), "Duplicate maintained dependencies")
        self.assertEqual(set(actual), expected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--go-mod", required=True)
    parser.add_argument("--dependencies", required=True)
    parser.add_argument("--source", action="append", required=True)
    ARGS, remaining = parser.parse_known_args()
    unittest.main(argv=[__file__, *remaining])
