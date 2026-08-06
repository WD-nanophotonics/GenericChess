#include "native_hash.h"

void gc_hash_full(const GCRules *rules, GCPosition *pos) {
    uint64_t lo = 0, hi = 0;
    GCSquare sq;
    for (sq = 0; sq < rules->squares; sq++) {
        if (pos->board[sq].occupied) {
            const GCPiece *p = &pos->board[sq];
            lo ^= rules->piece_owner_square_hash[0][p->owner][sq];
            hi ^= rules->piece_owner_square_hash[1][p->owner][sq];
            lo ^= rules->piece_base_hash[0][sq][p->base_type];
            hi ^= rules->piece_base_hash[1][sq][p->base_type];
            lo ^= rules->piece_current_hash[0][sq][p->current_type];
            hi ^= rules->piece_current_hash[1][sq][p->current_type];
            if (p->promoted) {
                lo ^= rules->piece_promoted_hash[0][sq];
                hi ^= rules->piece_promoted_hash[1][sq];
            }
        }
    }
    int owner, type, slot;
    for (owner = 0; owner < 2; owner++) {
        for (type = 0; type < rules->type_count; type++) {
            uint16_t count = pos->hand_counts[owner][type];
            for (slot = 0; slot < count; slot++) {
                lo ^= rules->hand_piece_hash[0][owner][type][slot];
                hi ^= rules->hand_piece_hash[1][owner][type][slot];
            }
        }
        if (pos->side_to_move == owner) {
            lo ^= rules->side_hash[0][owner];
            hi ^= rules->side_hash[1][owner];
        }
    }
    pos->hash_lo = lo;
    pos->hash_hi = hi;
}

int gc_hash_verify(const GCRules *rules, const GCPosition *pos) {
    uint64_t lo = pos->hash_lo, hi = pos->hash_hi;
    GCPosition *mutable_pos = (GCPosition *)pos;
    gc_hash_full(rules, mutable_pos);
    int ok = (mutable_pos->hash_lo == lo) && (mutable_pos->hash_hi == hi);
    mutable_pos->hash_lo = lo;
    mutable_pos->hash_hi = hi;
    return ok;
}

uint16_t gc_repetition_count(const GCRules *rules, const GCPosition *pos) {
    (void)rules;
    uint16_t count = 0;
    uint16_t i;
    for (i = 0; i < pos->history_len; i++) {
        if (pos->history_lo[i] == pos->hash_lo &&
            pos->history_hi[i] == pos->hash_hi) {
            /* With full history replay root_hash_count is 0 and every entry
             * counts once; the legacy perft pack folds the Python root count
             * into root_hash_count so index 0 then contributes that count. */
            count += (uint16_t)((i == 0 && pos->root_hash_count != 0)
                                    ? pos->root_hash_count
                                    : 1);
        }
    }
    return count;
}

/* Incremental hand hash helpers used by make/unmake. */
int gc_hash_add_hand(GCRules *rules, GCPosition *pos, uint8_t owner,
                     GCTypeIndex type) {
    uint16_t count = pos->hand_counts[owner][type];
    if (count >= GC_MAX_HAND) {
        return 0;
    }
    pos->hash_lo ^= rules->hand_piece_hash[0][owner][type][count];
    pos->hash_hi ^= rules->hand_piece_hash[1][owner][type][count];
    return 1;
}

int gc_hash_remove_hand(GCRules *rules, GCPosition *pos, uint8_t owner,
                        GCTypeIndex type) {
    uint16_t count = pos->hand_counts[owner][type];
    if (count == 0 || count > GC_MAX_HAND) {
        return 0;
    }
    pos->hash_lo ^= rules->hand_piece_hash[0][owner][type][count - 1];
    pos->hash_hi ^= rules->hand_piece_hash[1][owner][type][count - 1];
    return 1;
}

void gc_hash_xor_piece(GCRules *rules, GCPosition *pos, const GCPiece *piece,
                       GCSquare square) {
    pos->hash_lo ^= rules->piece_owner_square_hash[0][piece->owner][square];
    pos->hash_hi ^= rules->piece_owner_square_hash[1][piece->owner][square];
    pos->hash_lo ^= rules->piece_base_hash[0][square][piece->base_type];
    pos->hash_hi ^= rules->piece_base_hash[1][square][piece->base_type];
    pos->hash_lo ^= rules->piece_current_hash[0][square][piece->current_type];
    pos->hash_hi ^= rules->piece_current_hash[1][square][piece->current_type];
    if (piece->promoted) {
        pos->hash_lo ^= rules->piece_promoted_hash[0][square];
        pos->hash_hi ^= rules->piece_promoted_hash[1][square];
    }
}

void gc_hash_xor_side(GCRules *rules, GCPosition *pos, uint8_t owner) {
    pos->hash_lo ^= rules->side_hash[0][owner];
    pos->hash_hi ^= rules->side_hash[1][owner];
}
