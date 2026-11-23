"""Original CPython Debian metadata policy on public runtime_packages primitives."""
from pathlib import Path
import argparse,json,re,shutil,tempfile
from debian.deb822 import Deb822
from runtime_packages import (generate, paragraphs, DebianTools, dependency_records,
    library_directories, extract, sha, INSTALLED_FIELDS)

SYMBOL_FILTERS = [r'/^ (PyInit_|_add_one_to_index|asdl_)/d',
                  r'/^ (PyExpat_XML_|PyExpat_Xml)/d', r'/^ (ffi_type_|_ctypes_)/d']

def source_control(source, binary, original):
    fields={key:value for key,value in binary.items() if key not in INSTALLED_FIELDS | {'Version','Source'}}
    fields['Architecture']=original['Architecture']
    for key in original:
        extension = re.fullmatch(r'X([BCS]+)-(.+)', key)
        if extension and 'B' in extension[1] and extension[2] in fields:
            fields[key] = fields.pop(extension[2])
    return Deb822(source).dump()+'\n'+Deb822(fields).dump()

def main(specpath):
    spec=json.loads(Path(specpath).read_text());root=Path.cwd();path=lambda p:(root/p).absolute()
    packages={name:(row['label'],path(row['tar'])) for name,row in spec['packages'].items()}
    apt=[(path(row[0]),path(row[1])) for row in spec['apt']]
    dependencies=[path(p) for p in spec['dependencies']]
    files={key:path(value) for key,value in spec['debian_files'].items()}
    symbols={key:path(value) for key,value in spec['symbols'].items()}
    common=dict(tar=path(spec['tar']),tools=path(spec['tools']),control=path(spec['control']),
                changelog=path(spec['changelog']),module='sonic-fips',architecture=spec['architecture'],
                packages=packages,dependencies=dependencies,apt_packages=apt,symbols=symbols,
                debian_files=files)
    receipt={'policy_source':'original debian/rules binary-arch','source_rules_sha256':sha(path(spec['rules'])),'symbols_filters':SYMBOL_FILTERS}
    if spec['mode']=='controls':
        with tempfile.TemporaryDirectory(prefix='python-original-controls-') as temporary:
            scratch=Path(temporary);prep=scratch/'prepared';meta=scratch/'prepared.json'
            # This public call validates the real payload ELF/ABI/architecture and
            # prepares the selected APT/source provider metadata. It does not
            # calculate dependencies; the original helpers below own that step.
            generate(tree=prep,output=meta,shlibdeps=False,**common)
            work=scratch/'original';(work/'debian').mkdir(parents=True)
            source,*stanzas=paragraphs(path(spec['control']));selected=[row for row in stanzas if row['Package'] in packages]
            (work/'debian/control').write_text('\n'.join(Deb822(row).dump() for row in [source,*selected]))
            shutil.copyfile(path(spec['changelog']),work/'debian/changelog')
            for name,file in files.items():
                destination=work/'debian'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,destination)
            for package,(_,payload) in packages.items():extract(payload,work/'debian'/package,path(spec['tar']))
            dpkg=DebianTools(path(spec['tools']),work,spec['architecture'])
            # Preserve original ordering: makeshlibs, exactly three sed filters,
            # installdeb, shlibdeps, libc6 split, gencontrol.
            dpkg.run('dh_makeshlibs','-plibpython3.13','-V','libpython3.13')
            symbolfile=work/'debian/libpython3.13/DEBIAN/symbols'
            dpkg.run('sed','-ri',*[argument for expression in SYMBOL_FILTERS for argument in ['-e',expression]],symbolfile)
            dpkg.run('dh_installdeb','-a')
            roots=[work/'debian'/name for name in packages]
            roots += [prep/item['root'] for item in json.loads((prep/'manifest.json').read_text())['packages'] if item['kind']=='apt']
            roots += [record['root'] for record in dependency_records(dependencies,spec['architecture'])]
            allowed=set(roots)
            for directory in library_directories(roots):
                allowed.add(directory)
                for file in directory.glob('*.so*'):
                    if file.is_file():allowed.add(file.resolve().parent)
            dpkg.environment['SONIC_DPKG_TARGET_ROOTS']='\n'.join(map(str,sorted(allowed)))
            search=['-S'+str(p) for p in roots]+['-l'+str(p) for p in library_directories(roots)]
            dpkg.run('dh_shlibdeps','-a','--','--admindir='+dpkg.environment['DPKG_ADMINDIR'],*search)
            variables=work/'debian/python3.13-minimal.substvars';text=variables.read_text();match=re.search(r'^shlibs:Depends=(.*)$',text,re.M)
            if not match:raise ValueError('original minimal dh_shlibdeps output absent')
            dependencies_list=match[1].split(', ');libc=[entry for entry in dependencies_list if entry.startswith('libc6')]
            text=re.sub(r'^shlibs:Depends=.*$', 'shlibs:Depends='+', '.join(entry for entry in dependencies_list if not entry.startswith('libc6')),text,flags=re.M)
            text+='shlibs:Pre-Depends='+', '.join(libc)+'\n';variables.write_text(text)
            # Original dh_shlibdeps does not emit a substitution for a package
            # with no ELF. Original dpkg-gencontrol expands that absence to the
            # empty string (with a warning). Preserve its exact control output,
            # while retaining the shared tool's strict warning policy.
            scanned = json.loads(meta.read_text())['packages']
            receipt['empty_shlibs_substitutions'] = []
            for row in selected:
                name = row['Package']
                if '${shlibs:Depends}' not in '\n'.join(row.values()):
                    continue
                if 'elf_needed' not in scanned[name]:
                    raise ValueError('shared ELF scan result absent: ' + name)
                if scanned[name]['elf_needed']:
                    continue
                variable = work / 'debian' / (name + '.substvars')
                contents = variable.read_text() if variable.exists() else ''
                if not re.search(r'^shlibs:Depends=', contents, re.M):
                    variable.write_text(contents.rstrip('\n') + '\nshlibs:Depends=\n')
                    receipt['empty_shlibs_substitutions'].append({'package': name, 'shared_elf_count': 0})
            dpkg.run('dh_gencontrol','-a')
            receipt['minimal_libc_predepends']=libc;receipt['controls']={}
            for package in packages:
                original=work/'debian'/package/'DEBIAN/control';binary,=paragraphs(original)
                output=path(spec['source_outputs'][package]);output.write_text(source_control(source,binary,next(row for row in selected if row['Package']==package)))
                path(spec['binary_outputs'][package]).write_bytes(original.read_bytes())
                receipt['controls'][package]={'original_dpkg_gencontrol_sha256':sha(original),'fields':binary}
    else:
        tree=path(spec['tree']);output=path(spec['output']);helpers=[['dh_installdeb']]
        if 'libpython3.13' in packages:helpers=[['dh_makeshlibs','-V','libpython3.13'],['dh_installdeb']]
        expected, = paragraphs(path(spec['expected_control']))
        # The original helper sizes the original staged package after its
        # symbols filters. The shared engine adds its identity control and
        # sizes before the component's postfilter. Reuse the original helper's
        # actual Installed-Size through its public Debian substvars input.
        original_size = expected['Installed-Size']
        if not re.fullmatch(r'[0-9]+', original_size):
            raise ValueError('invalid original dpkg Installed-Size')
        with tempfile.TemporaryDirectory(prefix='python-original-size-') as temporary:
            variable = Path(temporary) / 'original.substvars'
            variable.write_text('Installed-Size=' + original_size + '\n')
            generate(tree=tree,output=output,shlibdeps=False,control_file_helpers=helpers,
                     substvars={package: variable for package in packages},**common)
        receipt['original_installed_size'] = original_size
        document=json.loads(output.read_text());manifest=json.loads((tree/'manifest.json').read_text())
        dpkg=DebianTools(path(spec['tools']),Path(tempfile.mkdtemp(prefix='python-symbol-policy-')),spec['architecture'])
        for package in packages:
            base=tree/'packages'/package
            if package=='libpython3.13':
                symbolfile=base/'DEBIAN/symbols';dpkg.run('sed','-ri',*[a for expression in SYMBOL_FILTERS for a in ['-e',expression]],symbolfile)
                document['packages'][package]['control_files']['symbols']['sha256']=sha(symbolfile)
            expected,=paragraphs(path(spec['expected_control']));actual,=paragraphs(base/'DEBIAN/control')
            if dict(expected)!=dict(actual):raise ValueError('final metadata control differs from original dpkg-gencontrol: '+package)
            receipt['control_fields']=actual
        document['_generated']['component_postprocessing']='original CPython symbols filter; verified original dpkg-gencontrol fields'
        output.write_text(json.dumps(document,sort_keys=True,indent=2)+'\n')
        shutil.rmtree(dpkg.scratch)
    path(spec['receipt']).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')

if __name__=='__main__':main(__import__('sys').argv[1])
