"""Validate declarative root patches from the tested immutable owner, not URLs."""
import ast,copy,json,pathlib,textwrap
from test_registry_ci import FixtureTestCase,registry_ci,write_json


class ConsumerSourcePatchTests(FixtureTestCase):
    def config(self):
        entry=self.entry('alpha','1.0.0')
        path=entry/'presubmit.json'
        cfg=json.loads(path.read_text())
        cfg['consumer_deps'][0].update(source_patches=['@alpha//patches:tool.patch'],patch_strip=1)
        return path,cfg

    def test_owner_patch_and_root_generation(self):
        path,cfg=self.config();write_json(path,cfg)
        registry_ci.validate_entry(self.root,'alpha','1.0.0')
        source=pathlib.Path(registry_ci.__file__).read_text()
        start=source.index('            declarations =');end=source.index('            (consumer / "MODULE.bazel").write_text',start)
        env={'config':cfg,'module':'alpha','version':'1.0.0','json':json,
             'staged_patches': {'@alpha//patches:tool.patch': '//_registry_source_patches:000.patch'}}
        exec(compile(textwrap.dedent(source[start:end]),'declaration-only','exec'),env)
        text='\n'.join(env['declarations']);tree=ast.parse(text)
        for statement in tree.body:
            if isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call):
                call=statement.value
                if isinstance(call.func,ast.Name) and call.func.id=='bazel_dep':
                    self.assertFalse(any(k.arg in ('source_patches','patch_strip','patches') for k in call.keywords))
        self.assertIn('patches = ["//_registry_source_patches:000.patch"], patch_strip = 1',text)

    def test_invalid_or_foreign_sources_rejected(self):
        path,cfg=self.config()
        for value in ([],['https://example.invalid/x.patch'],['@other//:x.patch'],['@alpha//:../x.patch'],
                      ['@alpha//:x.patch','@alpha//:x.patch'],['@alpha//:script.sh']):
            c=copy.deepcopy(cfg);c['consumer_deps'][0]['source_patches']=value;write_json(path,c)
            with self.assertRaises(registry_ci.RegistryError):registry_ci.validate_entry(self.root,'alpha','1.0.0')
        for value in (-1,True,'1'):
            c=copy.deepcopy(cfg);c['consumer_deps'][0]['patch_strip']=value;write_json(path,c)
            with self.assertRaises(registry_ci.RegistryError):registry_ci.validate_entry(self.root,'alpha','1.0.0')
        c=copy.deepcopy(cfg);del c['consumer_deps'][0]['source_patches'];write_json(path,c)
        with self.assertRaises(registry_ci.RegistryError):registry_ci.validate_entry(self.root,'alpha','1.0.0')
