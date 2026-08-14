#ifndef GENERIC_CHESS_NATIVE_RUNTIME_H
#define GENERIC_CHESS_NATIVE_RUNTIME_H

#include "native_semantic_key.h"

/* Apply one exact semantic action to a copied position.  This first validates
 * the action's pattern/geometry/target binding, then executes the declared
 * board, hand, type and auxiliary effects in order.  Returns 1 on success;
 * the destination is untouched on failure. */
int gc_semantic_runtime_make_checked(GCSemanticPosition *child,
                                      const GCSemanticRules *rules,
                                      const GCSemanticPosition *parent,
                                      uint64_t action);

/* Test-only witness inspection; not exposed through generic_chess.native.semantic. */
int gc_semantic_runtime_action_delivers_check_debug(
    const GCSemanticRules *rules,
    const GCSemanticPosition *parent,
    uint64_t action);

int gc_semantic_runtime_in_check(const GCSemanticRules *rules,
                                 const GCSemanticPosition *position,
                                 uint8_t side);

int gc_semantic_runtime_is_square_attacked(const GCSemanticRules *rules,
                                           const GCSemanticPosition *position,
                                           uint16_t square,
                                           uint8_t by_owner);

typedef struct {
    GCSemanticPosition saved;
} GCSemanticUndo;

#define GC_SEM_DELTA_MAX_BOARD_CELLS (2 * GC_SEM_MAX_EFFECTS + 1)
#define GC_SEM_DELTA_MAX_HAND_CELLS (2 * GC_SEM_MAX_EFFECTS + 2)
#define GC_SEM_DELTA_MAX_AUX_CELLS (GC_SEM_MAX_AUX_SLOTS * 3)

typedef struct {
    uint16_t square;
    GCPiece old_value;
} GCSemDeltaBoardCell;

typedef struct {
    uint8_t owner;
    uint16_t type;
    uint16_t old_count;
} GCSemDeltaHandCell;

typedef struct {
    uint8_t slot;
    uint8_t owner_index;
    GCSemAuxValue old_value;
} GCSemDeltaAuxCell;

/* Bounded transactional undo. The seen masks make every cell first-write
 * capture only; no full board, hand, aux, or history copy is retained. */
typedef struct {
    uint64_t board_seen[GC_MAX_SQUARES / 64];
    GCSemDeltaBoardCell board[GC_SEM_DELTA_MAX_BOARD_CELLS];
    uint8_t board_count;
    uint64_t hand_seen[2];
    GCSemDeltaHandCell hand[GC_SEM_DELTA_MAX_HAND_CELLS];
    uint8_t hand_count;
    uint32_t aux_seen;
    GCSemDeltaAuxCell aux[GC_SEM_DELTA_MAX_AUX_CELLS];
    uint8_t aux_count;
    uint8_t old_side_to_move;
    uint16_t old_ply;
    uint16_t old_history_len;
    uint8_t old_history_exact;
    uint64_t old_history_lo;
    uint64_t old_history_hi;
    uint64_t old_history_digest[4];
} GCSemanticDeltaUndo;

int gc_semantic_runtime_make_trusted(GCSemanticPosition *position,
                                     const GCSemanticRules *rules,
                                     uint64_t action,
                                     GCSemanticUndo *undo);
void gc_semantic_runtime_unmake(GCSemanticPosition *position,
                                const GCSemanticUndo *undo);

int gc_semantic_runtime_delta_make_trusted(
    GCSemanticPosition *position,
    const GCSemanticRules *rules,
    uint64_t action,
    GCSemanticDeltaUndo *undo);
void gc_semantic_runtime_delta_unmake(GCSemanticPosition *position,
                                      const GCSemanticDeltaUndo *undo);

typedef struct {
    const GCSemanticRules *rules;
    GCSemanticPosition current;
    GCSemanticDeltaUndo *undos;
    uint16_t depth;
    uint16_t capacity;
    uint16_t peak_depth;
    uint16_t capacity_grows;
} GCSemanticDeltaRuntimeStack;

GCSemanticDeltaRuntimeStack *gc_semantic_delta_runtime_new(
    const GCSemanticRules *rules,
    const GCSemanticPosition *position);
void gc_semantic_delta_runtime_free(GCSemanticDeltaRuntimeStack *runtime);
int gc_semantic_delta_runtime_push(GCSemanticDeltaRuntimeStack *runtime,
                                   uint64_t action);
int gc_semantic_delta_runtime_pop(GCSemanticDeltaRuntimeStack *runtime);

#endif
