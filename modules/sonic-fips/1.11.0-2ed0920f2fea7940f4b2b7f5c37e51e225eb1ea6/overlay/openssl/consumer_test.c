/* Public EVP and TLS interface consumer. SHA-256 vector: FIPS 180-4, "abc". */
#include <openssl/evp.h>
#include <openssl/ssl.h>
#include <string.h>

int main(void)
{
    static const unsigned char expected[32] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int size = 0;
    SSL_CTX *context;

    if (EVP_Digest("abc", 3, digest, &size, EVP_sha256(), NULL) != 1)
        return 1;
    if (size != sizeof(expected) || memcmp(digest, expected, sizeof(expected)))
        return 2;
    context = SSL_CTX_new(TLS_method());
    if (context == NULL)
        return 3;
    SSL_CTX_free(context);
    return 0;
}
