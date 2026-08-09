#ifndef GENERIC_CHESS_NATIVE_SHA256_H
#define GENERIC_CHESS_NATIVE_SHA256_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t state[8];
    uint64_t bit_count;
    uint8_t block[64];
    size_t block_len;
} GCSha256;

void gc_sha256_init(GCSha256 *ctx);
void gc_sha256_update(GCSha256 *ctx, const uint8_t *data, size_t len);
void gc_sha256_final(GCSha256 *ctx, uint8_t digest[32]);
void gc_sha256_hex(const uint8_t digest[32], char out[65]);

#endif
