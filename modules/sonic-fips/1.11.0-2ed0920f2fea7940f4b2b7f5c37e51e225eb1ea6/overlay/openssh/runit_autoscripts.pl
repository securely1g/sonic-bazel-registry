# Component-specific original dh_runit autoscripts and substitution producers.
BEGIN { $0 = 'dh_runit'; }
use strict;
use warnings;
use Debian::Debhelper::Dh_Lib;
our $VERSION;
my $source = shift @ARGV;
open(my $helper, '<', "$source/dh_runit") or die $!;
my $original;
{ local $/; $original = <$helper>; }
($VERSION) = $original =~ /our \$VERSION = "([^"]+)"/;
die "Missing original dh_runit version" unless defined $VERSION;
$ENV{DH_AUTOSCRIPTDIR} = $source;
init();
my $substitutions = { NAME => 'ssh', ENABLE => 'yes', ONUPGRADE => 'restart' };
for my $script ('postinst', 'prerm', 'postrm') {
    autoscript('openssh-server', $script, "$script-runit", $substitutions);
}
addsubstvar('openssh-server', 'runit:Conflicts', 'runit', '<< 2.1.2-51~');
addsubstvar('openssh-server', 'runit:Breaks', 'runit', '<< 2.1.2-51~');
addsubstvar('openssh-server', 'misc:Depends', 'runit-helper', '>= 2.14.0~');
