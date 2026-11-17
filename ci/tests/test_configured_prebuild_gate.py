"""Inert tests only; do not invoke Bazel/build/network."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
from unittest import mock
from test_registry_ci import FixtureTestCase, registry_ci, write_json
import test_registry_ci as fixtures


class ConfiguredGateTests(FixtureTestCase):
    def graph(self, mnemonic='CppLink', filename='runtime.tar'):
        return {'pathFragments': [{'id': 1, 'label': filename}],
                'artifacts': [{'id': 2, 'pathFragmentId': 1}],
                'actions': [{'mnemonic': mnemonic, 'outputIds': [2]}]}

    def test_schema_explicit_true_only(self):
        entry = self.entry('alpha', '1.0.0')
        path = entry / 'presubmit.json'
        cfg = json.loads(path.read_text())
        cfg['forbid_deb_outputs'] = True
        write_json(path, cfg)
        registry_ci.validate_entry(self.root, 'alpha', '1.0.0')
        for value in (False, 1, 'true', [], None):
            cfg['forbid_deb_outputs'] = value
            write_json(path, cfg)
            with self.assertRaises(registry_ci.RegistryError):
                registry_ci.validate_entry(self.root, 'alpha', '1.0.0')

    def test_metadata_imports_allowed_producers_rejected(self):
        for mnemonic in ('CppLink', 'ExtractDeb', 'DebExtract', 'DebianRuntimeMetadata'):
            self.assertEqual(registry_ci.audit_non_deb_actions(self.graph(mnemonic)), 1)
        for mnemonic, filename in [('DebAssemble', 'pkg.tar'), ('Genrule', 'x.deb'), ('Genrule', 'x.udeb')]:
            with self.assertRaises(registry_ci.RegistryError):
                registry_ci.audit_non_deb_actions(self.graph(mnemonic, filename))

    def test_empty_malformed_unknown_and_cycle_fail_closed(self):
        examples = [{}, {'actions': []}, self.graph()]
        examples[-1]['actions'][0]['outputIds'] = [999]
        cycle = self.graph(); cycle['pathFragments'][0]['parentId'] = 1; examples.append(cycle)
        missing = self.graph(); del missing['actions'][0]['mnemonic']; examples.append(missing)
        for graph in examples:
            with self.assertRaises(registry_ci.RegistryError):
                registry_ci.audit_non_deb_actions(graph)

    def gate(self, graph, fail=None):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp); calls = []
            def run(command, **kw):
                calls.append(command)
                kind = 'aquery' if 'aquery' in command else 'cquery'
                self.assertEqual(kw['timeout'], 1200)
                self.assertNotEqual(kw['stdout'].name, kw['stderr'].name)
                kw['stdout'].write(json.dumps(graph) if kind == 'aquery' else 'output.tar\n')
                return subprocess.CompletedProcess(command, 1 if kind == fail else 0)
            with mock.patch.object(registry_ci.subprocess, 'run', side_effect=run):
                registry_ci.configured_non_deb_gate({'forbid_deb_outputs': True},
                    ['bazel', '--batch'], ['--platforms=//:native', '--host_platform=//:native'],
                    ['@owner//:runtime', '@owner//:Common++', '@owner//:test'], work, work)
            return calls, json.loads((work/'configured-prebuild-audit.json').read_text())

    def test_full_selection_flags_quoted_and_receipts(self):
        calls, result = self.gate(self.graph())
        self.assertEqual(len(calls), 2)
        for command in calls:
            self.assertIn('--platforms=//:native', command)
            self.assertIn('--host_platform=//:native', command)
            self.assertTrue(any('"@owner//:Common++"' in arg and '"@owner//:test"' in arg for arg in command))
        self.assertEqual(result['actions'], 1)
        self.assertEqual(result['forbidden_producers'], [])

    def test_failed_config_or_deb_graph_cannot_pass(self):
        for phase in ('cquery', 'aquery'):
            with self.assertRaises(registry_ci.RegistryError):
                self.gate(self.graph(), phase)
        with self.assertRaises(registry_ci.RegistryError):
            self.gate(self.graph('DebAssemble', 'x.deb'))

    def test_actual_runner_stops_before_build_on_gate_failure(self):
        fixture = fixtures.FetchedModuleTests()
        fixture.setUp()
        try:
            fixture.config['forbid_deb_outputs'] = True
            write_json(fixture.config_path, fixture.config)
            with mock.patch.object(registry_ci, 'configured_non_deb_gate',
                                   side_effect=registry_ci.RegistryError('blocked graph')) as gate, \
                    mock.patch.object(registry_ci, 'run_logged') as run:
                with self.assertRaisesRegex(registry_ci.RegistryError, 'blocked graph'):
                    fixture.run_fixture('gate-block')
                gate.assert_called_once()
                self.assertEqual(gate.call_args.args[3], ['@alpha//:library', '@alpha//:consumer_test'])
                self.assertFalse(any('build' in call.args[0] or 'test' in call.args[0]
                                     for call in run.call_args_list))
        finally:
            fixture.doCleanups()

    def test_no_optin_no_subprocess_and_gate_before_build(self):
        with mock.patch.object(registry_ci.subprocess, 'run') as run:
            registry_ci.configured_non_deb_gate({}, [], [], [], Path('.'), Path('.'))
            run.assert_not_called()
        source = Path(registry_ci.__file__).read_text()
        call = source.index('            configured_non_deb_gate(config, prefix, flags,')
        self.assertLess(call, source.index('            run_logged([*prefix, "build", *flags,'))
        self.assertIn('build_targets + test_targets', source[call:call+240])
