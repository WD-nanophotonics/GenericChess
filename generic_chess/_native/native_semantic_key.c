#include "native_semantic_key.h"
#include "native_sha256.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { char *data; size_t len, cap; int ok; } GCSemBuf;
static void sb_init(GCSemBuf *b) { b->data=NULL; b->len=0; b->cap=0; b->ok=1; }
static void sb_reserve(GCSemBuf *b, size_t add) {
    if (!b->ok || add > (size_t)-1 - b->len) { b->ok=0; return; }
    size_t need=b->len+add+1; if (need<=b->cap) return;
    size_t cap=b->cap ? b->cap*2 : 256; while (cap<need) { if (cap>(size_t)-1/2) {cap=need;break;} cap*=2; }
    char *p=(char*)realloc(b->data,cap); if (!p) {b->ok=0;return;} b->data=p;b->cap=cap;
}
static void sb_raw(GCSemBuf *b, const char *s, size_t n) { sb_reserve(b,n); if (!b->ok)return; memcpy(b->data+b->len,s,n); b->len+=n;b->data[b->len]='\0'; }
static void sb_lit(GCSemBuf *b, const char *s) { sb_raw(b,s,strlen(s)); }
static void sb_u64(GCSemBuf *b, uint64_t v) { char x[32]; int n=snprintf(x,sizeof(x),"%llu",(unsigned long long)v); if(n<0){b->ok=0;return;} sb_raw(b,x,(size_t)n); }
static void sb_i64(GCSemBuf *b, int64_t v) { char x[32]; int n=snprintf(x,sizeof(x),"%lld",(long long)v); if(n<0){b->ok=0;return;} sb_raw(b,x,(size_t)n); }
static void sb_json_u16_escape(GCSemBuf *b, uint32_t value) {
    char x[7];
    snprintf(x, sizeof(x), "\\u%04x", (unsigned)(value & 0xffffu));
    sb_lit(b, x);
}
static void sb_json_string(GCSemBuf *b, const char *s) {
    sb_lit(b,"\"");
    const unsigned char *p=(const unsigned char*)s;
    while (*p && b->ok) {
        unsigned char c=*p++;
        if (c=='\"') sb_lit(b,"\\\"");
        else if (c=='\\') sb_lit(b,"\\\\");
        else if (c=='\b') sb_lit(b,"\\b");
        else if (c=='\f') sb_lit(b,"\\f");
        else if (c=='\n') sb_lit(b,"\\n");
        else if (c=='\r') sb_lit(b,"\\r");
        else if (c=='\t') sb_lit(b,"\\t");
        else if (c<0x20) sb_json_u16_escape(b,c);
        else if (c<0x80) sb_raw(b,(const char*)&c,1);
        else {
            uint32_t cp = 0; int needed = 0;
            if ((c & 0xe0u) == 0xc0u) { cp = c & 0x1fu; needed = 1; }
            else if ((c & 0xf0u) == 0xe0u) { cp = c & 0x0fu; needed = 2; }
            else if ((c & 0xf8u) == 0xf0u) { cp = c & 0x07u; needed = 3; }
            else { b->ok=0; continue; }
            for (int i=0; i<needed; i++) {
                unsigned char tail = *p++;
                if ((tail & 0xc0u) != 0x80u) { b->ok=0; break; }
                cp = (cp << 6) | (tail & 0x3fu);
            }
            if (!b->ok) continue;
            if ((needed == 1 && cp < 0x80u) ||
                (needed == 2 && cp < 0x800u) ||
                (needed == 3 && cp < 0x10000u) || cp > 0x10ffffu ||
                (cp >= 0xd800u && cp <= 0xdfffu)) { b->ok=0; continue; }
            if (cp <= 0xffffu) sb_json_u16_escape(b, cp);
            else {
                cp -= 0x10000u;
                sb_json_u16_escape(b, 0xd800u | (cp >> 10));
                sb_json_u16_escape(b, 0xdc00u | (cp & 0x3ffu));
            }
        }
    }
    sb_lit(b,"\"");
}
static int cmp_type(const GCSemanticRules *r, uint16_t a, uint16_t c) { return strcmp(r->type_ids[a],r->type_ids[c]); }
static void sorted_types(const GCSemanticRules *r, uint16_t *out) { for(uint16_t i=0;i<r->type_count;i++)out[i]=i; for(uint16_t i=1;i<r->type_count;i++){uint16_t x=out[i],j=i;while(j&&cmp_type(r,out[j-1],x)>0){out[j]=out[j-1];j--;}out[j]=x;} }
static void sorted_slots(const GCSemanticRules *r, uint8_t *out) { for(uint8_t i=0;i<r->aux_slot_count;i++)out[i]=i; for(uint8_t i=1;i<r->aux_slot_count;i++){uint8_t x=out[i],j=i;while(j&&r->aux_slots[out[j-1]].slot_id>r->aux_slots[x].slot_id){out[j]=out[j-1];j--;}out[j]=x;} }

