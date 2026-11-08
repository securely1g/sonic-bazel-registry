"""Synthetic installed-library contracts: exact package ownership and clean loading.

Expected values come from the small C sources below, not from generated BUILD
text. The fixture covers multiple .pc files, static and nested scripts, duplicate
filenames, AS_NEEDED and a two-DSO consumer through the production CcInfo adapter.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import tarfile
import sys
import sysconfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--adapter', type=Path, required=True)
    parser.add_argument('--go', type=Path)
    parser.add_argument('--rustc', type=Path)
    parser.add_argument('--cross-info', type=Path, help='Caller-supplied compiler/sysroot/flags JSON for ARM64')
    parser.add_argument('--qemu', type=Path, help='AArch64 user-mode emulator for an AMD64 execution host')
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix='apt-library-contract-'))
    print('Evidence:', root, flush=True)
    env = {k: v for k, v in os.environ.items() if k not in ('LD_LIBRARY_PATH', 'LD_PRELOAD')}
    env['USE_BAZEL_VERSION'] = '8.5.1'
    arch = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
    cross = json.loads(args.cross_info.read_text()) if args.cross_info else None
    compiler = [cross['cc']] + cross['flags'] if cross else ['gcc']
    if cross:
        arch = 'arm64'
        assert args.qemu, '--qemu is required for the cross-execution fixture'
    packages, cases = {}, []
    module_cases = {}

    def run(command, **options):
        options.setdefault('env', env)
        result = subprocess.run(command, text=True, capture_output=True, **options)
        if result.returncode:
            raise RuntimeError(shlex.join(map(str, command)) + '\n' + result.stdout + result.stderr)
        return result

    def library(name, function, value, soname=None, source_text=None):
        source = root / (name + '.c')
        source.write_text(source_text or f'int {function}(void) {{ return {value}; }}\n')
        target = root / (name + '.so')
        soname_flags = [] if soname is False else ['-Wl,-soname,' + (soname or name + '.so.1')]
        run(compiler + ['-shared', '-fPIC'] + soname_flags + ['-Wl,-rpath,$ORIGIN', str(source), '-o', str(target)])
        machine = run(['readelf','-h',str(target)]).stdout
        assert ('AArch64' if cross else 'X86-64') in machine, machine
        if soname is False:
            assert '(SONAME)' not in run(['readelf','-d',str(target)]).stdout
        return target.read_bytes()

    def archive(name, function, value, source_text=None):
        source, obj, target = [root / (name + suffix) for suffix in ('.c', '.o', '.a')]
        source.write_text(source_text or f'int {function}(void) {{ return {value}; }}\n')
        run(compiler + ['-fPIC', '-c', str(source), '-o', str(obj)])
        ar = str(Path(cross['cc']).with_name('aarch64-linux-gnu-ar')) if cross else 'ar'
        run([ar, 'rcs', str(target), str(obj)])
        return target.read_bytes()

    def package(name, files, dependencies=(), suite="fixture", target_arch=None):
        package_arch = target_arch or arch
        tree = root / ('pkg-' + name)
        (tree / 'DEBIAN').mkdir(parents=True)
        (tree / 'DEBIAN/control').write_text(f'Package: {name}\nVersion: 1\nArchitecture: {package_arch}\nMaintainer: Fixture <fixture@example.invalid>\nDescription: independent library contract\n')
        for path, content in files.items():
            p = tree / path
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, str):
                p.symlink_to(content)
            else:
                p.write_bytes(content)
        deb = root / (name + '.deb')
        run(['dpkg-deb', '--root-owner-group', '-Zxz', '--build', str(tree), str(deb)])
        packages[f'/{suite}/{name}:{package_arch}=1'] = dict(name=name, version='1', suite=suite, architecture=package_arch,
            filename=deb.name, sha256=hashlib.sha256(deb.read_bytes()).hexdigest(), files=sorted(files),
            depends_on=[f'/fixture/{dep}:{arch}=1' for dep in dependencies])

    def pc(lib):
        return f'prefix=/usr\nlibdir=${{prefix}}/lib\nincludedir=${{prefix}}/include\nName: {lib}\nDescription: fixture\nVersion: 1\nLibs: -L${{libdir}} -l{lib}\nCflags: -I${{includedir}}\n'.encode()

    host_pc = root/'host-only-pc'
    host_pc.mkdir()
    (host_pc/'missing-module.pc').write_bytes(pc('pcbase'))
    env['PKG_CONFIG_PATH'] = str(host_pc)
    run(['pkg-config','--exists','missing-module'])

    # libtwo is supplied by a dependency, after libone in a different .pc file.
    package('libmulti0', {'usr/lib/libtwo.so': library('libtwo', 'two', 29, 'libtwo.so.1'), 'usr/lib/libtwo.so.1': 'libtwo.so'})
    config_files = {'etc/ld.so.conf.d/libc.conf': b'# libc default configuration\n/usr/local/lib\n',
        'usr/lib/fixture.so.conf.d/settings.conf': b'fixture-setting=preserved\n'}
    package('fixture-config', config_files)
    package('libmulti-dev', dict(config_files, **{'usr/lib/libone.so': library('libone', 'one', 13, 'libone.so.1'),
        'usr/lib/libone.so.1': 'libone.so', 'usr/lib/pkgconfig/one.pc': pc('one'), 'usr/lib/pkgconfig/two.pc': pc('two')}), ['libmulti0'])
    cases.append(('multi', 'int one(void); int two(void);', 'one()+two()', 'libmulti-dev', ()))

    package('liboptional-dev', {
        'usr/lib/liboptional.so.1': library('liboptional', 'optional_value', 42,
            source_text='int optional_state=42; int optional_value(void){return optional_state;}\n'),
        'usr/lib/liboptional.so': 'liboptional.so.1',
        'usr/lib/liboptional_ctor.a': archive('liboptional_ctor', 'optional_ctor_anchor', 0,
            source_text='extern int optional_state; void optional_ctor_anchor(void){} __attribute__((constructor)) static void init(void){optional_state=99;}\n'),
        'usr/lib/pkgconfig/liboptional.pc': pc('optional'),
        'usr/lib/pkgconfig/liboptional-plugin.pc': pc('optional').replace(b'-loptional\n', b'-loptional -Wl,-z,nodlopen\n') + b'Cflags: -DUNSELECTED_PLUGIN=1\n',
        'usr/lib/pkgconfig/liboptional-ctor.pc': pc('optional_ctor').replace(b'-loptional_ctor\n', b'-loptional_ctor -Wl,-z,nodlopen -Wl,-u,optional_ctor_anchor\n') + b'Requires: liboptional >= 1\n'})
    cases.append(('optional', '#ifdef UNSELECTED_PLUGIN\n#error unrelated module Cflags leaked\n#endif\nint optional_value(void);', 'optional_value()', 'liboptional-dev', ()))

    package('libpcpublic-dev', {'usr/lib/libpcpublic.so.1': library('libpcpublic','pc_public_value',29),
        'usr/lib/libpcpublic.so': 'libpcpublic.so.1',
        'usr/lib/libpcpublic.a': archive('pcpublic_static','pc_public_value',29),
        'usr/include/pcpublic.h': b'int pc_public_value(void);\n',
        'usr/include/sdk-priority/pcpublic.h': b'int pc_public_value(void);\n',
        'usr/lib/pkgconfig/pc-public.pc': pc('pcpublic').replace(b'Cflags: -I${includedir}', b'Cflags: -I${includedir}/sdk-priority')})
    package('libpcprivate-dev', {'usr/lib/libpcprivate.a': archive('pcprivate','pc_private_anchor',0),'usr/lib/pkgconfig/pc-private.pc': pc('pcprivate').replace(b'-lpcprivate\n',b'-lpcprivate -Wl,-z,nodlopen -Wl,-u,pc_private_anchor\n') + b'Cflags: -DPC_PRIVATE_HEADER=1\n'})
    package('libpcgraph-dev', dict(config_files, **{
        'usr/lib/libpcbase.so.1': library('libpcbase','pc_base_value',13),
        'usr/lib/libpcbase.so': 'libpcbase.so.1',
        'usr/lib/libpcbase.a': archive('pcbase_static','pc_base_value',13),
        'usr/lib/pkgconfig/libpcgraph.pc': pc('pcbase').replace(b'prefix=/usr\n',b'prefix=${pcfiledir}/../..\n').replace(b'-lpcbase\n', b'\\\n  -lpcbase\n') + b'Requires: pc-public >= 1\nRequires.private: pc-private >= 1\n',
        'usr/lib/pkgconfig/graph-alias.pc': 'libpcgraph.pc',
        'usr/lib/pkgconfig/cycle-a.pc': pc('pcbase') + b'Requires: cycle-b\n',
        'usr/lib/pkgconfig/cycle-b.pc': pc('pcpublic') + b'Requires: cycle-a\n',
        'usr/lib/pkgconfig/bad-version.pc': pc('pcbase') + b'Requires: pc-public > 99\n',
        'usr/lib/pkgconfig/missing-dep.pc': pc('pcbase') + b'Requires: missing-module\n'}))
    cases.append(('pcgraph', '#ifdef WRONG_PC_PROVIDER\n#error foreign provider selected\n#endif\n#include <pcpublic.h>\n#ifndef PC_PRIVATE_HEADER\n#error private Requires Cflags missing\n#endif\nint pc_base_value(void);', 'pc_base_value()+pc_public_value()', 'libpcgraph-dev', ()))
    module_cases['pcgraph'] = '@locked//libpcgraph-dev:pkgconfig/libpcgraph'
    package('foreign-pc-provider', {'usr/share/pkgconfig/pc-public.pc': pc('wrong') + b'Cflags: -DWRONG_PC_PROVIDER=1\n'}, suite='other')
    foreign_arch = 'arm64' if arch == 'amd64' else 'amd64'
    package('foreign-arch-provider', {'usr/share/pkgconfig/pc-public.pc': pc('wrong') + b'Cflags: -DWRONG_PC_PROVIDER=1\n'}, target_arch=foreign_arch)
    package('libpconly-dev', {
        'usr/include/pconly.h': b'extern char pc_only_marker;\n',
        'usr/share/pkgconfig/pconly.pc': b'Name: pconly\nDescription: flags without a library\nVersion: 1\nCflags: -I/usr/include -DPC_ONLY_HEADER=1\nLibs: -Wl,--defsym,pc_only_marker=42\n'})
    cases.append(('pconly', '#include <pconly.h>\n#ifndef PC_ONLY_HEADER\n#error module Cflags missing\n#endif', '(int)(long)&pc_only_marker', 'libpconly-dev', ()))
    module_cases['pconly'] = '@locked//libpconly-dev:pkgconfig/pconly'
    for case in ['pcalias', 'pccompat']:
        cases.append((case, '#ifdef WRONG_PC_PROVIDER\n#error foreign provider selected\n#endif\n#include <pcpublic.h>\n#ifndef PC_PRIVATE_HEADER\n#error private Requires Cflags missing\n#endif\nint pc_base_value(void);', 'pc_base_value()+pc_public_value()', 'libpcgraph-dev', ()))
    module_cases['pcalias'] = '@locked//libpcgraph-dev:pkgconfig/graph-alias'
    cases.append(('pccycle', 'int pc_base_value(void); int pc_public_value(void);', 'pc_base_value()+pc_public_value()', 'libpcgraph-dev', ()))
    module_cases['pccycle'] = '@locked//libpcgraph-dev:pkgconfig/cycle-a'

    package('libboundary-dev', dict(config_files, **{
        'usr/lib/libboundary.so.1': library('libboundary', 'boundary_value', 42),
        'usr/lib/libboundary_link.so': 'libboundary.so.1',
        'usr/lib/libboundary.so': 'libboundary_link.so',
        'usr/lib/libbroken.so': 'libabsent.so.1',
        'usr/lib/libcycle.so': 'libcycle_next.so',
        'usr/lib/libcycle_next.so': 'libcycle.so',
        'usr/lib/libopaque.so.1': b'\x00opaque package data',
        'usr/lib/libopaque.so': 'libopaque.so.1',
        'usr/lib/libnotes.so.1': b'ordinary text package data\n',
        'usr/lib/pkgconfig/boundary.pc': pc('boundary')}))
    cases.append(('boundary', 'int boundary_value(void);', 'boundary_value()', 'libboundary-dev', ()))
    package('libnosoname-dev', {'usr/lib/libnosoname.so.1': library('libnosoname', 'nosoname_value', 42, soname=False),
        'usr/lib/libnosoname.so': 'libnosoname.so.1', 'usr/lib/pkgconfig/nosoname.pc': pc('nosoname')})
    cases.append(('nosoname', 'int nosoname_value(void);', 'nosoname_value()', 'libnosoname-dev', ()))
    package('libarchive0', {'usr/lib/libexternal_archive.a': archive('external_archive', 'archive_value', 42)})
    package('libarchivedep-dev', {'usr/lib/pkgconfig/archivedep.pc': pc('external_archive')}, ['libarchive0'])
    cases.append(('archivedep', 'int archive_value(void);', 'archive_value()', 'libarchivedep-dev', ()))
    # Other GNU commands remain intact; only declared file operands are rewritten.
    package('libordered-first', {'usr/lib/choice/libpcordered.so': library('libpcordered', 'pc_ordered_value', 42)})
    package('libordered-second', {'usr/lib/other/libpcordered.so': library('libpcordered_decoy', 'pc_ordered_value', 99, 'libpcordered_decoy.so.1')})
    package('libdirectives-dev', {
        'usr/lib/choice/libdirective.so.1': library('libdirective', 'directive_value', 42),
        'usr/lib/other/libdirective.so.1': library('libdirective_decoy', 'directive_value', 99, 'libdirective_decoy.so.1'),
        'usr/lib/libdirectives.so': b'/* Do not interpret INPUT(/missing/comment.so). */\nSEARCH_DIR("/usr/lib/choice")\nINCLUDE "directives.ld"\nPROVIDE ( fixture_marker = 1 );\n',
        'usr/lib/directives.ld': b'INPUT ( "libdirective.so.1" )\n',
        'usr/lib/pkgconfig/directives.pc': pc('directives'),
        'usr/lib/pkgconfig/pc-ordered.pc': pc('pcordered').replace(b'-L${libdir}', b'-L${libdir}/choice -L${libdir}/other').replace(b'-lpcordered', b'-lpcordered\nLibs.private: -lm -lpcordered')}, ['libordered-first', 'libordered-second'])
    cases.append(('directives', 'int directive_value(void);', 'directive_value()', 'libdirectives-dev', ()))
    cases.append(('pcordered', 'int pc_ordered_value(void);', 'pc_ordered_value()', 'libdirectives-dev', ()))
    module_cases['pcordered'] = '@locked//libdirectives-dev:pkgconfig/pc-ordered'

    # Debian ncurses ships INPUT(libncurses.so.6 -ltinfo), with no absolute
    # filenames. Both relative filenames and -l forms must carry exact inputs.
    for case, second in [('relative', '-lrelative_info'), ('exact', '-l:libexact_info.so.1')]:
        package('lib' + case + '0', {
            'usr/lib/lib' + case + '.so.6': library('lib' + case, case + '_value', 13, 'lib' + case + '.so.6'),
            'usr/lib/lib' + case + '_info.so.1': library('lib' + case + '_info', case + '_info', 29)})
        package('lib' + case + '-dev', {
            'usr/lib/lib' + case + '.so': f'INPUT(lib{case}.so.6 {second})\n'.encode(),
            'usr/lib/lib' + case + '_info.so': 'lib' + case + '_info.so.1',
            'usr/lib/pkgconfig/' + case + '.pc': pc(case)}, ['lib' + case + '0'])
        cases.append((case, f'int {case}_value(void); int {case}_info(void);', case + '_value()+' + case + '_info()', 'lib' + case + '-dev', ()))

    for case in ['mixed', 'nested']:
        package('lib' + case + '0', {'usr/lib/lib' + case + '.so.1': library('lib' + case, case + '_dynamic', 39)})
        inner = f'GROUP ( /usr/lib/lib{case}.so.1 /usr/lib/lib{case}_static.a /usr/lib/{case}_object.o )\n'.encode()
        object_source = root / (case + '_object.c')
        object_source.write_text(f'int {case}_object(void) {{ return 1; }}\n')
        object_file = root / (case + '_object.o')
        run(compiler + ['-fPIC', '-c', str(object_source), '-o', str(object_file)])
        files = {'usr/lib/lib' + case + '_static.a': archive('lib' + case + '_static', case + '_static', 2),
            'usr/lib/' + case + '_object.o': object_file.read_bytes(),
            'usr/lib/lib' + case + '.so': inner,
            'usr/lib/pkgconfig/' + case + '.pc': pc(case)}
        if case == 'nested':
            files['usr/lib/libnested_inner.so'] = inner
            files['usr/lib/libnested.so'] = b'INPUT ( /usr/lib/libnested_inner.so )\n'
        package('lib' + case + '-dev', files, ['lib' + case + '0'])
        cases.append((case, f'int {case}_dynamic(void); int {case}_static(void); int {case}_object(void);', case + '_dynamic()+' + case + '_static()+' + case + '_object()', 'lib' + case + '-dev', ()))

    cases.append(('pcscript', 'int mixed_dynamic(void); int mixed_static(void); int mixed_object(void);', 'mixed_dynamic()+mixed_static()+mixed_object()', 'libmixed-dev', ()))
    module_cases['pcscript'] = '@locked//libmixed-dev:pkgconfig/mixed'

    # Equal filenames but distinct SONAMEs and symbols must select both exact files.
    package('libcollision-left', {'usr/lib/left/libsame.so.1': library('collision_left', 'left_value', 17, 'libleft.so.1'), 'usr/lib/left/libleft.so.1': 'libsame.so.1'})
    package('libcollision-right', {'usr/lib/right/libsame.so.1': library('collision_right', 'right_value', 25, 'libright.so.1'), 'usr/lib/right/libright.so.1': 'libsame.so.1'})
    package('libcollision-dev', {'usr/lib/libcollision.so': b'GROUP ( /usr/lib/left/libsame.so.1 /usr/lib/right/libsame.so.1 )\n',
        'usr/lib/pkgconfig/collision.pc': pc('collision')}, ['libcollision-left', 'libcollision-right'])
    cases.append(('collision', 'int left_value(void); int right_value(void);', 'left_value()+right_value()', 'libcollision-dev', ()))

    package('libneeded0', {'usr/lib/librequired.so.1': library('librequired', 'required_value', 42),
        'usr/lib/libunused.so.1': library('libunused', 'unused_value', 77)})
    package('libneeded-dev', {'usr/lib/libneeded.so': b'GROUP ( /usr/lib/librequired.so.1 AS_NEEDED ( /usr/lib/libunused.so.1 ) )\n',
        'usr/lib/pkgconfig/needed.pc': pc('needed')}, ['libneeded0'])
    cases.append(('needed', 'int required_value(void);', 'required_value()', 'libneeded-dev', ('libunused.so.1',)))
    cases.append(('pcneeded', 'int required_value(void);', 'required_value()', 'libneeded-dev', ('libunused.so.1',)))
    module_cases['pcneeded'] = '@locked//libneeded-dev:pkgconfig/needed'

    # The .pc -u flag must pull a constructor archive even though callers only
    # reference the DSO's function. This mirrors libbsd-ctor's link contract.
    package('libctor0', {'usr/lib/libctor.so.1': library('libctor', 'ctor_value', 0,
        source_text='int ctor_state=0; int ctor_value(void){return ctor_state;}\n')})
    package('libconstructor-dev', {'usr/lib/libctor.so': 'libctor.so.1',
        'usr/lib/libctor-init.a': archive('libctor-init', 'ctor_anchor', 0,
            source_text='extern int ctor_state; void ctor_anchor(void){} __attribute__((constructor)) static void init(void){ctor_state=42;}\n'),
        'usr/lib/pkgconfig/base.pc': pc('ctor'),
        'usr/lib/pkgconfig/constructor.pc': pc('ctor').replace(b'-lctor\n',b'-lctor -lctor-init -Wl,-u,ctor_anchor\n')}, ['libctor0'])
    cases.append(('constructor', 'int ctor_value(void);', 'ctor_value()', 'libconstructor-dev', ()))

    package('libconflict0', {'usr/lib/left/libfirst.so.1': library('conflict_first','conflict_first',17,'libduplicate.so.1'),
        'usr/lib/right/libsecond.so.1': library('conflict_second','conflict_second',25,'libduplicate.so.1')})
    package('libconflict-dev', {'usr/lib/libconflict.so': b'GROUP ( /usr/lib/left/libfirst.so.1 /usr/lib/right/libsecond.so.1 )\n',
        'usr/lib/pkgconfig/conflict.pc': pc('conflict')}, ['libconflict0'])


    # An unavailable private module must affect the explicit contract only.
    package('libcompatmissing-dev', dict(config_files, **{
        'usr/lib/libcompatmissing.so': library('compatmissing','compat_missing_value',42),
        'usr/lib/pkgconfig/compatmissing.pc': pc('compatmissing') + b'Requires.private: absent-private-provider >= 1\n'}))
    cases.append(('compatmissing','int compat_missing_value(void);','compat_missing_value()','libcompatmissing-dev',()))

    # Plugins with the same basename are data/runtime plugins, not link inputs
    # of the unrelated library selected by this module.
    package('libcompatformat-dev', {'usr/lib/libcompatformat.so': library('compatformat','compat_format_value',42),'usr/lib/pkgconfig/compatformat.pc': b'Libs: -L/usr/lib -lcompatformat\nCflags: -I/usr/include\n'})
    cases.append(('compatformat','int compat_format_value(void);','compat_format_value()','libcompatformat-dev',()))

    package('libplugins-dev', {
        'usr/lib/libplugins.so': library('plugins','plugin_main_value',42),
        'usr/lib/plugins/one/module.so': library('plugin_one','plugin_one_value',99,'module.so'),
        'usr/lib/plugins/two/module.so': library('plugin_two','plugin_two_value',77,'module.so'),
        'usr/lib/pkgconfig/plugins.pc': pc('plugins')})
    for case in ['plugins','pluginslegacy']:
        cases.append((case,'int plugin_main_value(void);','plugin_main_value()','libplugins-dev',('module.so',)))
    module_cases['plugins']='@locked//libplugins-dev:pkgconfig/plugins'

    package('libsystemflags-dev', {
        'usr/include/fixture-system/pc_system_value.h': b'#define PC_SYSTEM_VALUE 42\n',
        'usr/share/pkgconfig/systemflags.pc': b'Name: systemflags\nDescription: compiler contract\nVersion: 1\nCflags: -isystem /usr/include/fixture-system -DPC_SYSTEM_DEFINE=1\n',
        'usr/share/pkgconfig/unsupported.pc': b'Name: unsupported\nDescription: unsupported compile contract\nVersion: 1\nCflags: -pthread\n'})
    cases.append(('pcsystem','#include <pc_system_value.h>\n#ifndef PC_SYSTEM_DEFINE\n#error compiler define missing\n#endif','PC_SYSTEM_VALUE','libsystemflags-dev',()))
    module_cases['pcsystem']='@locked//libsystemflags-dev:pkgconfig/systemflags'

    package('libwhole-dev', {
        'usr/lib/libwhole.so': library('whole','whole_value',0,source_text='int whole_state=0; int whole_value(void){return whole_state;}\n'),
        'usr/lib/libwhole_first.a': archive('whole_first','whole_first_anchor',0,source_text='extern int whole_state; void whole_first_anchor(void){} __attribute__((constructor)) static void init(void){whole_state+=19;}\n'),
        'usr/lib/libwhole_second.a': archive('whole_second','whole_second_anchor',0,source_text='extern int whole_state; void whole_second_anchor(void){} __attribute__((constructor)) static void init(void){whole_state+=23;}\n'),
        'usr/lib/pkgconfig/whole.pc': pc('whole').replace(b'-lwhole\n',b'-lwhole -Wl,--whole-archive -lwhole_first -Wl,--no-whole-archive\nLibs.private: -Wl,--whole-archive -lwhole_second -Wl,--no-whole-archive\n')})
    cases.append(('pcwhole','int whole_value(void);','whole_value()','libwhole-dev',()))
    cases.append(('wholelegacy','int whole_value(void);','whole_value()+23','libwhole-dev',()))
    module_cases['pcwhole']='@locked//libwhole-dev:pkgconfig/whole/static'

    # Independent SDK+GNU controls establish the dynamic/private expectations.
    reference_runtime = root/'reference-runtime'
    reference_runtime.mkdir()
    shutil.copy2(root/'pkg-libwhole-dev/usr/lib/libwhole.so',reference_runtime/'whole.so.1')
    reference_source=root/'whole-reference.c'
    reference_source.write_text('#include <stdio.h>\nint whole_value(void); int main(void){printf("%d\\n",whole_value());}\n')
    pcenv=dict(env,PKG_CONFIG_PATH='',PKG_CONFIG_LIBDIR=str(root/'pkg-libwhole-dev/usr/lib/pkgconfig'))
    for mode,expected_value in [('dynamic','19'),('static','42')]:
        command=['pkg-config','--define-variable=prefix='+str(root/'pkg-libwhole-dev/usr'),'--libs']+(['--static'] if mode=='static' else [])+['whole']
        reference_flags=shlex.split(run(command,env=pcenv).stdout)
        executable=root/('whole-reference-'+mode)
        run(compiler+[str(reference_source)]+reference_flags+['-Wl,-rpath,'+str(reference_runtime),'-o',str(executable)])
        command=([str(args.qemu),'-L',cross['sysroot'],str(executable)] if cross else [str(executable)])
        assert run(command).stdout.strip()==expected_value,(mode,reference_flags)
    print('PASS independent pkg-config/GNU public=19 static=42 controls',flush=True)

    package('libmixed-first', {'usr/lib/first/libmixed.a': archive('mixed_first','mixed_value',42)})
    package('libmixed-second', {'usr/lib/second/libmixed.so': library('mixed_second','mixed_value',99,'libmixed_decoy.so.1')})
    package('libsearchorder-dev', {'usr/lib/pkgconfig/mixed.pc': pc('mixed').replace(b'-L${libdir}',b'-L ${libdir}/first -L${libdir}/second')}, ['libmixed-first','libmixed-second'])
    cases.append(('pcmixed','int mixed_value(void);','mixed_value()','libsearchorder-dev',()))
    module_cases['pcmixed']='@locked//libsearchorder-dev:pkgconfig/mixed'

    package('libswitch-dev', {
        'usr/lib/libswitch.a': archive('switch_archive','switch_value',42),
        'usr/lib/libswitch.so': library('switch_shared','switch_value',99),
        'usr/lib/pkgconfig/switch.pc': pc('switch').replace(b'-lswitch',b'-Wl,--push-state,-Bstatic -lswitch -Wl,--pop-state'),
        'usr/lib/pkgconfig/switch-dynamic.pc': pc('switch').replace(b'-lswitch',b'-Wl,--push-state,-Bdynamic -lswitch -Wl,--pop-state')})
    cases.append(('pcswitchstatic','int switch_value(void);','switch_value()','libswitch-dev',('switch_shared.so.1',)))
    module_cases['pcswitchstatic']='@locked//libswitch-dev:pkgconfig/switch'
    cases.append(('pcswitchdynamic','int switch_value(void);','switch_value()-57','libswitch-dev',()))
    module_cases['pcswitchdynamic']='@locked//libswitch-dev:pkgconfig/switch-dynamic/static'

    package('libliteral-dev', dict(config_files, **{
        'usr/lib/libliteral.a': archive('literal','literal_value',42),
        'usr/lib/pkgconfig/literal.pc': pc('literal').replace(b'-lliteral',b'-l:libliteral.a'),
        'usr/lib/pkgconfig/literal-file.pc': pc('literal').replace(b'-lliteral',b'libliteral.a')}))
    for case in ['literal','literallegacy']:
        cases.append((case,'int literal_value(void);','literal_value()','libliteral-dev',()))
    module_cases['literal']='@locked//libliteral-dev:pkgconfig/literal'
    cases.append(('literalfile','int literal_value(void);','literal_value()','libliteral-dev',()))
    module_cases['literalfile']='@locked//libliteral-dev:pkgconfig/literal-file'

    package('libscriptchild0', {'usr/lib/libscriptchild.so': library('scriptchild','script_child_value',42)})
    package('libscriptdup-dev', {'usr/lib/libscriptdup.so': b'GROUP ( -lscriptchild /usr/lib/libscriptchild.so )\n','usr/lib/pkgconfig/scriptdup.pc': pc('scriptdup')}, ['libscriptchild0'])
    cases.append(('pcscriptdup','int script_child_value(void);','script_child_value()','libscriptdup-dev',()))
    module_cases['pcscriptdup']='@locked//libscriptdup-dev:pkgconfig/scriptdup'

    package('libnames-dev', dict(config_files, **{
        'usr/lib/a_b/libx.so': library('name_plus','name_plus_value',42),
        'usr/lib/a/b_libx.so': library('name_minus','name_minus_value',42),
        'usr/lib/duplicate/libx.so': library('name_other','name_other_value',99),
        'usr/lib/pkgconfig/foo+bar.pc': pc('x').replace(b'-L${libdir}',b'-L${libdir}/a_b'),
        'usr/lib/pkgconfig/foo-bar.pc': pc('x').replace(b'-L${libdir} -lx',b'-L${libdir}/a -l:b_libx.so')}))
    for case,function,module in [('pcnameplus','name_plus_value','foo+bar'),('pcnameminus','name_minus_value','foo-bar')]:
        cases.append((case,'int '+function+'(void);',function+'()','libnames-dev',()))
        module_cases[case]='@locked//libnames-dev:pkgconfig/'+module

    # Independent module identities may share the same runtime DSO. Their
    # consumer must still link and run after their old per-module search paths
    # would exceed Linux's single argument/environment-string limit.
    scale_modules = ["scale_" + str(i) + "_" + "long_module_name_" * 8 for i in range(640)]
    scale_files = {'usr/lib/libscale.so.1': library('libscale', 'scale_value', 42, 'libscale.so.1'),
        'usr/lib/libscale.so': 'libscale.so.1'}
    scale_files.update({'usr/lib/pkgconfig/' + name + '.pc': pc('scale') for name in scale_modules})
    package('libscale-dev', scale_files)
    cases.append(('scale', 'int scale_value(void);', 'scale_value()', 'libscale-dev', ()))
    module_cases['scale'] = ':scale_modules'

    # pkg-config's dynamic contract excludes Libs.private. An unavailable
    # static-only dependency must not poison either dynamic public interface.
    package('libprivateboundary-dev', {
        'usr/lib/libprivateboundary.so.1': library('libprivateboundary', 'private_boundary_value', 42, 'libprivateboundary.so.1'),
        'usr/lib/libprivateboundary.so': 'libprivateboundary.so.1',
        'usr/lib/pkgconfig/privateboundary.pc': pc('privateboundary') + b'Libs.private: -lfixture_static_only_unavailable\n'})
    for case in ['privatelegacy', 'privatemodule']:
        cases.append((case, 'int private_boundary_value(void);', 'private_boundary_value()', 'libprivateboundary-dev', ()))
    module_cases['privatemodule'] = '@locked//libprivateboundary-dev:pkgconfig/privateboundary'

    # A package owning the libc ABI belongs to the selected toolchain at
    # execution time. Its archive stays complete, while transitive SDK CcInfo
    # must not override the executable's interpreter with a second C runtime.
    fixture_c_runtime = library('fixture-libc', 'fixture_c_marker', 0, 'libc.so.6')
    fixture_c_peer = library('fixture-c-peer', 'fixture_c_peer', 0, 'libfixture_c_peer.so.1')
    package('fixture-c-runtime', dict(config_files, **{
        'usr/lib/libc.so.6': fixture_c_runtime,
        'usr/lib/libfixture_c_peer.so.1': fixture_c_peer}))
    source = root/'systemboundary.c'
    source.write_text('int system_boundary_value(void){return 42;}\n')
    boundary = root/'libsystemboundary.so'
    run(compiler+['-shared','-fPIC',str(source),'-Wl,-soname,libsystemboundary.so.1',
        '-Wl,--no-as-needed',str(root/'fixture-libc.so'),'-Wl,--as-needed','-o',str(boundary)])
    assert '[libc.so.6]' in run(['readelf','-d',str(boundary)]).stdout
    package('libsystemboundary-dev', {
        'usr/lib/libsystemboundary.so.1': boundary.read_bytes(),
        'usr/lib/libsystemboundary.so': 'libsystemboundary.so.1',
        'usr/lib/pkgconfig/systemboundary.pc': pc('systemboundary')}, ['fixture-c-runtime'])
    for case in ['systemlegacy', 'systemmodule']:
        cases.append((case, 'int system_boundary_value(void);', 'system_boundary_value()', 'libsystemboundary-dev', ()))
    module_cases['systemmodule'] = '@locked//libsystemboundary-dev:pkgconfig/systemboundary'

    package('libplain-dev', {
        'usr/lib/libplain.so.1': library('libplain', 'plain_value', 42, 'libplain.so.1'),
        'usr/lib/libplain.so': 'libplain.so.1'})

    roots = {f'/fixture/{p}:{arch}': '1' for _, _, _, p, _ in cases}
    roots[f'/fixture/fixture-config:{arch}'] = '1'
    roots[f'/fixture/libplain-dev:{arch}'] = '1'
    (root / 'apt.lock.json').write_text(json.dumps(dict(version=2, sources={'fixture': {'uris': [root.as_uri()]},'other':{'uris':[root.as_uri()]}},
        packages=packages, dependency_sets={'locked': {'sets': {arch: roots}},
            'providers': {'sets': {arch: {f'/fixture/libpcpublic-dev:{arch}': '1',f'/fixture/libpcprivate-dev:{arch}':'1'}}},
            'foreign': {'sets': {arch: {f'/other/foreign-pc-provider:{arch}': '1'}}},
            'foreign_arch': {'sets': {foreign_arch: {f'/fixture/foreign-arch-provider:{foreign_arch}': '1'}}},
            'conflicting': {'sets': {arch: {f'/fixture/libconflict-dev:{arch}': '1'}}}})))
    adapter = root / 'adapter'
    adapter.mkdir()
    (adapter / 'MODULE.bazel').write_text('module(name="fixture_adapter")\nbazel_dep(name="rules_cc",version="0.2.20")\n')
    (adapter / 'BUILD.bazel').write_text('exports_files(["shared_library.bzl"])\n')
    (adapter / 'shared_library.bzl').symlink_to(args.adapter.resolve())
    (root / 'context.bzl').write_text('''load("@rules_cc//cc:defs.bzl", "CcInfo")
def _impl(ctx):
    flags=[]
    files=[]
    dynamic_files=[]
    for item in ctx.attr.dep[CcInfo].linking_context.linker_inputs.to_list():
        flags.extend(item.user_link_flags)
        files.extend(item.additional_inputs)
        for lib in item.libraries:
            selected=lib.interface_library or lib.dynamic_library or lib.pic_static_library or lib.static_library
            if selected:
                flags.append(selected.path)
                files.append(selected)
            if lib.dynamic_library:
                files.append(lib.dynamic_library)
                dynamic_files.append(lib.dynamic_library.path)
    compilation=ctx.attr.dep[CcInfo].compilation_context
    files.extend(compilation.headers.to_list())
    out=ctx.actions.declare_file(ctx.label.name+".json")
    ctx.actions.write(out,json.encode({"flags":flags,"files":[file.path for file in files],"dynamic_files":dynamic_files,"normal_includes":compilation.includes.to_list(),"system_includes":compilation.system_includes.to_list(),"quote_includes":compilation.quote_includes.to_list()}))
    return [DefaultInfo(files=depset([out]+files))]
link_context=rule(implementation=_impl,attrs={"dep":attr.label(providers=[CcInfo])})
''')
    (root / 'MODULE.bazel').write_text(f'''module(name="library_contracts")
bazel_dep(name="rules_distroless",version="0.9.4.sonic.18")
bazel_dep(name="rules_cc",version="0.2.20")
bazel_dep(name="fixture_adapter",version="1")
local_path_override(module_name="fixture_adapter",path="{adapter}")
apt=use_extension("@rules_distroless//apt:extensions.bzl","apt")
apt.import_lock(lock="//:apt.lock.json",libraries=True)
use_repo(apt,"locked","conflicting","providers")
''')
    if cross:
        for name, directory in [('fixture_cc',Path(cross['cc']).parent.parent),('fixture_sysroot',Path(cross['sysroot']))]:
            target=root/name
            target.mkdir()
            (target/'MODULE.bazel').write_text('module(name="'+name+'")\n')
            if name=='fixture_cc':
                for entry in directory.iterdir():
                    if entry.name not in ('BUILD.bazel','MODULE.bazel','REPO.bazel'):
                        (target/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
            else:
                (target/'root').mkdir()
                for entry in directory.iterdir():
                    if entry.name not in ('BUILD.bazel','BUILD','MODULE.bazel','REPO.bazel'):
                        (target/'root'/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
            marker = 'bin/aarch64-linux-gnu-gcc' if name == 'fixture_cc' else 'root/usr/include/stdio.h'
            (target/'BUILD.bazel').write_text('package(default_visibility=["//visibility:public"])\nexports_files(["'+marker+'"])\nfilegroup(name="files",srcs=glob(["**"]))\n')
            with (root/'MODULE.bazel').open('a') as module:
                module.write(f'bazel_dep(name="{name}",version="1")\nlocal_path_override(module_name="{name}",path="{target}")\n')
        with (root/'MODULE.bazel').open('a') as module:
            module.write('bazel_dep(name="platforms",version="1.0.0")\n')
        (root/'cross_config.bzl').symlink_to(Path(__file__).with_name('cross_toolchain_fixture.bzl').resolve())
    build = ['load("@rules_cc//cc:defs.bzl","cc_library","cc_shared_library","cc_binary")',
        'load("@fixture_adapter//:shared_library.bzl","shared_library_cc_info")', 'load(":context.bzl","link_context")', 'exports_files(["apt.lock.json"])']
    build.append('cc_library(name="scale_modules",deps=' + repr([
        '@locked//libscale-dev:pkgconfig/' + name for name in scale_modules]) + ')')
    for case, declarations, expression, pkg, _ in cases:
        (root / (case + '.c')).write_text(declarations + f'\nint {case}_answer(void) {{ return {expression}; }}\n')
        (root / (case + '_leaf.c')).write_text(f'int {case}_answer(void); int {case}_downstream(void) {{ return {case}_answer()+2; }}\n')
        (root / (case + '_main.c')).write_text(f'#include <stdio.h>\nint {case}_downstream(void); int main(void) {{ printf("%d\\n",{case}_downstream()); return 0; }}\n')
        interface = module_cases.get(case, f'@locked//{pkg}:{pkg.removesuffix("-dev")}')
        build += [f'cc_library(name="{case}_objects",srcs=["{case}.c"],deps=["{interface}"])',
            f'cc_shared_library(name="{case}_bridge",deps=[":{case}_objects"],user_link_flags=["-Wl,-z,defs","-Wl,--as-needed","-Wl,-rpath,$ORIGIN","-Wl,-soname,lib{case}_bridge.so"])',
            f'shared_library_cc_info(name="{case}_link",shared_library=":{case}_bridge")',
            f'cc_library(name="{case}_leaf",srcs=["{case}_leaf.c"],deps=[":{case}_objects"])',
            f'cc_shared_library(name="{case}_downstream",deps=[":{case}_leaf"],dynamic_deps=[":{case}_bridge"],user_link_flags=["-Wl,-z,defs","-Wl,--as-needed","-Wl,-rpath,$ORIGIN","-Wl,-soname,lib{case}_downstream.so"])',
            f'shared_library_cc_info(name="{case}_downstream_link",shared_library=":{case}_downstream")',
            f'cc_binary(name="{case}_consumer",srcs=["{case}_main.c"],deps=[":{case}_downstream_link"],linkopts=["-Wl,-rpath,$$ORIGIN/../lib"])']
    build.append('link_context(name="legacy_header_context",dep="@providers//libpcpublic-dev:libpcpublic")')
    build.append('link_context(name="strict_header_context",dep="@providers//libpcpublic-dev:pkgconfig/pc-public")')
    build.append('link_context(name="language_context",dep=":multi_downstream_link")')
    build.append('link_context(name="foreign_context",dep="@locked//libprivateboundary-dev:libprivateboundary")')
    build.append('link_context(name="foreign_plain_context",dep="@locked//libplain-dev:libplain")')
    build.append('link_context(name="system_runtime_context",dep="@locked//libsystemboundary-dev:libsystemboundary")')
    (root/'explicit_ctor.c').write_text('int optional_value(void); int ctor_selected(void){return optional_value();}\n')
    build += ['cc_library(name="explicit_ctor_objects",srcs=["explicit_ctor.c"],deps=["@locked//liboptional-dev:liboptional_cc","@locked//liboptional-dev:liboptional_ctor_static"])',
        'cc_shared_library(name="explicit_ctor",deps=[":explicit_ctor_objects"])']
    build += ['cc_library(name="explicit_plugin_objects",srcs=["explicit_ctor.c"],deps=["@locked//liboptional-dev:pkgconfig/liboptional-plugin"])',
        'cc_shared_library(name="explicit_plugin",deps=[":explicit_plugin_objects"])',
        'cc_library(name="graph_static_objects",srcs=["pcgraph.c"],deps=["@locked//libpcgraph-dev:pkgconfig/libpcgraph/static"])',
        'cc_shared_library(name="graph_static",deps=[":graph_static_objects"])']
    if not cross:
        headers = root/'python_headers'
        shutil.copytree(sysconfig.get_paths()['include'],headers)
        (root/'optional_python.c').write_text('''#include <Python.h>
extern int optional_downstream(void);
static PyObject *answer(PyObject *self, PyObject *args){return PyLong_FromLong(optional_downstream());}
static PyMethodDef methods[]={{"answer",answer,METH_NOARGS,"answer"},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"optional_python",NULL,-1,methods};
PyMODINIT_FUNC PyInit_optional_python(void){return PyModule_Create(&module);}
''')
        build += ['cc_library(name="python_headers",hdrs=glob(["python_headers/**"]),includes=["python_headers"])',
            'cc_binary(name="optional_python.so",srcs=["optional_python.c"],linkshared=True,deps=[":python_headers",":optional_downstream_link"],linkopts=["-Wl,-rpath,$$ORIGIN/../lib"])']
    payload_packages = ["libnames-dev", "libliteral-dev", "libcompatmissing-dev", 'fixture-config', 'libmulti-dev', 'libboundary-dev', 'libpcgraph-dev', 'fixture-c-runtime']
    build.append('filegroup(name="package_inputs",srcs=[' + ','.join(f'"@locked//{pkg}/{arch}:{kind}"' for pkg in payload_packages for kind in ['deb', 'data', 'control']) + '])')
    if cross:
        version=run([cross['cc'],'-dumpversion']).stdout.strip()
        build += ['load(":cross_config.bzl","cross_config")', 'load("@rules_cc//cc:defs.bzl","cc_toolchain")',
            f'cross_config(name="cross_config",compiler="@fixture_cc//:bin/aarch64-linux-gnu-gcc",sysroot_marker="@fixture_sysroot//:root/usr/include/stdio.h",gcc_version="{version}")',
            'filegroup(name="cross_files",srcs=["@fixture_cc//:files","@fixture_sysroot//:files"])',
            'cc_toolchain(name="cross_cc",toolchain_identifier="fixture_aarch64_gcc",toolchain_config=":cross_config",all_files=":cross_files",ar_files=":cross_files",as_files=":cross_files",compiler_files=":cross_files",dwp_files=":cross_files",linker_files=":cross_files",objcopy_files=":cross_files",strip_files=":cross_files",supports_param_files=1)',
            'platform(name="arm64",constraint_values=["@platforms//cpu:arm64","@platforms//os:linux"])',
            'toolchain(name="cross_toolchain",toolchain=":cross_cc",toolchain_type="@bazel_tools//tools/cpp:toolchain_type",exec_compatible_with=["@platforms//cpu:x86_64","@platforms//os:linux"],target_compatible_with=["@platforms//cpu:arm64","@platforms//os:linux"])']
    (root/'conflict.c').write_text('int conflict_first(void); int conflict_second(void); int main(void){return conflict_first()+conflict_second();}\n')
    build.append('cc_binary(name="conflict_consumer",srcs=["conflict.c"],deps=["@conflicting//libconflict-dev:libconflict"])')
    build.append('link_context(name="plugin_context",dep="@locked//libplugins-dev:pkgconfig/plugins")')
    (root / 'BUILD.bazel').write_text('\n'.join(build)+'\n')
    (root / 'sandbox').mkdir()
    bazel = ['bazel','--nohome_rc','--nosystem_rc','--max_idle_secs=60']
    flags = ['--registry='+args.registry.resolve().as_uri(),'--registry=https://bcr.bazel.build','--spawn_strategy=sandboxed','--jobs=2']
    if cross:
        flags += ['--platforms=//:arm64','--extra_toolchains=//:cross_toolchain']

    def execute(file, cwd):
        command=[str(args.qemu),'-L',cross['sysroot'],str(file)] if cross else [str(file)]
        return run(command,cwd=cwd).stdout.strip()
    # Ordinary package interfaces must work before any native library is built.
    result = run(bazel+['build']+flags+['//:package_inputs'],cwd=root)
    (root/'package-inputs.log').write_text(result.stdout+result.stderr)
    outputs = run(bazel+['cquery']+flags+['//:package_inputs','--output=files'],cwd=root).stdout.splitlines()
    execroot = Path(run(bazel+['info']+flags+['execution_root'],cwd=root).stdout.strip())
    archives = [execroot / file for file in outputs]
    for pkg in payload_packages:
        selected = [file for file in archives if '_'+pkg+'-' in str(file)]
        deb = next(file for file in selected if file.name == 'package.deb')
        assert deb.read_bytes() == (root/(pkg+'.deb')).read_bytes(), pkg
        data = next(file for file in selected if file.name == 'content.tar.gz')
        with tarfile.open(data) as archive:
            entries = {item.name.removeprefix('./'): item for item in archive.getmembers()}
            for path, content in config_files.items():
                assert archive.extractfile(entries[path]).read() == content, (pkg,path)
            if pkg == 'fixture-c-runtime':
                assert archive.extractfile(entries['usr/lib/libc.so.6']).read() == fixture_c_runtime
                assert archive.extractfile(entries['usr/lib/libfixture_c_peer.so.1']).read() == fixture_c_peer
            if pkg == 'libboundary-dev':
                for name, destination in [('libbroken.so', 'libabsent.so.1'), ('libcycle.so', 'libcycle_next.so'), ('libcycle_next.so', 'libcycle.so')]:
                    member = entries['usr/lib/'+name]
                    assert member.issym() and member.linkname == destination,(name,member.linkname)
                assert archive.extractfile(entries['usr/lib/libopaque.so.1']).read() == b'\x00opaque package data'
                assert archive.extractfile(entries['usr/lib/libnotes.so.1']).read() == b'ordinary text package data\n'
        control = next(file for file in selected if file.name.startswith('control.tar'))
        with tarfile.open(control) as archive:
            member = next(item for item in archive.getmembers() if item.name.removeprefix('./') == 'control')
            assert ('Package: '+pkg+'\n').encode() in archive.extractfile(member).read(),pkg
    print('PASS deb/data/control preserve plain configuration files, alone and beside native libraries',flush=True)
    metadata = run(bazel+['build']+flags+['@locked//libpconly-dev:pkgconfig'],cwd=root)
    pc_outputs = run(bazel+['cquery']+flags+['@locked//libpconly-dev:pkgconfig','--output=files'],cwd=root).stdout.splitlines()
    assert len(pc_outputs)==1 and pc_outputs[0].endswith('/usr/share/pkgconfig/pconly.pc'),pc_outputs
    assert (execroot/pc_outputs[0]).read_bytes()==(root/'pkg-libpconly-dev/usr/share/pkgconfig/pconly.pc').read_bytes()
    print('PASS usr/share original pkgconfig export',flush=True)
    for label, message in [('@locked//libcompatmissing-dev:pkgconfig/compatmissing','absent-private-provider'),('@locked//libsystemflags-dev:pkgconfig/unsupported','CcInfo cannot propagate'),('@locked//libnames-dev:libx_cc','Ambiguous shared library'),('@locked//libcompatformat-dev:pkgconfig/compatformat','pkg-config module compatformat')]:
        result=subprocess.run(bazel+['build']+flags+[label],cwd=root,env=env,text=True,capture_output=True)
        assert result.returncode and message in result.stdout+result.stderr,(label,result.stdout+result.stderr)
        print('PASS explicit compiler/dependency diagnostic isolated:',label,flush=True)
    for module in ['bad-version', 'missing-dep']:

        result = subprocess.run(bazel+['build']+flags+['@locked//libpcgraph-dev:pkgconfig/'+module],cwd=root,env=env,text=True,capture_output=True)
        (root/(module+'.log')).write_text(result.stdout+result.stderr)
        assert result.returncode and 'pkg-config module '+module in result.stdout+result.stderr,(module,result.stdout+result.stderr)
        print('PASS module dependency error isolated:',module,flush=True)
    for name, message in [('libbroken_cc', 'Unresolved native symlink'), ('libcycle_cc', 'Cyclic native symlink'), ('libopaque_cc', 'Cannot inspect native shared library')]:
        result = subprocess.run(bazel+['build']+flags+['@locked//libboundary-dev:'+name],cwd=root,env=env,text=True,capture_output=True)
        (root/(name+'.log')).write_text(result.stdout+result.stderr)
        assert result.returncode and message in result.stdout+result.stderr,(name,result.stdout+result.stderr)
        print('PASS native-only error:',name,flush=True)
    with (root / 'build.log').open('w') as log:
        result = subprocess.run(bazel+['build']+flags+['//:'+case+'_consumer' for case, *_ in cases]+['//:language_context','//:legacy_header_context','//:strict_header_context','//:foreign_context','//:foreign_plain_context','//:system_runtime_context','//:plugin_context','//:explicit_ctor','//:explicit_plugin','//:graph_static']+(['//:optional_python.so'] if not cross else []),cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit('Fixture build failed: '+str(root/'build.log'))
    # Legacy SDK headers remain system headers, so a source -I can override
    # them even when a foreign build forwards dependency flags directly to cc1.
    source_headers=root/'source-header-priority'
    source_headers.mkdir()
    (source_headers/'pcpublic.h').write_text('#define SOURCE_HEADER_SELECTED 1\n')
    priority_source=root/'header-priority.c'
    priority_source.write_text('#include <pcpublic.h>\n#ifndef SOURCE_HEADER_SELECTED\n#error SDK_overrode_source_header\n#endif\n')
    for label, succeeds in [('legacy_header_context', True), ('strict_header_context', False)]:
        context=json.loads((root/('bazel-bin/'+label+'.json')).read_text())
        operands=[]
        for option,key in [('-I','normal_includes'),('-isystem','system_includes'),('-iquote','quote_includes')]:
            for directory in context[key]:
                operands.extend([option, str(execroot/directory)])
        response=root/(label+'.rsp')
        operands.extend(['-I',str(source_headers)])
        response.write_text(shlex.join(operands))
        result=subprocess.run(compiler+['-Wp,@'+str(response),'-fsyntax-only',str(priority_source)],cwd=root,env=env,text=True,capture_output=True)
        assert (result.returncode==0)==succeeds,(label,result.stderr)
        if not succeeds:
            assert 'SDK_overrode_source_header' in result.stderr,result.stderr
    print('PASS legacy SDK header precedence and strict module include category',flush=True)
    # configure_make collects LibraryToLink dynamic files into a flat prefix;
    # its original .pc then resolves an ordinary -l name against that prefix.
    for label, libname, declaration, expression in [
        ('foreign_context', 'privateboundary', 'int private_boundary_value(void);', 'private_boundary_value()'),
        ('foreign_plain_context', 'plain', 'int plain_value(void);', 'plain_value()'),
        ('system_runtime_context', 'systemboundary', 'int system_boundary_value(void);', 'system_boundary_value()'),
    ]:
        foreign_prefix = root/label
        (foreign_prefix/'lib').mkdir(parents=True)
        foreign_context = json.loads((root/('bazel-bin/'+label+'.json')).read_text())
        for path in foreign_context['dynamic_files']:
            source = execroot/path
            destination = foreign_prefix/'lib'/source.name
            if destination.exists():
                assert destination.read_bytes() == source.read_bytes(), source.name
                continue
            shutil.copy2(source, destination)
        source = foreign_prefix/'consumer.c'
        source.write_text(declaration+' int main(void){return ('+expression+')==42?0:1;}\n')
        run(compiler+[str(source), '-L'+str(foreign_prefix/'lib'), '-l'+libname, '-Wl,-rpath,$ORIGIN/lib', '-o', str(foreign_prefix/'consumer')])
        assert execute(foreign_prefix/'consumer', foreign_prefix) == ''
        print('PASS foreign dependency-prefix consumer resolves the original -l alias:', label, flush=True)
    runtime_context=json.loads((root/'bazel-bin/system_runtime_context.json').read_text())
    assert not any('libc.so.6' in path or 'fixture_c_peer' in path for path in runtime_context['dynamic_files']),runtime_context
    print('PASS toolchain C runtime excluded from transitive SDK runtime; complete libc archive retained',flush=True)
    plugin_context=json.loads((root/'bazel-bin/plugin_context.json').read_text())
    assert not any('module.so' in value or '/plugins/one/' in value or '/plugins/two/' in value for value in plugin_context['flags']+plugin_context['files']),plugin_context
    ordinary_dynamic = run(['readelf','-d',str(root/'bazel-bin/liboptional_bridge.so')]).stdout
    assert 'NOOPEN' not in ordinary_dynamic, 'Optional static pkg-config flags leaked into the default dynamic interface:\n'+ordinary_dynamic
    selected_dynamic = run(['readelf','-d',str(root/'bazel-bin/libexplicit_ctor.so')]).stdout
    assert 'NOOPEN' in selected_dynamic, selected_dynamic
    for target in ['explicit_plugin', 'graph_static']:
        dynamic = run(['readelf','-d',str(root/'bazel-bin'/('lib'+target+'.so'))]).stdout
        assert 'NOOPEN' in dynamic,(target,dynamic)
    print('PASS explicit constructor interface retains NOOPEN',flush=True)
    result = subprocess.run(bazel+['build']+flags+['//:conflict_consumer'],cwd=root,env=env,text=True,capture_output=True)
    (root/'conflict.log').write_text(result.stdout+result.stderr)
    assert result.returncode and 'Ambiguous native shared library libduplicate.so.1' in result.stdout+result.stderr,result.stdout+result.stderr
    print('PASS conflicting SONAME rejected before linking',flush=True)
    for case, _, _, _, forbidden in cases:
        for target in [case+'_bridge',case+'_downstream']:
            dynamic = run(['readelf','-d',str(root/'bazel-bin'/('lib'+target+'.so'))]).stdout
            assert 'NOOPEN' not in dynamic,(target,dynamic)
            for name in forbidden:
                assert '['+name+']' not in dynamic,(target,dynamic)
        output = execute(root/'bazel-bin'/(case+'_consumer'),root)
        assert output=='44',(case,output)
        print('PASS',case,'clean Bazel loading =',output,flush=True)
    # Assemble an install layout from the produced DSOs and the fixture's pinned
    # runtime packages. Hide the entire build tree while executing it, so neither
    # preloads nor old Bazel paths can mask missing runtime files.
    install = Path(tempfile.mkdtemp(prefix='apt-installed-contract-'))
    (install/'lib').mkdir()
    (install/'bin').mkdir()
    for tree in root.glob('pkg-*'):
        # The deliberately incomplete libc ABI is a metadata sentinel. Installed
        # consumers use the real compiler/emulator C runtime, as native builds do.
        if tree.name == 'pkg-fixture-c-runtime':
            continue
        for file in tree.rglob('*'):
            if not file.is_file() or file.read_bytes()[:4] != b'\x7fELF':
                continue
            dynamic = run(['readelf','-d',str(file)]).stdout
            names = re.findall(r'\(SONAME\).*\[([^]]+)\]',dynamic)
            if names:
                shutil.copy2(file,install/'lib'/names[0])
            elif '.so' in file.name:
                shutil.copy2(file,install/'lib'/file.name)
    for case, *_ in cases:
        for name in [case+'_bridge',case+'_downstream']:
            shutil.copy2(root/'bazel-bin'/('lib'+name+'.so'),install/'lib'/('lib'+name+'.so'))
        shutil.copy2(root/'bazel-bin'/(case+'_consumer'),install/'bin'/(case+'_consumer'))
    if not cross:
        shutil.copy2(root/'bazel-bin/optional_python.so',install/'bin/optional_python.so')
    context=json.loads((root/'bazel-bin/language_context.json').read_text())
    execroot=Path(run(bazel+['info']+flags+['execution_root'],cwd=root).stdout.strip())
    foreign_flags=context['flags']+['-Wl,-rpath,$ORIGIN/../lib']
    if args.go:
        source=root/'consumer.go'
        source.write_text('package main\n/* int multi_downstream(void); */\nimport "C"\nimport "fmt"\nfunc main(){fmt.Println(int(C.multi_downstream()))}\n')
        goenv=dict(env,CGO_ENABLED='1',GO111MODULE='off',GOPROXY='off',GOSUMDB='off',GOCACHE=str(root/'go-cache'),GOPATH=str(root/'gopath'),CGO_LDFLAGS=shlex.join(foreign_flags))
        run([str(args.go),'build','-o',str(install/'bin/go_consumer'),str(source)],cwd=execroot,env=goenv)
    if args.rustc:
        source=root/'consumer.rs'
        source.write_text('extern "C" { fn multi_downstream() -> i32; }\nfn main(){println!("{}",unsafe{multi_downstream()});}\n')
        command=[str(args.rustc),'--edition=2021',str(source),'-o',str(install/'bin/rust_consumer')]
        for flag in foreign_flags:
            command+=['-C','link-arg='+flag]
        run(command,cwd=execroot)
    hidden=root.with_name(root.name+'.hidden')
    root.rename(hidden)
    try:
        for executable in sorted((install/'bin').iterdir()):
            if executable.suffix == '.so':
                continue
            output=execute(executable,install)
            assert output=='44',(executable,output)
            print('PASS installed clean loading',executable.name,'=',output,flush=True)
        if not cross:
            result=run([sys.executable,'-I','-c','import sys; sys.path.insert(0,sys.argv[1]); import optional_python; print(optional_python.answer())',str(install/'bin')],cwd=install)
            assert result.stdout.strip()=='44',result.stdout
            print('PASS installed CPython extension import = 44',flush=True)
    finally:
        hidden.rename(root)
    print('PASS all native library contracts; installed evidence:',install,flush=True)


if __name__ == '__main__':
    main()
