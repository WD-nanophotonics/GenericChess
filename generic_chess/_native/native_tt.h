#ifndef GENERIC_CHESS_NATIVE_TT_H
#define GENERIC_CHESS_NATIVE_TT_H

#include "native_eval.h"
#include "native_semantic_state.h"
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
                int *entry_depth_out, uint64_t *collision_out);

/* Store one node result.  ``*replaced_out`` receives 1 when an entry was
 * replaced (or a new one written). */
int gc_tt_store(GCTable *tt, const GCPosition *pos, int depth,
                const GCEvaluationTables *eval, int ply, int32_t score,
                GCTTBound bound, GCPackedAction best_action, int has_action,
                uint64_t *replaced_out);

/* Independent semantic search table.  Its key includes the canonical current
 * position digest and an incremental digest of the exact history/event path;
 * it must not be mixed with the legacy table above. */
#define GC_SEM_TT_WAYS 4
#define GC_SEM_TT_PV_MAX_DEPTH 64

typedef struct {
    uint64_t position_digest[4];
    uint64_t history_context[4];
    uint16_t history_len;
    uint16_t depth;
    uint16_t pv_length;
    int32_t score;
    GCPackedAction best_action;
    GCPackedAction pv[GC_SEM_TT_PV_MAX_DEPTH];
    uint32_t generation;
    uint8_t bound;
    uint8_t occupied;
    uint8_t has_action;
} GCSemanticTTEntry;

typedef struct {
    GCSemanticTTEntry entries[GC_SEM_TT_WAYS];
} GCSemanticTTBucket;

typedef struct {
    GCSemanticTTBucket *buckets;
    size_t bucket_count;
    size_t requested_bytes;
    size_t allocated_bytes;
    uint32_t generation;
    uint64_t occupied_entries;
} GCSemanticTable;

GCSemanticTable *gc_semantic_tt_create(size_t requested_bytes,
                                        size_t *allocated_out);
void gc_semantic_tt_free(GCSemanticTable *tt);
void gc_semantic_tt_clear(GCSemanticTable *tt);
uint32_t gc_semantic_tt_next_generation(GCSemanticTable *tt);
size_t gc_semantic_tt_entry_bytes(void);
int gc_semantic_tt_probe(const GCSemanticTable *tt,
                         const GCSemanticPosition *position,
                         const uint64_t history_context[4], int depth,
                         int32_t *score_out, GCPackedAction *action_out,
                         int *has_action_out, int *entry_depth_out,
                         uint8_t *bound_out, uint32_t *generation_out,
                         uint64_t *collision_out, GCPackedAction *pv_out,
                         uint16_t *pv_length_out);
int gc_semantic_tt_store(GCSemanticTable *tt,
                         const GCSemanticPosition *position,
                         const uint64_t history_context[4], int depth,
                         int32_t score, GCTTBound bound,
                         GCPackedAction best_action, int has_action,
                         const GCPackedAction *pv, uint16_t pv_length,
                         uint64_t *replaced_out);

#endif /* GENERIC_CHESS_NATIVE_TT_H */
