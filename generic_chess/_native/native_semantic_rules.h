#ifndef GENERIC_CHESS_NATIVE_SEMANTIC_RULES_H
#define GENERIC_CHESS_NATIVE_SEMANTIC_RULES_H

/* Phase 1.9C-1: C-owned semantic rules capsule (ADR-017).
 *
 * The capsule owns the deterministic numeric payload of CompiledSemanticIR
 * v2 + support and can reconstruct it exactly. It remains deliberately
 * separate from legacy GCRules; runtime execution lives in the independent
 * native_semantic_runtime module and is still capability-gated. */

#include "native_types.h"
#include <Python.h>
#include <stdint.h>

#define GC_SEM_MAX_GEOMETRIES 4096
#define GC_SEM_MAX_PATTERNS 256
#define GC_SEM_MAX_AUX_SLOTS 8
#define GC_SEM_MAX_EFFECTS 4
#define GC_SEM_MAX_INVARIANT_REFS 4

typedef struct {
    uint8_t kind;            /* square_ref enum code */
    uint8_t has_square;
    uint16_t square;
    uint8_t has_offset;
    int16_t offset_df;
    int16_t offset_dr;
    uint8_t owner_relative;
    uint8_t has_step;
    uint16_t step;
    uint8_t has_slot;
    uint16_t slot_id;
} GCSemSquareRef;

typedef struct {
    uint8_t kind;            /* type_ref enum code */
    uint8_t has_type;
    uint16_t type_index;
} GCSemTypeRef;

typedef struct {
    uint8_t kind;            /* spatial enum code */
    GCSemSquareRef *refs;
    uint16_t refs_count;
    uint8_t has_zone;
    uint16_t zone_index;
} GCSemSpatial;

typedef struct {
    uint8_t aggregation;
    uint8_t owner;
    GCSemTypeRef type_ref;
    uint8_t compare_field;
    uint8_t promoted;
    uint8_t location;
    GCSemSpatial spatial;
    uint8_t comparison;
    int32_t value;
} GCSemStateGuard;

typedef struct {
    uint16_t slot_id;
    uint8_t comparison;
    uint8_t has_value;
    int32_t value;
    uint8_t has_square_ref;
    GCSemSquareRef square_ref;
} GCSemSlotGuard;

typedef struct {
    uint8_t kind;            /* effect enum code */
    uint8_t has_from;
    GCSemSquareRef from_ref;
    uint8_t has_to;
    GCSemSquareRef to_ref;
    uint8_t has_square;
    GCSemSquareRef square_ref;
    uint8_t piece_owner;
    uint8_t has_piece_type_ref;
    GCSemTypeRef piece_type_ref;
    uint8_t has_disposition;
    uint8_t disposition;
    uint8_t has_slot;
    uint16_t slot_id;
    uint8_t has_type_ref;
    GCSemTypeRef type_ref;
    uint8_t count;
    uint8_t has_value;
    int32_t value;
} GCSemEffect;

typedef struct {
    uint8_t kind;            /* invariant enum code */
    GCSemSquareRef *refs;
    uint16_t refs_count;
} GCSemInvariant;

typedef struct {
    uint8_t kind;            /* postcondition enum code */
    uint8_t max_stratum;
} GCSemPostcondition;

typedef struct {
    uint8_t kind;            /* path enum code */
    uint8_t has_count;
    int32_t count;
    uint8_t has_lo;
    int32_t lo;
    uint8_t has_hi;
    int32_t hi;
    uint8_t owner_filter;
} GCSemPathPredicate;

typedef struct {
    uint16_t *type_indices;
    uint8_t type_count;
    uint16_t *geometry_indices;
    uint8_t geometry_count;
    uint8_t target;
    GCSemPathPredicate *path;
    uint8_t path_count;
    GCSemStateGuard *guards;
    uint8_t guard_count;
    GCSemSlotGuard *slot_guards;
    uint8_t slot_guard_count;
    GCSemEffect *effects;
    uint8_t effect_count;
    GCSemInvariant *invariants;
    uint8_t invariant_count;
    GCSemPostcondition *postconditions;
    uint8_t postcondition_count;
    uint8_t promotion_mode;
    uint8_t has_explicit_promotion;
    uint16_t explicit_promotion_type;
    uint8_t cost;
    uint8_t stratum;
} GCSemPattern;

typedef struct {
    uint16_t source;
    uint16_t *squares;
    uint16_t count;
} GCSemPathEntry;

typedef struct {
    GCSemPathEntry *entries;
    uint16_t count;
} GCSemPathOwner;

typedef struct {
    uint8_t kind;            /* geometry enum code */
    uint8_t has_min_steps;
    int16_t min_steps;
    uint8_t has_atom_source;
    uint16_t atom_source_type;
    uint16_t atom_source_index;
    GCSemPathOwner paths[2];
} GCSemGeometry;

typedef struct {
    uint16_t *squares;
    uint16_t count;
} GCSemZone;

typedef struct {
    uint16_t slot_id;
    uint8_t value_kind;
    uint8_t scope;
    uint8_t lifetime;
    uint8_t initial_kind;    /* 0 none, 1 bool/int, 2 square */
    int32_t initial_int;
    uint16_t initial_file;
    uint16_t initial_rank;
} GCSemAuxSlot;

typedef struct {
    uint16_t slot_id;
    uint8_t event;
    GCSemSquareRef square_ref;
    uint8_t owner;
} GCSemTrigger;

typedef struct {
    uint8_t is_anchor;
    uint8_t is_promotable;
    uint8_t promo_target_count;
    GCTypeIndex promo_targets[GC_MAX_PROMO_TARGETS];
} GCSemType;

typedef struct {
    uint32_t *pairs;
    uint16_t count;
} GCSemPairList;

typedef struct {
    uint16_t *squares;
    uint16_t count;
} GCSemSquareList;

typedef struct {
    char fingerprint[65];
    uint8_t semantic_payload_version;
    uint8_t board_size;
    uint16_t repetition_limit;
    uint16_t max_ply;
    uint16_t type_count;
    /* Payload v2 owns stable public type IDs for semantic position identity.
     * v1 compile-only capsules leave this NULL. */
    char **type_ids;
    GCSemType types[GC_MAX_TYPES];
    GCSemPairList promo_allowed[GC_MAX_TYPES][2];
    GCSemSquareList promo_forced[GC_MAX_TYPES][2];
    uint64_t alive_promo[GC_MAX_TYPES][2][GC_MAX_SQUARES];
    GCSemSquareList drop_mask[GC_MAX_TYPES][2];
    GCSemGeometry *geometries;
    uint16_t geometry_count;
    GCSemZone *zones;
    uint16_t zone_count;
    GCSemAuxSlot *aux_slots;
    uint8_t aux_slot_count;
    GCSemTrigger *triggers;
    uint16_t trigger_count;
    GCSemPattern *patterns;
    uint16_t pattern_count;
} GCSemanticRules;

/* Parse a Python payload dict into an owned GCSemanticRules.
 * Returns NULL (with a Python exception set) on any parse/validation or
 * allocation failure; partial allocations are freed exactly once. */
GCSemanticRules *gc_semantic_rules_compile(PyObject *payload);

/* Free every nested dynamic allocation exactly once. */
void gc_semantic_rules_free(GCSemanticRules *rules);

/* Rebuild the exact normalized numeric payload dict from C-owned state.
 * Returns a new Python object; never returns a cached Python copy. */
PyObject *gc_semantic_rules_build_info(const GCSemanticRules *rules);

#endif /* GENERIC_CHESS_NATIVE_SEMANTIC_RULES_H */
