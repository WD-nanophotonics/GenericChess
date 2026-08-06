#ifndef GENERIC_CHESS_NATIVE_TT_H
#define GENERIC_CHESS_NATIVE_TT_H

#include "native_eval.h"
#include "native_types.h"

#define GC_TT_WAYS 4

typedef enum {
    GC_TT_BOUND_NONE = 0,
    GC_TT_BOUND_EXACT = 1,
    GC_TT_BOUND_LOWER = 2,
    GC_TT_BOUND_UPPER = 3
} GCTTBound;

typedef struct {
    uint64_t hash_lo;
    uint64_t hash_hi;
    uint64_t repetition_lo;
    uint64_t repetition_hi;
    uint16_t ply;
    uint16_t history_len;
    int32_t score;
    int16_t depth;
    GCPackedAction best_action;
    uint16_t generation;
    uint8_t bound;
    uint8_t occupied;
    uint8_t has_action;
} GCTTEntry;

typedef struct {
    GCTTEntry entries[GC_TT_WAYS];
} GCTTBucket;

typedef struct {
    GCTTBucket *buckets;
    size_t bucket_count; /* power of two, >= 1 */
    size_t requested_bytes;
    size_t allocated_bytes;
    uint32_t generation;
    uint64_t occupied_entries;
} GCTable;

/* Create a TT with at most ``requested_bytes`` of table memory (0 = disabled,
 * returns NULL).  ``allocated_out`` receives the actual bytes. */
GCTable *gc_tt_create(size_t requested_bytes, size_t *allocated_out);

void gc_tt_free(GCTable *tt);
void gc_tt_clear(GCTable *tt);

int32_t gc_score_to_tt(const GCEvaluationTables *eval, int32_t score, int ply);
int32_t gc_score_from_tt(const GCEvaluationTables *eval, int32_t score, int ply);

/* Probe.  Returns 1 on a full key match (score already ply-adjusted via
 * ``*score_out``).  ``*collision_out`` counts a visited bucket whose occupied
 * entry did not match. */
int gc_tt_probe(const GCTable *tt, const GCPosition *pos, int depth,
                const GCEvaluationTables *eval, int ply, int32_t *score_out,
                GCPackedAction *action_out, int *has_action_out,
                uint64_t *collision_out);

/* Store one node result.  ``*replaced_out`` receives 1 when an entry was
 * replaced (or a new one written). */
int gc_tt_store(GCTable *tt, const GCPosition *pos, int depth,
                const GCEvaluationTables *eval, int ply, int32_t score,
                GCTTBound bound, GCPackedAction best_action, int has_action,
                uint64_t *replaced_out);

#endif /* GENERIC_CHESS_NATIVE_TT_H */
