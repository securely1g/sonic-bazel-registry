"""Archive data only: source-owned patch staging and fail-closed controls."""
import io,tarfile,json,hashlib,base64
from unittest import mock
from test_registry_ci import FixtureTestCase,registry_ci,write_json

class SourcePatchStagingTests(FixtureTestCase):
    def archive(self, kind='regular'):
        out=io.BytesIO()
        with tarfile.open(fileobj=out,mode='w:gz') as tar:
            if kind=='parent-symlink':
                x=tarfile.TarInfo('owner/patches');x.type=tarfile.SYMTYPE;x.linkname='/tmp';tar.addfile(x)
            x=tarfile.TarInfo('owner/patches/tool.patch' if kind!='traversal' else 'owner/../tool.patch')
            if kind=='symlink':x.type=tarfile.SYMTYPE;x.linkname='/tmp/patch';tar.addfile(x)
            else:
                x.size=4;tar.addfile(x,io.BytesIO(b'body'))
                if kind=='duplicate':tar.addfile(x,io.BytesIO(b'body'))
        return out.getvalue()
    def setup_stage(self, raw):
        entry=self.entry('alpha','1.0.0');source=json.loads((entry/'source.json').read_text());source.update(strip_prefix='owner',integrity='sha256-'+base64.b64encode(hashlib.sha256(raw).digest()).decode());write_json(entry/'source.json',source)
        consumer=self.root/'consumer';consumer.mkdir();artifacts=self.root/'receipts';artifacts.mkdir()
        cfg={'consumer_deps':[{'name':'tool','version':'1.0','source_patches':['@alpha//patches:tool.patch'],'patch_strip':1}]}
        return entry,consumer,artifacts,cfg
    def test_exact_bytes_staged_to_main_repository(self):
        raw=self.archive();entry,consumer,artifacts,cfg=self.setup_stage(raw)
        with mock.patch.object(registry_ci,'urlopen',return_value=io.BytesIO(raw)):
            labels=registry_ci.stage_consumer_source_patches(self.root,'alpha','1.0.0',cfg,consumer,artifacts)
        self.assertEqual(labels,{'@alpha//patches:tool.patch':'//_registry_source_patches:000.patch'})
        self.assertEqual((consumer/'_registry_source_patches/000.patch').read_bytes(),b'body')
        self.assertIn('000.patch',(consumer/'_registry_source_patches/BUILD.bazel').read_text())
    def test_wrong_archive_hash_rejected_before_outputs(self):
        raw=self.archive();entry,consumer,artifacts,cfg=self.setup_stage(raw)
        with mock.patch.object(registry_ci,'urlopen',return_value=io.BytesIO(raw+b'wrong')):
            with self.assertRaisesRegex(registry_ci.RegistryError,'checksum'):
                registry_ci.stage_consumer_source_patches(self.root,'alpha','1.0.0',cfg,consumer,artifacts)
        self.assertFalse((consumer/'_registry_source_patches').exists())
    def test_unsafe_archive_members_rejected(self):
        for kind in ['symlink','parent-symlink','traversal','duplicate']:
            with self.subTest(kind=kind):
                raw=self.archive(kind)
                # independent fixture directories per negative variant
                import tempfile,pathlib
                with tempfile.TemporaryDirectory() as d:
                    old=self.root;self.root=pathlib.Path(d)
                    try:
                        entry,consumer,artifacts,cfg=self.setup_stage(raw)
                        with mock.patch.object(registry_ci,'urlopen',return_value=io.BytesIO(raw)):
                            with self.assertRaises(registry_ci.RegistryError):registry_ci.stage_consumer_source_patches(self.root,'alpha','1.0.0',cfg,consumer,artifacts)
                    finally:self.root=old

    def test_foreign_label_and_missing_owner_file_rejected(self):
        raw=self.archive();entry,consumer,artifacts,cfg=self.setup_stage(raw)
        for label in ['@other//patches:tool.patch','@alpha//patches:missing.patch']:
            cfg['consumer_deps'][0]['source_patches']=[label]
            with mock.patch.object(registry_ci,'urlopen',return_value=io.BytesIO(raw)):
                with self.assertRaises(registry_ci.RegistryError):registry_ci.stage_consumer_source_patches(self.root,'alpha','1.0.0',cfg,consumer,artifacts)
        self.assertFalse((consumer/'_registry_source_patches').exists())
    def test_existing_or_symlink_staging_directory_rejected(self):
        raw=self.archive();entry,consumer,artifacts,cfg=self.setup_stage(raw)
        directory=consumer/'_registry_source_patches';directory.symlink_to(artifacts,target_is_directory=True)
        with mock.patch.object(registry_ci,'urlopen',return_value=io.BytesIO(raw)):
            with self.assertRaisesRegex(registry_ci.RegistryError,'fresh'):registry_ci.stage_consumer_source_patches(self.root,'alpha','1.0.0',cfg,consumer,artifacts)
    def test_order_and_strip_retained_by_generator(self):
        raw=self.archive();entry,consumer,artifacts,cfg=self.setup_stage(raw)
        cfg['consumer_deps'][0]['patch_strip']=2
        with mock.patch.object(registry_ci,'urlopen',return_value=io.BytesIO(raw)):
            labels=registry_ci.stage_consumer_source_patches(self.root,'alpha','1.0.0',cfg,consumer,artifacts)
        receipt=json.loads((artifacts/'consumer-source-patches.json').read_text())
        self.assertEqual(receipt['patches'][0]['source_label'],'@alpha//patches:tool.patch')
        self.assertEqual(cfg['consumer_deps'][0]['patch_strip'],2)
        self.assertEqual(labels['@alpha//patches:tool.patch'],'//_registry_source_patches:000.patch')
