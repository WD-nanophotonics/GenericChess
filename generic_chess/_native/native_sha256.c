#include "native_sha256.h"

#include <string.h>

static uint32_t rotr32(uint32_t x, uint32_t n) { return (x >> n) | (x << (32 - n)); }
static uint32_t ch(uint32_t x, uint32_t y, uint32_t z) { return (x & y) ^ (~x & z); }
static uint32_t maj(uint32_t x, uint32_t y, uint32_t z) { return (x & y) ^ (x & z) ^ (y & z); }
static uint32_t bs0(uint32_t x) { return rotr32(x, 2) ^ rotr32(x, 13) ^ rotr32(x, 22); }
static uint32_t bs1(uint32_t x) { return rotr32(x, 6) ^ rotr32(x, 11) ^ rotr32(x, 25); }
static uint32_t ss0(uint32_t x) { return rotr32(x, 7) ^ rotr32(x, 18) ^ (x >> 3); }
static uint32_t ss1(uint32_t x) { return rotr32(x, 17) ^ rotr32(x, 19) ^ (x >> 10); }

static const uint32_t K[64] = {
    0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
    0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
    0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
    0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
    0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
    0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
    0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
    0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
};

static void transform(GCSha256 *ctx, const uint8_t block[64]) {
    uint32_t w[64], a,b,c,d,e,f,g,h;
    for (int i=0;i<16;i++) w[i]=(uint32_t)block[i*4]<<24 | (uint32_t)block[i*4+1]<<16 | (uint32_t)block[i*4+2]<<8 | block[i*4+3];
    for (int i=16;i<64;i++) w[i]=ss1(w[i-2])+w[i-7]+ss0(w[i-15])+w[i-16];
    a=ctx->state[0];b=ctx->state[1];c=ctx->state[2];d=ctx->state[3];e=ctx->state[4];f=ctx->state[5];g=ctx->state[6];h=ctx->state[7];
    for (int i=0;i<64;i++) { uint32_t t1=h+bs1(e)+ch(e,f,g)+K[i]+w[i], t2=bs0(a)+maj(a,b,c); h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2; }
    ctx->state[0]+=a;ctx->state[1]+=b;ctx->state[2]+=c;ctx->state[3]+=d;ctx->state[4]+=e;ctx->state[5]+=f;ctx->state[6]+=g;ctx->state[7]+=h;
}

void gc_sha256_init(GCSha256 *ctx) {
    static const uint32_t initial[8]={0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u};
    memcpy(ctx->state,initial,sizeof(initial)); ctx->bit_count=0; ctx->block_len=0;
}
void gc_sha256_update(GCSha256 *ctx, const uint8_t *data, size_t len) {
    ctx->bit_count += (uint64_t)len * 8;
    while (len) { size_t take=64-ctx->block_len; if (take>len) take=len; memcpy(ctx->block+ctx->block_len,data,take); ctx->block_len+=take; data+=take; len-=take; if (ctx->block_len==64) { transform(ctx,ctx->block); ctx->block_len=0; } }
}
void gc_sha256_final(GCSha256 *ctx, uint8_t digest[32]) {
    uint64_t bits=ctx->bit_count; uint8_t pad=0x80; gc_sha256_update(ctx,&pad,1); uint8_t zero=0;
    while (ctx->block_len != 56) gc_sha256_update(ctx,&zero,1);
    uint8_t lenbuf[8]; for (int i=0;i<8;i++) lenbuf[7-i]=(uint8_t)(bits>>(i*8)); gc_sha256_update(ctx,lenbuf,8);
    for (int i=0;i<8;i++) for (int j=0;j<4;j++) digest[i*4+j]=(uint8_t)(ctx->state[i]>>(24-j*8));
}
void gc_sha256_hex(const uint8_t digest[32], char out[65]) { static const char h[]="0123456789abcdef"; for (int i=0;i<32;i++){out[i*2]=h[digest[i]>>4];out[i*2+1]=h[digest[i]&15];} out[64]='\0'; }
