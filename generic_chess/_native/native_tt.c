#include "native_tt.h"

#include <stdlib.h>
#include <string.h>

int32_t gc_score_to_tt(const GCEvaluationTables *eval, int32_t score, int ply) {
    if (score > eval->mate_threshold) {
        return score + ply;
    }
    if (score < -eval->mate_threshold) {
        return score - ply;
    }
    return score;
}

int32_t gc_score_from_tt(const GCEvaluationTables *eval, int32_t score, int ply) {
    if (score > eval->mate_threshold) {
        return score - ply;
    }
    if (score < -eval->mate_threshold) {
        return score + ply;
    }
    return score;
}

static size_t gc_tt_index(const GCTable *tt, const GCPosition *pos) {
    uint64_t x = pos->hash_lo ^ pos->hash_hi ^ pos->repetition_context_lo ^
                 pos->repetition_context_hi;
    x ^= (uint64_t)pos->ply << 1;
    x ^= (uint64_t)pos->history_len << 2;
    x ^= x >> 30;
    x *= 0xBF58476D1CE4E5B9ull;
    x ^= x >> 27;
    x *= 0x94D049BB133111EBull;
    x ^= x >> 31;
    return (size_t)(x & (tt->bucket_count - 1));
}

static int gc_tt_key_match(const GCTTEntry *e, const GCPosition *pos) {
    return e->hash_lo == pos->hash_lo && e->hash_hi == pos->hash_hi &&
           e->repetition_lo == pos->repetition_context_lo &&
           e->repetition_hi == pos->repetition_context_hi &&
           e->ply == pos->ply && e->history_len == pos->history_len;
}

GCTable *gc_tt_create(size_t requested_bytes, size_t *allocated_out) {
    if (allocated_out != NULL) {
        *allocated_out = 0;
    }
    if (requested_bytes == 0) {
        return NULL; /* disabled */
    }
    size_t bucket_size = sizeof(GCTTBucket);
    size_t max_buckets = requested_bytes / bucket_size;
    if (max_buckets == 0) {
        max_buckets = 1;
    }
    size_t buckets = 1;
    while (buckets <= max_buckets / 2) {
        buckets *= 2;
    }
    size_t bytes = 0;
    if (!gc_checked_size_mul(buckets, bucket_size, &bytes)) {
        return NULL;
    }
    GCTable *tt = (GCTable *)calloc(1, sizeof(GCTable));
    if (tt == NULL) {
        return NULL;
    }
    tt->buckets = (GCTTBucket *)calloc(buckets, bucket_size);
    if (tt->buckets == NULL) {
        free(tt);
        return NULL;
    }
    tt->bucket_count = buckets;
    tt->requested_bytes = requested_bytes;
    tt->allocated_bytes = bytes;
    tt->generation = 1;
    if (allocated_out != NULL) {
        *allocated_out = bytes;
    }
    return tt;
}

void gc_tt_free(GCTable *tt) {
    if (tt == NULL) {
        return;
    }
    free(tt->buckets);
    free(tt);
}

void gc_tt_clear(GCTable *tt) {
    if (tt == NULL) {
        return;
    }
    memset(tt->buckets, 0, tt->allocated_bytes);
    tt->occupied_entries = 0;
    tt->generation = 1;
}

int gc_tt_probe(const GCTable *tt, const GCPosition *pos, int depth,
                const GCEvaluationTables *eval, int ply, int32_t *score_out,
                GCPackedAction *action_out, int *has_action_out,
                int *entry_depth_out, uint64_t *collision_out) {
    if (tt == NULL) {
        return 0;
    }
    GCTTBucket *bucket = &tt->buckets[gc_tt_index(tt, pos)];
    int way;
    for (way = 0; way < GC_TT_WAYS; way++) {
        GCTTEntry *e = &bucket->entries[way];
        if (!e->occupied) {
            continue;
        }
        if (gc_tt_key_match(e, pos)) {
            if (score_out != NULL) {
                *score_out = gc_score_from_tt(eval, e->score, ply);
            }
            if (action_out != NULL) {
                *action_out = e->best_action;
            }
            if (has_action_out != NULL) {
                *has_action_out = e->has_action;
            }
            if (entry_depth_out != NULL) {
                *entry_depth_out = e->depth;
            }
            return 1;
        }
        if (collision_out != NULL) {
            (*collision_out)++;
        }
    }
    return 0;
}

int gc_tt_store(GCTable *tt, const GCPosition *pos, int depth,
                const GCEvaluationTables *eval, int ply, int32_t score,
                GCTTBound bound, GCPackedAction best_action, int has_action,
                uint64_t *replaced_out) {
    if (tt == NULL) {
        return 0;
    }
    if (replaced_out != NULL) {
        *replaced_out = 0;
    }
    GCTTBucket *bucket = &tt->buckets[gc_tt_index(tt, pos)];
    GCTTEntry *target = NULL;
    int way;
    for (way = 0; way < GC_TT_WAYS; way++) {
        GCTTEntry *e = &bucket->entries[way];
        if (e->occupied && gc_tt_key_match(e, pos)) {
            if (depth >= e->depth || tt->generation > e->generation) {
                target = e;
            }
            break;
        }
    }
    if (target == NULL) {
        for (way = 0; way < GC_TT_WAYS; way++) {
            if (!bucket->entries[way].occupied) {
                target = &bucket->entries[way];
                break;
            }
        }
    }
    if (target == NULL) {
        /* Replacement priority: older generation, then shallowest depth,
         * then the fixed way index for determinism. */
        target = &bucket->entries[0];
        uint16_t best_gen = target->generation;
        int16_t best_depth = target->depth;
        for (way = 1; way < GC_TT_WAYS; way++) {
            GCTTEntry *e = &bucket->entries[way];
            if (e->generation < best_gen ||
                (e->generation == best_gen && e->depth < best_depth)) {
                target = e;
                best_gen = e->generation;
                best_depth = e->depth;
            }
        }
    }
    if (replaced_out != NULL) {
        *replaced_out = target->occupied ? 1 : 1;
    }
    if (!target->occupied) {
        tt->occupied_entries++;
    }
    memset(target, 0, sizeof(GCTTEntry));
    target->hash_lo = pos->hash_lo;
    target->hash_hi = pos->hash_hi;
    target->repetition_lo = pos->repetition_context_lo;
    target->repetition_hi = pos->repetition_context_hi;
    target->ply = pos->ply;
    target->history_len = pos->history_len;
    target->score = gc_score_to_tt(eval, score, ply);
    target->depth = (int16_t)depth;
    target->best_action = best_action;
    target->generation = (uint16_t)tt->generation;
    target->bound = (uint8_t)bound;
    target->occupied = 1;
    target->has_action = (uint8_t)(has_action ? 1 : 0);
    return 1;
}
