package configdata;
use Exporter;
our @ISA = qw(Exporter);
our @EXPORT = qw(%config %target %disabled %unified_info);
our %config = ('target'=>'debian-arm64','FIPSKEY'=>'f4556650ac31d35461610bac4ed81b1a181b2d8a43ea2854cbae22ca74560813','options'=>'enable-shared --prefix=/usr --openssldir=/usr/lib/ssl --libdir=lib/aarch64-linux-gnu enable-unit-test enable-rfc3779 enable-cms enable-tfo enable-zstd enable-zlib enable-fips enable-ec_nistp_64_gcc_128 no-asan no-brotli no-brotli-dynamic no-buildtest-c++ no-capieng no-crypto-mdebug no-crypto-mdebug-backtrace no-demos no-devcryptoeng no-egd no-external-tests no-fips-jitter no-fuzz-afl no-fuzz-libfuzzer no-h3demo no-heartbeats no-hqinterop no-idea no-jitter no-md2 no-mdc2 no-msan no-padlockeng no-pie no-rc5 no-rdrand no-sctp no-ssl3 no-ssl3-method no-sslkeylog no-trace no-ubsan no-uplink no-weak-ssl-ciphers no-winstore no-zlib-dynamic no-zstd-dynamic','shlib_version'=>'3');
$config{sourcedir} = $ENV{OPENSSL_SOURCE_ROOT};
$config{builddir} = $ENV{OPENSSL_CONFIG_ROOT};
our %target = ('perl_platform'=>'Unix','dso_scheme'=>'dlfcn','shared_target'=>'linux-shared');
our %disabled = ('asan'=>'default','brotli'=>'default','brotli-dynamic'=>'default','buildtest-c++'=>'default','capieng'=>'option','crypto-mdebug'=>'default','crypto-mdebug-backtrace'=>'default','demos'=>'default','devcryptoeng'=>'default','egd'=>'default','external-tests'=>'default','fips-jitter'=>'default','fuzz-afl'=>'default','fuzz-libfuzzer'=>'default','h3demo'=>'default','heartbeats'=>'cascade','hqinterop'=>'default','idea'=>'option','jitter'=>'default','md2'=>'default','mdc2'=>'option','msan'=>'default','padlockeng'=>'option','pie'=>'default','rc5'=>'option','rdrand'=>'option','sctp'=>'default','ssl3'=>'option(ssl3-method)','ssl3-method'=>'option','sslkeylog'=>'default','trace'=>'default','ubsan'=>'default','uplink'=>'no uplink_arch','weak-ssl-ciphers'=>'default','winstore'=>'not-windows','zlib-dynamic'=>'default','zstd-dynamic'=>'default');
our %unified_info = ();
our %available_protocols = (
    tls  => [
    "ssl3",
    "tls1",
    "tls1_1",
    "tls1_2",
    "tls1_3"
],
    dtls => [
    "dtls1",
    "dtls1_2"
],);
1;