typedef struct { GCSha256 sha; uint8_t buffer[1024]; size_t length; int ok; } GCSemStream;
static void ss_init(GCSemStream *s) { gc_sha256_init(&s->sha); s->length = 0; s->ok = 1; }
static void ss_raw(GCSemStream *s, const char *data, size_t length) {
    if (!s->ok) return;
    while (length > 0) {
        size_t available = sizeof(s->buffer) - s->length;
        size_t take = available < length ? available : length;
        memcpy(s->buffer + s->length, data, take);
        s->length += take; data += take; length -= take;
        if (s->length == sizeof(s->buffer)) {
            gc_sha256_update(&s->sha, s->buffer, s->length);
            s->length = 0;
        }
    }
}
static void ss_lit(GCSemStream *s, const char *text) { ss_raw(s, text, strlen(text)); }
static void ss_u64(GCSemStream *s, uint64_t value) {
    char buf[24]; size_t end = sizeof(buf);
    do { buf[--end] = (char)('0' + (value % 10)); value /= 10; } while (value != 0);
    ss_raw(s, buf + end, sizeof(buf) - end);
}
static void ss_i64(GCSemStream *s, int64_t value) {
    if (value < 0) { ss_lit(s, "-"); ss_u64(s, (uint64_t)(-(value + 1)) + 1); }
    else ss_u64(s, (uint64_t)value);
}
static void ss_json_u16_escape(GCSemStream *s, uint32_t value) { char buf[7]; snprintf(buf, sizeof(buf), "\\u%04x", (unsigned)(value & 0xffffu)); ss_lit(s, buf); }
static void ss_json_string(GCSemStream *s, const char *text) {
    if (text == NULL) { s->ok = 0; return; }
    ss_lit(s, "\"");
    const unsigned char *p = (const unsigned char *)text;
    while (*p && s->ok) {
        unsigned char c = *p++;
        if (c == '\"') ss_lit(s, "\\\"");
        else if (c == '\\') ss_lit(s, "\\\\");
        else if (c == '\b') ss_lit(s, "\\b");
        else if (c == '\f') ss_lit(s, "\\f");
        else if (c == '\n') ss_lit(s, "\\n");
        else if (c == '\r') ss_lit(s, "\\r");
        else if (c == '\t') ss_lit(s, "\\t");
        else if (c < 0x20) ss_json_u16_escape(s, c);
        else if (c < 0x80) ss_raw(s, (const char *)&c, 1);
        else {
            uint32_t cp = 0; int needed = 0;
            if ((c & 0xe0u) == 0xc0u) { cp = c & 0x1fu; needed = 1; }
            else if ((c & 0xf0u) == 0xe0u) { cp = c & 0x0fu; needed = 2; }
            else if ((c & 0xf8u) == 0xf0u) { cp = c & 0x07u; needed = 3; }
            else { s->ok = 0; continue; }
            for (int i = 0; i < needed; i++) {
                unsigned char tail = *p++;
                if ((tail & 0xc0u) != 0x80u) { s->ok = 0; break; }
                cp = (cp << 6) | (tail & 0x3fu);
            }
            if (!s->ok) continue;
            if ((needed == 1 && cp < 0x80u) || (needed == 2 && cp < 0x800u) ||
                (needed == 3 && cp < 0x10000u) || cp > 0x10ffffu ||
                (cp >= 0xd800u && cp <= 0xdfffu)) { s->ok = 0; continue; }
            if (cp <= 0xffffu) ss_json_u16_escape(s, cp);
            else { cp -= 0x10000u; ss_json_u16_escape(s, 0xd800u | (cp >> 10)); ss_json_u16_escape(s, 0xdc00u | (cp & 0x3ffu)); }
        }
    }
    ss_lit(s, "\"");
}
static void ss_type_string(GCSemStream *s, const GCSemanticRules *r, uint16_t index) {
    if (index >= r->type_count || !r->type_ids[index]) { s->ok = 0; return; }
    if (r->canonical_type_simple[index]) {
        ss_raw(s, "\"", 1);
        ss_raw(s, r->type_ids[index], r->canonical_type_lengths[index]);
        ss_raw(s, "\"", 1);
    } else ss_json_string(s, r->type_ids[index]);
}

