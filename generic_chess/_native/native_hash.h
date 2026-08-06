#ifndef GENERIC_CHESS_NATIVE_HASH_H
#define GENERIC_CHESS_NATIVE_HASH_H

#include "native_types.h"

/* Full recomputation of the deterministic 128-bit position hash. */
void gc_hash_full(const GCRules *rules, GCPosition *pos);

/* Debug helper: returns 1 when the stored hash matches the full recompute. */
int gc_hash_verify(const GCRules *rules, const GCPosition *pos);

/* Repetition count of the position's current hash within its history
 * (including the root base count supplied by Python). */
uint16_t gc_repetition_count(const GCRules *rules, const GCPosition *pos);

/* Number of occurrences of a hash in the position history, using the same
 * weighting as gc_repetition_count (index 0 weighted by root_hash_count). */
uint16_t gc_hash_occurrences(const GCRules *rules, const GCPosition *pos,
                             uint64_t hash_lo, uint64_t hash_hi);

/* Deterministic token for one (position hash, occurrence count) pair. */
void gc_repetition_count_token(uint64_t position_lo, uint64_t position_hi,
                               uint16_t count, uint64_t *out_lo,
                               uint64_t *out_hi);

/* Recompute the repetition-context fingerprint from the full history. */
int gc_repetition_context_rebuild(GCPosition *pos);

/* Incremental hash helpers used by make/unmake. */
/* Return 1 on success, 0 when the hand count is out of the supported range
 * (must be treated as an error by make/unmake, never silently ignored). */
int gc_hash_add_hand(GCRules *rules, GCPosition *pos, uint8_t owner,
                     GCTypeIndex type);
int gc_hash_remove_hand(GCRules *rules, GCPosition *pos, uint8_t owner,
                        GCTypeIndex type);
void gc_hash_xor_piece(GCRules *rules, GCPosition *pos, const GCPiece *piece,
                       GCSquare square);
void gc_hash_xor_side(GCRules *rules, GCPosition *pos, uint8_t owner);

#endif /* GENERIC_CHESS_NATIVE_HASH_H */
