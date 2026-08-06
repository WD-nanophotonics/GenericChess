#ifndef GENERIC_CHESS_NATIVE_TYPES_H
#define GENERIC_CHESS_NATIVE_TYPES_H

/* Native Phase 1 kernel types and packed-action layout.
 *
 * Square index is row-major: index = rank * width + file (rank 0 is the
 * first row), matching the Python Core linearization.
 */

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define GC_MAX_SQUARES 256   /* supports boards up to 16x16 */
#define GC_MAX_TYPES 64
#define GC_MAX_ATOMS 16
#define GC_MAX_PROMO_TARGETS 8
#define GC_MAX_ACTIONS 4096
#define GC_MAX_PLY 512
#define GC_MAX_HAND 64
#define GC_NO_SQUARE 0xFFFFu
#define GC_NO_TYPE 0xFFFFu

typedef uint16_t GCSquare;
typedef uint16_t GCTypeIndex;
typedef uint64_t GCPackedAction;

typedef struct {
    int16_t df;
    int16_t dr;
} GCVector;

typedef struct {
    uint8_t kind;       /* 0 = leap, 1 = ray */
    GCVector vec;       /* owner-relative offset (leap) or direction (ray) */
    uint8_t max_steps;  /* 0 = unbounded (ray) */
} GCAtom;

typedef struct {
    GCTypeIndex base_type;
    GCTypeIndex current_type;
    uint8_t owner;
    uint8_t promoted;
    uint8_t occupied;
} GCPiece;

/* Packed action bit layout (64-bit).
 *  bits 0-7   : to square (0..255)
 *  bits 8-15  : from square (0..255; 0xFF = drop sentinel)
 *  bits 16-23 : promotion target type index (0xFF = none)
 *  bits 24-31 : base type index (mover base / drop base)
 *  bits 32-35 : kind (0 = board, 1 = drop)
 */
#define GC_ACTION_TO_SHIFT 0u
#define GC_ACTION_TO_MASK 0xFFull
#define GC_ACTION_FROM_SHIFT 8u
#define GC_ACTION_FROM_MASK 0xFFull
#define GC_ACTION_PROMO_SHIFT 16u
#define GC_ACTION_PROMO_MASK 0xFFull
#define GC_ACTION_BASE_SHIFT 24u
#define GC_ACTION_BASE_MASK 0xFFull
#define GC_ACTION_KIND_SHIFT 32u
#define GC_ACTION_KIND_MASK 0xFull

#define GC_ACTION_KIND_BOARD 0u
#define GC_ACTION_KIND_DROP 1u

#define GC_ACTION_TO(a) (((a) >> GC_ACTION_TO_SHIFT) & GC_ACTION_TO_MASK)
#define GC_ACTION_FROM(a) (((a) >> GC_ACTION_FROM_SHIFT) & GC_ACTION_FROM_MASK)
#define GC_ACTION_PROMO(a) (((a) >> GC_ACTION_PROMO_SHIFT) & GC_ACTION_PROMO_MASK)
#define GC_ACTION_BASE(a) (((a) >> GC_ACTION_BASE_SHIFT) & GC_ACTION_BASE_MASK)
#define GC_ACTION_KIND(a) (((a) >> GC_ACTION_KIND_SHIFT) & GC_ACTION_KIND_MASK)

#define GC_ACTION_MAKE(to, from, promo, base, kind) \
    ((((uint64_t)(to) & GC_ACTION_TO_MASK) << GC_ACTION_TO_SHIFT) | \
     (((uint64_t)(from) & GC_ACTION_FROM_MASK) << GC_ACTION_FROM_SHIFT) | \
     (((uint64_t)(promo) & GC_ACTION_PROMO_MASK) << GC_ACTION_PROMO_SHIFT) | \
     (((uint64_t)(base) & GC_ACTION_BASE_MASK) << GC_ACTION_BASE_SHIFT) | \
     (((uint64_t)(kind) & GC_ACTION_KIND_MASK) << GC_ACTION_KIND_SHIFT))