int gc_semantic_position_key_digest_raw(const GCSemanticRules *r,
                                        const GCSemanticPosition *p,
                                        uint8_t digest[32]) {
    if (!r || !p || !digest || !r->type_ids || !r->canonical_order_ready ||
        r->type_count > GC_MAX_TYPES || r->aux_slot_count > GC_SEM_MAX_AUX_SLOTS) return 0;
    GCSemStream s; ss_init(&s);
    ss_lit(&s, "{\"aux_state\":{");
    int first = 1;
    for (uint8_t si = 0; si < r->aux_slot_count; si++) {
        uint8_t slot_index = r->canonical_aux_indices[si];
        const GCSemAuxSlot *slot = &r->aux_slots[slot_index];
        uint8_t first_i = slot->scope == 1 ? 1 : 0, last_i = slot->scope == 1 ? 2 : 0;
        for (uint8_t i = first_i; i <= last_i; i++) {
            if (!first) ss_lit(&s, ","); first = 0;
            char key[64]; int owner = slot->scope == 1 ? (int)i - 1 : -1;
            snprintf(key, sizeof(key), "%u:%d", (unsigned)slot->slot_id, owner);
            ss_json_string(&s, key); ss_lit(&s, ":");
            const GCSemAuxValue *value = &p->aux[slot_index][i];
            if (!value->has_value) ss_lit(&s, "null");
            else if (value->kind == 0) ss_i64(&s, value->bool_value);
            else { ss_lit(&s, "["); ss_u64(&s, value->square % r->board_size); ss_lit(&s, ","); ss_u64(&s, value->square / r->board_size); ss_lit(&s, "]"); }
        }
    }
    ss_lit(&s, "},\"board\":[");
    for (uint16_t sq = 0; sq < (uint16_t)(r->board_size * r->board_size); sq++) {
        if (sq) ss_lit(&s, ",");
        const GCPiece *piece = &p->board[sq];
        if (!piece->occupied) ss_lit(&s, "null");
        else {
            if (piece->base_type >= r->type_count || piece->current_type >= r->type_count) { s.ok = 0; break; }
            ss_lit(&s, "["); ss_i64(&s, piece->owner); ss_lit(&s, ","); ss_type_string(&s, r, piece->base_type);
            ss_lit(&s, ","); ss_type_string(&s, r, piece->current_type); ss_lit(&s, ",");
            ss_lit(&s, piece->promoted ? "true" : "false"); ss_lit(&s, "]");
        }
    }
    ss_lit(&s, "],\"hands\":[[[");
    for (uint8_t owner = 0; owner < 2; owner++) {
        if (owner) ss_lit(&s, "],[");
        int first_hand = 1;
        for (uint16_t ti = 0; ti < r->type_count; ti++) {
            uint16_t type_index = r->canonical_type_indices[ti];
            uint16_t count = p->hand_counts[owner][type_index];
            if (!count) continue;
            if (!first_hand) ss_lit(&s, ","); first_hand = 0;
            ss_lit(&s, "["); ss_type_string(&s, r, type_index); ss_lit(&s, ","); ss_u64(&s, count); ss_lit(&s, "]");
        }
    }
    ss_lit(&s, "]]],\"ruleset\":"); ss_json_string(&s, r->fingerprint); ss_lit(&s, ",\"side_to_move\":"); ss_u64(&s, p->side_to_move); ss_lit(&s, "}");
    if (!s.ok) return 0;
    if (s.length > 0) gc_sha256_update(&s.sha, s.buffer, s.length);
    gc_sha256_final(&s.sha, digest);
    return 1;
}

