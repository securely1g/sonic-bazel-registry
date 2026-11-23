"""CPython profile counters from declared source-built executables and inputs."""
import ast
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import struct
import sys
import tarfile
import tempfile



def declared_test_data(root):
    """Use the frozen public runtime's data paths without changing Python paths."""
    manifest = json.loads((root / 'toolchain.json').read_text())
    if manifest.get('format_version') != 1 or manifest.get('profile') != 'python_build':
        raise RuntimeError('Original CPython checks require the declared Python test runtime')
    paths = manifest['data_environment']
    expected = {'LOCPATH', 'TCL_LIBRARY', 'TK_LIBRARY', 'TZDIR', 'PYTHONTZPATH'}
    if set(paths) != expected:
        raise RuntimeError('Declared Python test data environment does not match the frozen interface')
    result = {}
    for name, relative in paths.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise RuntimeError('Invalid declared Python test data path: ' + relative)
        target = root / path
        valid = target.is_dir()
        if not valid:
            raise RuntimeError('Missing original Python test data: ' + str(target))
        result[name] = str(target)
    return result


def freeze(argv):
    tool, module, source, header, profile = argv
    header, profile = Path(header).absolute(), Path(profile).absolute()
    profile.mkdir(parents=True, exist_ok=True)
    header.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, GCOV_PREFIX=str(profile), GCOV_PREFIX_STRIP='1')
    subprocess.run([str(Path(tool).absolute()), module, str(Path(source).absolute()), str(header)],
                   env=environment, check=True)


def extraction(archive, root):
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            if member.name.startswith('/') or '..' in Path(member.name).parts:
                raise ValueError('invalid runtime archive path: ' + member.name)
        stream.extractall(root, filter='fully_trusted')


def original_excludes(rules):
    text = rules.read_text().replace('\\\n', ' ')
    # These are the source's unconditional AMD64/Linux TEST_EXCLUDES. Other
    # architecture/debug/buildd choices are outside the five selected packages.
    common = set()
    for match in re.finditer(r'^TEST_EXCLUDES[ \t]*\+?=[ \t]*([^\n]*)$', text, re.M):
        common.update(match[1].split())
    audio = re.search(r'ifeq \(,\$\(wildcard /dev/dsp\)\)\n[ \t]+TEST_EXCLUDES \+= ([^\n]+)\nendif', text)
    if not audio:
        raise ValueError('missing original audio-device exclusion condition')
    if not Path('/dev/dsp').exists():
        common.update(audio[1].split())
    profile = set()
    for match in re.finditer(r'^PROFILE_EXCLUDES[ \t]*\+?=[ \t]*([^\n]*)$', text, re.M):
        profile.update(match[1].split())
    if not profile:
        raise ValueError('missing original PROFILE_EXCLUDES')
    return sorted(common | profile)


def elf_execution_identity(path):
    """Allocated code, relocation bytes, CET property and linker Build-ID."""
    data = Path(path).read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('expected original AMD64 ELF64 little-endian artifact')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, header[6] + i * header[11]) for i in range(header[12])]
    strings = sections[header[13]]
    names = data[strings[4]:strings[4] + strings[5]]
    identity = {}
    for section in sections:
        name = names[section[0]:].split(b'\0', 1)[0].decode()
        if name in ('.text', '.note.gnu.build-id', '.note.gnu.property') or section[1] in (4, 9):
            identity[name] = hashlib.sha256(data[section[4]:section[4] + section[5]]).hexdigest()
    if '.text' not in identity or '.note.gnu.build-id' not in identity:
        raise ValueError('missing native text/Build-ID identity')
    return identity


def elf_layout(path):
 data=path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',data);ph=[struct.unpack_from('<IIQQQQQQ',data,h[5]+i*h[9]) for i in range(h[10])];sh=[struct.unpack_from('<IIQQQQIIQQ',data,h[6]+i*h[11]) for i in range(h[12])];needed=[];soname=None;search_paths=[]
 for section in sh:
  if section[1]==6:
   strings=sh[section[6]];table=data[strings[4]:strings[4]+strings[5]]
   for off in range(section[4],section[4]+section[5],16):
    tag,value=struct.unpack_from('<QQ',data,off)
    if tag in [1,14,15,29]:
     name=table[value:].split(b'\0',1)[0].decode()
     if tag==14:soname=name
     elif tag==1:needed.append(name)
     else:search_paths.append(name)
 return {'PT_LOAD':[list(x) for x in ph if x[0]==1],'NEEDED':needed,'soname':soname,'search_paths':search_paths}


