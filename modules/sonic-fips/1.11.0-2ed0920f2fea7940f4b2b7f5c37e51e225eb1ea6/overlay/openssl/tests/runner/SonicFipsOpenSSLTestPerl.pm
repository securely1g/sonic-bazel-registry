package SonicFipsOpenSSLTestPerl;
use strict;
use warnings;
INIT {
    # The managed runtime first selects its hermetic Perl. TAP then uses $^X.
    $^X = $ENV{OPENSSL_SUITE_PERL} // die "OPENSSL_SUITE_PERL is required";
}
1;
