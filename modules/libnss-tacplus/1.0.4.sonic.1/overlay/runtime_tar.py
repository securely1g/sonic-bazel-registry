"""Apply the original NSS install hook using declared target libc paths."""
import io
from pathlib import Path
import re
import sys
import tarfile
elf, libc, config, copyright, output, *docs = sys.argv[1:]
with tarfile.open(libc) as archive:
    names=[member.name.removeprefix('./') for member in archive]
    versions=sorted({match.group(1) for name in names if (match:=re.fullmatch(r'(?:usr/)?lib/x86_64-linux-gnu/libc-(.*)\.so',name))})
    nss=sorted({match.group(1) for name in names if (match:=re.fullmatch(r'(?:usr/)?lib/x86_64-linux-gnu/libnss_files\.so\.(.)',name))})
if len(versions)>1 or len(nss)!=1:raise ValueError('ambiguous original libc/NSS installation identity: '+repr((versions,nss)))
filename='libnss_tacplus-'+(''.join(versions))+'.so'
with tarfile.open(output,'w',format=tarfile.GNU_FORMAT) as archive:
    for name,source,mode in [('lib/x86_64-linux-gnu/'+filename,elf,0o755),('etc/tacplus_nss.conf',config,0o644),('usr/share/doc/libnss-tacplus/copyright',copyright,0o644)] + [(name, source, 0o644) for name, source in zip(docs[::2], docs[1::2])]:
        data=Path(source).read_bytes();member=tarfile.TarInfo(name);member.mode=mode;member.size=len(data);archive.addfile(member,io.BytesIO(data))
    link=tarfile.TarInfo('lib/x86_64-linux-gnu/libnss_tacplus.so.'+nss[0]);link.type=tarfile.SYMTYPE;link.linkname=filename;link.mode=0o777;archive.addfile(link)
