#ifndef GENERIC_CHESS_NATIVE_RULES_H
#define GENERIC_CHESS_NATIVE_RULES_H

#include "native_types.h"

/* Plain payload filled by the Python module from a serialized payload dict;
 * keeps the C kernel independent of Python domain classes. */
typedef struct {
    char fingerprint[65];
    int width;
    int height;
    int type_count;
    int repetition_limit;
    int max_ply;

    uint8_t is_anchor[GC_MAX_TYPES];
    uint8_t is_promotable[GC_MAX_TYPES];
    uint8_t atom_count[GC_MAX_TYPES];
    GCAtom atoms[GC_MAX_TYPES][GC_MAX_ATOMS];

    uint8_t promo_target_count[GC_MAX_TYPES];
    GCTypeIndex promo_targets[GC_MAX_TYPES][GC_MAX_PROMO_TARGETS];

    uint32_t *promo_pairs[GC_MAX_TYPES][2];
    uint32_t promo_pair_count[GC_MAX_TYPES][2];
    uint64_t promo_forced[GC_MAX_TYPES][2][4];
    uint64_t alive_promo[GC_MAX_TYPES][2][GC_MAX_SQUARES];
    uint64_t drop_mask[GC_MAX_TYPES][2][4];
} GCCompiledPayload;

/* Allocate and fully copy the payload into an owned GCRules (including hash
 * table initialization). Returns NULL on allocation failure. */
GCRules *gc_rules_compile(const GCCompiledPayload *payload);

void gc_rules_free(GCRules *rules);

/* Free the temporary per-(type,owner) pair arrays owned by a payload. */
void gc_payload_free_pairs(GCCompiledPayload *payload);

#endif /* GENERIC_CHESS_NATIVE_RULES_H */