int gc_semantic_position_key_digest(const GCSemanticRules *r, const GCSemanticPosition *p, char out_hex[65]) {
    if (!r || !p || !out_hex || !r->type_ids || r->type_count>GC_MAX_TYPES || r->aux_slot_count>GC_SEM_MAX_AUX_SLOTS) return 0;
    uint16_t types[GC_MAX_TYPES]; uint8_t slots[GC_SEM_MAX_AUX_SLOTS]; sorted_types(r,types); sorted_slots(r,slots);
    GCSemBuf b; sb_init(&b);
    sb_lit(&b,"{\"aux_state\":{");
    int first=1;
    for(uint8_t si=0;si<r->aux_slot_count;si++) { const GCSemAuxSlot *s=&r->aux_slots[slots[si]]; uint8_t first_i=s->scope==1?1:0,last_i=s->scope==1?2:0; for(uint8_t i=first_i;i<=last_i;i++) {
        if(!first)sb_lit(&b,","); first=0; char key[64]; int owner=s->scope==1?(int)i-1:-1; snprintf(key,sizeof(key),"%u:%d",(unsigned)s->slot_id,owner); sb_json_string(&b,key); sb_lit(&b,":"); const GCSemAuxValue *v=&p->aux[slots[si]][i];
        if(!v->has_value) { sb_lit(&b,"null"); }
        else if(v->kind==0) sb_i64(&b,v->bool_value);
        else { sb_lit(&b,"["); sb_u64(&b,v->square%r->board_size); sb_lit(&b,","); sb_u64(&b,v->square/r->board_size); sb_lit(&b,"]"); }
    }}
    sb_lit(&b,"},\"board\":[");
    for(uint16_t sq=0;sq<(uint16_t)(r->board_size*r->board_size);sq++){if(sq)sb_lit(&b,",");const GCPiece *pce=&p->board[sq];if(!pce->occupied)sb_lit(&b,"null");else{if(pce->base_type>=r->type_count||pce->current_type>=r->type_count){b.ok=0;break;}sb_lit(&b,"[");sb_i64(&b,pce->owner);sb_lit(&b,",");sb_json_string(&b,r->type_ids[pce->base_type]);sb_lit(&b,",");sb_json_string(&b,r->type_ids[pce->current_type]);sb_lit(&b,",");sb_lit(&b,pce->promoted?"true":"false");sb_lit(&b,"]");}}
    sb_lit(&b,"],\"hands\":[[[");
    for(uint8_t owner=0;owner<2;owner++){if(owner)sb_lit(&b,"],[");int first_hand=1;for(uint16_t ti=0;ti<r->type_count;ti++){uint16_t t=types[ti];uint16_t count=p->hand_counts[owner][t];if(!count)continue;if(!first_hand)sb_lit(&b,",");first_hand=0;sb_lit(&b,"[");sb_json_string(&b,r->type_ids[t]);sb_lit(&b,",");sb_u64(&b,count);sb_lit(&b,"]");}}
    sb_lit(&b,"]]],\"ruleset\":"); sb_json_string(&b,r->fingerprint); sb_lit(&b,",\"side_to_move\":"); sb_u64(&b,p->side_to_move); sb_lit(&b,"}");
    if(!b.ok){free(b.data);return 0;} GCSha256 sha;uint8_t digest[32];gc_sha256_init(&sha);gc_sha256_update(&sha,(const uint8_t*)b.data,b.len);gc_sha256_final(&sha,digest);gc_sha256_hex(digest,out_hex);free(b.data);return 1;
}
