"""Run original ParseXS with declared input and stable logical line filenames."""
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile

perl, source, output, logical_output, prototypes, *inputs = sys.argv[1:]
source_name = PurePosixPath(source)
if source_name.is_absolute() or '..' in source_name.parts:
    raise ValueError('XS source must be a declared execution-root-relative path')
perl = str(Path(perl).absolute())
output = str(Path(output).absolute())
source_input = Path(source).absolute()
extra_inputs = [Path(name).absolute() for name in inputs]
with tempfile.TemporaryDirectory(prefix='netsnmp-xs-') as directory:
    work = Path(directory)
    staged_source = work / source
    staged_source.parent.mkdir(parents=True, exist_ok=True)
    staged_source.symlink_to(source_input)
    for path in extra_inputs:
        (staged_source.parent / path.name).symlink_to(path)
    # ParseXS keeps filename for XS #line entries and outfile for C #line
    # entries. A handle prevents it replacing outfile with the writable path.
    program = r'''
use File::Basename qw(dirname);
my ($source,$output,$logical_output,$prototypes)=@ARGV;
open my $handle, '>', $output or die "Cannot create output: $!";
my %options=(filename=>$source, output=>$handle, outfile=>$logical_output,
             prototypes=>$prototypes);
$options{typemap}=["typemap"] if -f dirname($source)."/typemap";
ExtUtils::ParseXS::process_file(%options);
close $handle or die "Cannot close output: $!";
'''
    subprocess.run([perl, '-MExtUtils::ParseXS', '-e', program, source,
                    output, logical_output, prototypes], cwd=work, check=True)
