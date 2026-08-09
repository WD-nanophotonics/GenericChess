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