#define GC_ACTION_BOARD(to, from, base) \
    GC_ACTION_MAKE((to), (from), GC_NO_TYPE, (base), GC_ACTION_KIND_BOARD)
#define GC_ACTION_PROMOTED(to, from, promo, base) \
    GC_ACTION_MAKE((to), (from), (promo), (base), GC_ACTION_KIND_BOARD)
#define GC_ACTION_DROP(to, base) \
    GC_ACTION_MAKE((to), GC_NO_SQUARE, GC_NO_TYPE, (base), GC_ACTION_KIND_DROP)

typedef struct {
    GCPiece board[GC_MAX_SQUARES];
    uint16_t hand_counts[2][GC_MAX_TYPES];
    uint8_t side_to_move;
    uint16_t ply;
    uint64_t hash_lo;
    uint64_t hash_hi;
    uint64_t history_lo[GC_MAX_PLY + 1];
    uint64_t history_hi[GC_MAX_PLY + 1];
    uint16_t history_len;
    uint16_t root_hash_count; /* repetition count of the root hash from Python */
} GCPosition;

typedef struct {
    GCSquare from;
    GCSquare to;
    GCPiece moved;     /* piece at from before make */
    GCPiece captured;  /* piece at to before make (occupied=0 if none) */
    uint8_t was_drop;
    uint8_t was_promotion;
    uint8_t old_side;
    uint16_t old_ply;
    uint16_t old_history_len;
    uint64_t old_hash_lo;
    uint64_t old_hash_hi;
} GCUndo;

typedef struct {
    char fingerprint[65];
    uint8_t width;
    uint8_t height;
    uint16_t squares;
    uint8_t type_count;
    uint8_t repetition_limit;
    uint16_t max_ply;

    uint8_t is_anchor[GC_MAX_TYPES];
    uint8_t is_promotable[GC_MAX_TYPES];
    uint8_t atom_count[GC_MAX_TYPES];
    GCAtom atoms[GC_MAX_TYPES][GC_MAX_ATOMS];

    uint8_t promo_target_count[GC_MAX_TYPES];
    GCTypeIndex promo_targets[GC_MAX_TYPES][GC_MAX_PROMO_TARGETS];

    /* Promotion allowed pairs per (type, owner): packed (from<<16|to). */
    uint32_t *promo_pairs[GC_MAX_TYPES][2];
    uint32_t promo_pair_count[GC_MAX_TYPES][2];
    /* Forced promotion to-squares per (type, owner): 256-bit bitset. */
    uint64_t promo_forced[GC_MAX_TYPES][2][4];
    /* Alive promotion-target mask per (type, owner, square): bit t set when
     * target index t has non-empty mobility from that square (matches Core's
     * "structurally dead target" filter). */
    uint64_t alive_promo[GC_MAX_TYPES][2][GC_MAX_SQUARES];
    /* Drop mask per (type, owner): 256-bit bitset. */
    uint64_t drop_mask[GC_MAX_TYPES][2][4];

    /* Deterministic Zobrist tables (derived from the fingerprint).
     * stream 0 = low 64-bit half, stream 1 = high half.
     * hand entries are per (owner,type,slot) so quantities are distinguished
     * and incremental add/remove toggles exactly one slot. */
    uint64_t piece_hash[2][2][GC_MAX_SQUARES][GC_MAX_TYPES][2];
    uint64_t hand_piece_hash[2][2][GC_MAX_TYPES][GC_MAX_HAND];
    uint64_t side_hash[2][2];
} GCRules;

typedef enum {
    GC_TERM_ONGOING = 0,
    GC_TERM_CHECKMATE = 1,
    GC_TERM_STALEMATE = 2,
    GC_TERM_REPETITION = 3,
    GC_TERM_MAX_PLY = 4
} GCTerminal;

#endif /* GENERIC_CHESS_NATIVE_TYPES_H */