def merge_fallback_profiles(work, profile, gcov, origin="source_view"):
    """Merge only action-owned relative fallback counters using GCC's tool."""
    receipts = []
    roots = sorted(work.rglob('sonic-fips-cpython-pgo'))
    for namespace in roots:
        if namespace.is_symlink() or not namespace.resolve().is_relative_to(work.resolve()):
            raise RuntimeError('fallback profile namespace escapes the owned short work tree')
        files = sorted(namespace.rglob('*.gcda'))
        if not files:
            continue
        rows = []
        with tempfile.TemporaryDirectory(prefix='merge-', dir=work) as temporary:
            temporary = Path(temporary)
            staged, merged = temporary / 'input', temporary / 'output'
            for source in files:
                if source.is_symlink() or not source.resolve().is_relative_to(work.resolve()):
                    raise RuntimeError('fallback counter escapes owned work tree')
                target = staged / 'sonic-fips-cpython-pgo' / source.relative_to(namespace)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                rows.append({'source': str(source.relative_to(work)),
                             'final_use_path': str(target.relative_to(staged)),
                             'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
            subprocess.run(gcov + ['merge', '-o', str(merged), str(profile), str(staged)], check=True)
            # Keep the live workload log and declared TreeArtifact root intact.
            for source in merged.rglob('*.gcda'):
                target = profile / source.relative_to(merged)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        shutil.rmtree(namespace)
        receipts.append({'origin': origin, 'owned_root': str(work), 'namespace': str(namespace.relative_to(work)), 'counters': rows,
                         'merge': 'selected GCC gcov-tool merge', 'source': 'owned relative fallback'})
    return receipts


def main(specfile, profile, report):
    root = Path.cwd()
    spec = json.loads(Path(specfile).read_text())
    if spec['workload'] == 'original' and not spec.get('test_data_runtime'):
        raise RuntimeError('Original PROFILE_TASK requires declared Python test data')
    resolve = lambda p: (root / p).absolute()
    profile, report = Path(profile).absolute(), Path(report).absolute()
    profile.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(os.environ['TEST_TMPDIR']).absolute()
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pf-', dir=temporary_root) as temporary, tempfile.TemporaryDirectory(prefix='pt-', dir=temporary_root) as fixture_temporary:
        work = Path(temporary)
        source = resolve(spec['source_root'])
        build = work / 'build'
        build.mkdir()
        extensions = build / 'lib.linux-x86_64-3.13'
        extensions.mkdir()
        regular_fixtures = []
        for filename in spec['source_files']:
            file = resolve(filename)
            relative = file.relative_to(source)
            target = work / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Preserve the two lstat/readlink fixtures and the freeze entry
            # script: Python resolves a script symlink before setting sys.path[0].
            # Its sibling imports and pycache must remain in this owned view.
            if str(relative) in ('Lib/test/archivetestdata/testtar.tar', 'Lib/test/test_os.py', 'Tools/freeze/freeze.py'):
                shutil.copy2(file, target)
                old, new = file.stat(), target.stat()
                digest = hashlib.sha256(file.read_bytes()).hexdigest()
                if ((old.st_mode & 0o7777, old.st_mtime_ns) != (new.st_mode & 0o7777, new.st_mtime_ns)
                        or digest != hashlib.sha256(target.read_bytes()).hexdigest()):
                    raise RuntimeError('regular test fixture bytes/mode/mtime changed')
                regular_fixtures.append({'source': str(relative), 'sha256': digest,
                                         'mode': oct(new.st_mode & 0o7777), 'mtime_ns': new.st_mtime_ns})
            else:
                target.symlink_to(file)
        # Original SONiC Makefile touches this missing Git-archive release file.
        news = work / 'Misc/NEWS'
        if not news.exists():
            news.write_bytes(b'')
        (work / 'Modules').mkdir(exist_ok=True)
        local_setup = work / 'Modules/Setup.local'
        if local_setup.is_symlink():
            local_setup.unlink()
        local_setup.write_bytes(resolve(spec['setup_local']).read_bytes())
        (work / 'pybuilddir.txt').write_text('build/lib.linux-x86_64-3.13')
        for key, destination in [('makefile', 'Makefile'), ('pyconfig', 'pyconfig.h')]:
            target = work / destination
            if target.is_symlink():
                target.unlink()
            shutil.copyfile(resolve(spec[key]), target)
        variables = ast.literal_eval(resolve(spec['metadata']).read_text().split('build_time_vars = ', 1)[1])
        compiler_runtime = work / 'compiler-runtime'
        compiler_runtime.symlink_to(resolve(spec['shell']).parent.parent, target_is_directory=True)
        compiler_shell = compiler_runtime / 'bin/sh'
        for name, arguments in spec['compilers'].items():
            wrapper = work / Path(arguments[0]).name
            # SDK paths are declared execroot inputs; make them independent of
            # the test's own temporary working directories.
            def absolute_argument(argument):
                for prefix in ('--sysroot=', '-isystem', '-iquote', '-idirafter', '-I', '-L', '-B'):
                    if argument.startswith(prefix) and len(argument) > len(prefix):
                        return prefix + str(resolve(argument[len(prefix):]))
                return str(resolve(argument)) if argument.startswith(('external/', 'bazel-out/')) else argument
            command = [absolute_argument(argument) for argument in arguments]
            links = [absolute_argument(argument) for argument in spec['link_flags']]
            for directory in spec.get('compiler_library_directories', []):
                directory = str(resolve(directory))
                links += ['-L' + directory, '-Wl,-rpath-link,' + directory]
            # Test-created executables use the same declared target loader and
            # libc as the copied interpreter; these wrappers are training-only.
            # Test-created Python builds own their new core in the original
            # build directory or prefix/lib. Keep the outer CPython core out of
            # this compiler context; it belongs only to the execution view.
            test_libraries = ['$ORIGIN', '$ORIGIN/../lib', work / 'runtime/usr/lib/x86_64-linux-gnu'] + [
                resolve(p) for p in spec.get('target_runtime_directories', []) + spec.get('compiler_library_directories', [])]
            links += ['-Wl,--disable-new-dtags', '-Wl,--dynamic-linker=' + str(resolve(spec['loader'])),
                      '-Wl,-rpath,' + ':'.join(str(p) for p in dict.fromkeys(test_libraries))]
            wrapper.write_text('#!' + str(compiler_shell) + '\nset -eu\ncompile=false\nfor arg in "$@"; do [ "$arg" != -c ] || compile=true; done\nif "$compile"; then exec ' + shlex.join(command) + ' "$@"; fi\n' +
                               'skip_output=false\nfor arg in "$@"; do\nif "$skip_output"; then skip_output=false; continue; fi\nif [ "$arg" = -o ]; then skip_output=true; continue; fi\ncase "$arg" in ' + shlex.quote(str(work)) + '/*.so*|' + shlex.quote(str(fixture_temporary)) + '/*.so*)\n' +
                               '[ -f "$arg" ] || continue\nresolved=$(' + shlex.quote(str(compiler_runtime / 'bin/readlink')) + ' -f -- "$arg")\n' +
                               'case "$resolved" in ' + shlex.quote(str(work)) + '/*|' + shlex.quote(str(fixture_temporary)) + '/*) set -- "$@" "-Wl,-rpath,${arg%/*}" ;; esac\n' +
                               ';; esac\ndone\nexec ' + shlex.join(command + links) + ' "$@"\n')
            wrapper.chmod(0o755)
            variables[name] = str(wrapper)

        # This is the original static variant, rather than the shared build's
        # separately installed sysconfig metadata.
        variables.update(Py_ENABLE_SHARED=0, PY_ENABLE_SHARED=0, LDLIBRARY='libpython3.13.a', BLDLIBRARY='libpython3.13.a',
                         RUNSHARED='', PY3LIBRARY='', VPATH='', srcdir=str(source), abs_srcdir=str(source), abs_builddir=str(work))
        for key, value in spec.get('build_configuration', {}).items():
            variables[key] = value.replace('@SOURCE_ROOT@', str(source)).replace(
                '@EXECUTION_TOOLS@', str(resolve(spec['shell']).parent.parent)).replace(
                '@CC@', variables['CC']).replace('@CXX@', variables['CXX'])
        variables['CONFIG_ARGS'] = shlex.join([arg for arg in shlex.split(variables.get('CONFIG_ARGS', '')) if arg != '--enable-shared'])
        # Original GCC configure branch and the flags actually used by this
        # native stage. Installed shared metadata remains unchanged.
        variables.update(PGO_PROF_GEN_FLAG='-fprofile-generate',
                         PGO_PROF_USE_FLAG='-fprofile-use -fprofile-correction',
                         LLVM_PROF_MERGER='true')
        stage_flags = '-fprofile-generate=.'
        if stage_flags:
            variables['PY_CFLAGS_NODIST'] = (variables.get('PY_CFLAGS_NODIST', '') + ' ' + stage_flags).strip()
            variables['CFLAGS_NODIST'] = (variables.get('CFLAGS_NODIST', '') + ' ' + stage_flags).strip()
        variables['PY_LDFLAGS_NODIST'] = (variables.get('PY_LDFLAGS_NODIST', '') + ' -fprofile-generate=.').strip()
        variables['LDFLAGS_NODIST'] = (variables.get('LDFLAGS_NODIST', '') + ' -fprofile-generate=.').strip()
        metadata = extensions / '_sysconfigdata__linux_x86_64-linux-gnu.py'
        runtime = work / 'runtime'
        runtime.mkdir()
        for payload in spec['runtime_payloads']:
            extraction(resolve(payload), runtime)
        sealed_inputs = []
        for payload in spec['runtime_payloads']:
            with tarfile.open(resolve(payload)) as archive:
                for member in archive.getmembers():
                    if member.isfile() and 'symcrypt' in Path(member.name).name:
                        original_bytes = archive.extractfile(member).read()
                        staged = runtime / member.name.removeprefix('./')
                        digest = hashlib.sha256(original_bytes).hexdigest()
                        if hashlib.sha256(staged.read_bytes()).hexdigest() != digest:
                            raise RuntimeError('sealed SymCrypt runtime bytes changed')
                        sealed_inputs.append({'payload': payload, 'member': member.name, 'sha256': digest})
        libraries = [runtime / 'usr/lib/x86_64-linux-gnu']
        libraries += [resolve(path) for path in spec['library_directories']]
        library_path = ':'.join(str(path) for path in dict.fromkeys(libraries))
        loader = work / 'ld'
        loader.symlink_to(resolve(spec['loader']))
        runtime_libraries = work / 'l'
        runtime_libraries.mkdir()
        bound_names = {}
        for directory in dict.fromkeys(libraries):
            for candidate in sorted(directory.glob('*.so*')):
                if not candidate.is_file():
                    continue
                with candidate.open('rb') as stream:
                    if stream.read(4) != b'\x7fELF':
                        continue
                info = elf_layout(candidate)
                for name in [candidate.name, info['soname']]:
                    if name and name not in bound_names:
                        (runtime_libraries / name).symlink_to(candidate)
                        bound_names[name] = str(candidate)
        execution_artifacts = []

        def program(source, destination, executable=True, runtime_copy=False):
            destination.parent.mkdir(parents=True, exist_ok=True)
            original = elf_execution_identity(resolve(source))
            if executable:
                # The current non-PIE ELF has room for these short strings.
                # Preserve its LOAD mappings and direct execve env/argv semantics.
                shutil.copyfile(resolve(source), destination)
                destination.chmod(0o755)
                subprocess.run([str(resolve(spec['patchelf'])), '--set-interpreter', str(loader),
                                '--force-rpath', '--set-rpath', str(runtime_libraries), str(destination)], check=True)
                if elf_execution_identity(destination) != original:
                    raise RuntimeError('runtime ELF copy changed allocated text/relocations/Build-ID')
                old, new = elf_layout(resolve(source)), elf_layout(destination)
                if old['PT_LOAD'] != new['PT_LOAD'] or old['NEEDED'] != new['NEEDED']:
                    raise RuntimeError('runtime ELF copy changed LOAD layout or NEEDED')
            elif runtime_copy:
                # CPython's original installation RUNPATH belongs to /usr.
                # A private execution copy uses the declared short library view.
                shutil.copyfile(resolve(source), destination)
                subprocess.run([str(resolve(spec['patchelf'])), '--force-rpath',
                                '--set-rpath', str(runtime_libraries), str(destination)], check=True)
                if elf_execution_identity(destination) != original:
                    raise RuntimeError('module runtime copy changed text/relocations/Build-ID')
                old, new = elf_layout(resolve(source)), elf_layout(destination)
                if old['PT_LOAD'] != new['PT_LOAD'] or old['NEEDED'] != new['NEEDED']:
                    raise RuntimeError('module runtime copy changed LOAD layout or NEEDED')
            else:
                destination.symlink_to(resolve(source))
            execution_artifacts.append({'input': source, 'execution_view': str(destination.relative_to(work)),
                                        'method': ('short-interpreter/RPATH direct ELF copy' if executable else 'short-RPATH module copy' if runtime_copy else 'declared artifact symlink'),
                                        'elf_text_relocations_build_id': original,
                                        'input_sha256': hashlib.sha256(resolve(source).read_bytes()).hexdigest()})
            return destination

        # The shared core is another source-built CPython ELF with the
        # original installation RUNPATH. Relocate only its execution copy;
        # dependency package and sealed provider bytes remain untouched.
        shared_core = runtime_libraries / 'libpython3.13.so.1.0'
        if shared_core.is_file() and elf_layout(shared_core)['search_paths']:
            original_core = shared_core.resolve()
            copied_core = program(str(original_core), work / 'libpython3.13.so.1.0', executable=False, runtime_copy=True)
            for alias, original_path in list(bound_names.items()):
                if Path(original_path).resolve() == original_core:
                    destination = runtime_libraries / alias
                    destination.unlink()
                    destination.symlink_to(copied_core)
                    bound_names[alias] = str(copied_core)

        python = program(spec['interpreter'], work / 'python')
        if spec['embed']:
            program(spec['embed'], work / 'Programs/_testembed')
        for name, filename in spec['modules'].items():
            program(filename, extensions / (name + '.cpython-313-x86_64-linux-gnu.so'), executable=False, runtime_copy=bool(elf_layout(resolve(filename))['search_paths']))
        # gcov-tool is executed with the selected GCC SDK's own declared host
        # loader/libraries, just as that SDK's compiler forwarding scripts do.
        gcc_metadata = resolve(spec['gcc_metadata'])
        gcc = json.loads(gcc_metadata.read_text())
        gcc_root = gcc_metadata.parent
        gcov = [str(gcc_root / gcc['loader']), '--inhibit-cache', '--library-path',
                ':'.join(str(gcc_root / p) for p in gcc['library_directories']), str(resolve(spec['gcov_tool']))]
        freezer_receipts = []
        for frozen in spec['freeze_profiles']:
            frozen = resolve(frozen)
            freezer_receipts.append({'input': str(frozen), 'counter_count': len(list(frozen.rglob('*.gcda')))})
            if not any(frozen.rglob('*.gcda')):
                continue
            if not any(profile.rglob('*.gcda')):
                shutil.copytree(frozen, profile, dirs_exist_ok=True)
            else:
                merged = work / 'merged-profile'
                shutil.rmtree(merged, ignore_errors=True)
                subprocess.run(gcov + ['merge', '-o', str(merged), str(profile), str(frozen)], check=True)
                shutil.rmtree(profile)
                shutil.move(merged, profile)
        trailer = next(line.split('>  ', 1)[1] for line in (work / 'debian/changelog').read_text().splitlines()
                       if line.startswith(' -- '))
        source_date_epoch = int(parsedate_to_datetime(trailer).timestamp()) + 86400
        environment = {
            'HOME': str(work / 'home'), 'TMPDIR': fixture_temporary, 'SOURCE_DATE_EPOCH': str(source_date_epoch), 'TZ': 'UTC',
            'PYTHONPATH': str(extensions) + ':' + str(work / 'Lib'),
            'GCOV_PREFIX': str(profile), 'GCOV_PREFIX_STRIP': '1',
            'OPENSSL_CONF': str(runtime / 'etc/ssl/openssl.cnf'),
            'OPENSSL_CONF_INCLUDE': str(runtime / 'etc/ssl'),
            'OPENSSL_MODULES': str(runtime / 'usr/lib/x86_64-linux-gnu/ossl-modules'),
            'OPENSSL_ENGINES': str(runtime / 'usr/lib/x86_64-linux-gnu/engines-3'),
            'PATH': ':'.join(str(resolve(p)) for p in spec['execution_path'].split(':')),
        }
        environment.update(spec.get('configure_environment', {}))
        environment.update({name: variables[name] for name in ('CC', 'CXX')})
        environment['CPP'] = shlex.quote(variables['CC']) + ' -E'
        test_data = {}
        if 'test_data_runtime' in spec:
            data_root = resolve(spec['test_data_runtime'])
            data_environment = declared_test_data(data_root)
            # Original Debian tests and ensurepip select wheels through this
            # sysconfig value. Only the owned build view is relocated.
            original_wheel_directory = variables.get('WHEEL_PKG_DIR')
            if original_wheel_directory:
                relative_wheels = Path(original_wheel_directory).relative_to('/')
                wheel_directory = data_root / relative_wheels
                if not wheel_directory.is_dir():
                    raise RuntimeError('Original wheel package directory missing from declared runtime: ' + str(wheel_directory))
                variables['WHEEL_PKG_DIR'] = str(wheel_directory)
            # The original datetime tests open /usr/share/zoneinfo directly.
            # Keep libc on that same execution-platform data unless the caller
            # explicitly selected another TZDIR. PYTHONTZPATH stays declared.
            if 'TZDIR' in os.environ:
                environment['TZDIR'] = os.environ['TZDIR']
            environment.setdefault('TZDIR', '/usr/share/zoneinfo')
            for key, value in data_environment.items():
                environment.setdefault(key, value)
            platform_timezone = {'root': environment['TZDIR'], 'input_contract': 'execution-platform FHS data; not a hermetic input'}
            if environment['TZDIR'] == '/usr/share/zoneinfo':
                timezone_files = {}
                for relative in ('tzdata.zi', 'Asia/Tehran'):
                    path = Path(environment['TZDIR']) / relative
                    if path.is_file():
                        timezone_files[relative] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                        if relative == 'tzdata.zi':
                            platform_timezone['version'] = path.read_text().splitlines()[0]
                platform_timezone['files'] = timezone_files
            test_data = {'runtime': spec['test_data_runtime'], 'environment': {key: environment[key] for key in data_environment},
                         'platform_timezone': platform_timezone,
                         'wheel_package_directory': {'original': original_wheel_directory, 'build_view': variables.get('WHEEL_PKG_DIR')},
                         'manifest_sha256': hashlib.sha256((data_root / 'toolchain.json').read_bytes()).hexdigest()}
        if spec.get('openssl_pkgconfig'):
            # Preserve the original public .pc metadata and GNU pkgconf query
            # behavior. CcInfo already supplies declared header/library searches.
            pc_directory = work / 'openssl-pkgconfig'
            pc_directory.mkdir()
            pc_projection = []
            bindings = {'-l' + name: '-l:' + Path(path).name
                        for name, path in spec['openssl_libraries'].items()}
            for original in spec['openssl_pkgconfig']:
                original_path = resolve(original)
                lines = []
                for line in original_path.read_text().splitlines():
                    if line.startswith(('Libs:', 'Libs.private:', 'Cflags:')):
                        key, flags = line.split(':', 1)
                        projected = []
                        omit = False
                        for word in shlex.split(flags):
                            if omit:
                                omit = False
                                continue
                            if word in ('-I', '-L', '-isystem', '-iquote', '-idirafter'):
                                omit = True
                                continue
                            if word.startswith(('-I', '-L', '-isystem', '-iquote', '-idirafter')):
                                continue
                            projected.append(bindings.get(word, word))
                        line = key + ': ' + ' '.join(projected)
                    lines.append(line)
                projected_path = pc_directory / original_path.name
                projected_path.write_text('\n'.join(lines) + '\n')
                pc_projection.append({'source': original, 'source_sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
                                      'projected_sha256': hashlib.sha256(projected_path.read_bytes()).hexdigest()})
            test_data['openssl_pkgconfig'] = {'files': pc_projection, 'library_bindings': spec['openssl_libraries'],
                                              'queries': ['--libs-only-L', '--libs-only-l', '--cflags-only-I']}
            environment.update(PKG_CONFIG=str(resolve(spec['pkgconf'])), PKG_CONFIG_LIBDIR=str(pc_directory),
                               PKG_CONFIG_PATH='', PKG_CONFIG_SYSROOT_DIR='')
        metadata.write_text('build_time_vars = ' + repr(variables) + '\n')
        Path(environment['HOME']).mkdir()
        baseline_counters = {str(p.relative_to(profile)): hashlib.sha256(p.read_bytes()).hexdigest() for p in profile.rglob('*.gcda')}
        commands = []
        fallback_profiles = []
        log = profile / 'workload.log'
        with log.open('w') as stream:
            if spec['workload'] == 'contextvars-smoke':
                command = [str(python), '-S', '-c', 'import _contextvars; v=_contextvars.ContextVar("profile"); v.set(7); assert _contextvars.copy_context()[v]==7']
                result = subprocess.run(command, cwd=work, env=environment, stdout=stream, stderr=subprocess.STDOUT)
                commands.append({'argv': command, 'returncode': result.returncode})
                if result.returncode:
                    raise RuntimeError('native profile smoke failed; see ' + str(log))
            else:
                excludes = original_excludes(work / 'debian/rules')
                command = [str(python), str(work / 'Lib/test/regrtest.py'), '-s', '-j', '1', '-unone,decimal', '-x'] + excludes
                next_file = build / 'pynexttest'
                previous = None
                while True:
                    selected = next_file.read_text() if next_file.exists() else None
                    result = subprocess.run(command, cwd=work, env=environment, stdout=stream, stderr=subprocess.STDOUT)
                    stream.flush()
                    commands.append({'argv': command, 'selected': selected, 'returncode': result.returncode})
                    if result.returncode < 0:
                        raise RuntimeError('profile interpreter terminated by signal ' + str(-result.returncode) + '; original test driver did not complete; see ' + str(log))
                    if selected is None and not next_file.exists() and result.returncode:
                        raise RuntimeError('profile test driver failed before starting the original single-test sequence; see ' + str(log))
                    fallback_profiles.extend(merge_fallback_profiles(work, profile, gcov))
                    fallback_profiles.extend(merge_fallback_profiles(Path(fixture_temporary), profile, gcov, "fixture_tmp"))
                    if not next_file.exists():
                        break
                    upcoming = next_file.read_text()
                    if upcoming == previous:
                        raise RuntimeError('original single-test driver stopped advancing: ' + upcoming)
                    previous = upcoming
                # Original profiled-build.diff tolerates test failures. Keep all
                # original selections and retain each result instead of adding skips.
        fallback_profiles.extend(merge_fallback_profiles(work, profile, gcov))
        fallback_profiles.extend(merge_fallback_profiles(Path(fixture_temporary), profile, gcov, "fixture_tmp"))
        counters = sorted(profile.rglob('*.gcda'))
        if not counters:
            raise RuntimeError('profile workload produced no GCC counter files')
        changed_counters = sum(baseline_counters.get(str(p.relative_to(profile))) != hashlib.sha256(p.read_bytes()).hexdigest() for p in counters)
        if not changed_counters:
            raise RuntimeError('original workload changed no GCC counters; freezer data alone is not training')
        result = {
            'workload': spec['workload'], 'commands': commands, 'counter_count': len(counters),
            'profiles': [{'path': str(p.relative_to(profile)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in counters],
            'runtime_loader': spec['loader'], 'gcc_metadata': spec['gcc_metadata'],
            'source_date_epoch': source_date_epoch, 'freezer_profiles': freezer_receipts, 'test_data': test_data,
            'counters_changed_by_workload': changed_counters, 'fallback_profiles': fallback_profiles,
            'normal_profile_source': 'GCOV_PREFIX declared output tree; GCOV_PREFIX_STRIP=1 removes only initial dot',
            'execution_artifacts': execution_artifacts, 'source_view': 'individual symlinks to declared source artifacts',
            'product_elf_inputs': 'unchanged', 'regular_fixtures': regular_fixtures,
            'private_tmp_layout': {'source_view': str(work), 'fixture_tmp': fixture_temporary}, 'runtime_library_bindings': bound_names, 'sealed_symcrypt': sealed_inputs,
        }
        report.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    if sys.argv[1] == 'freeze':
        freeze(sys.argv[2:])
    elif sys.argv[1] == 'profile':
        main(*sys.argv[2:])
    else:
        raise SystemExit('unknown CPython profile action')
