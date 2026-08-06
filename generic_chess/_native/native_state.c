#include "native_state.h"

#include <string.h>

#include "native_hash.h"

int gc_position_pack(GCPosition *pos, const GCRules *rules,
                     const GCBoardPayload *payload) {
    memset(pos, 0, sizeof(GCPosition));
    pos->side_to_move = payload->side_to_move;
    pos->ply = payload->ply;
    pos->root_hash_count = payload->root_hash_count;
    memcpy(pos->board, payload->board, sizeof(GCPiece) * rules->squares);
    memcpy(pos->hand_counts, payload->hand_counts, sizeof(pos->hand_counts));
    gc_hash_full(rules, pos);
    pos->history_lo[0] = pos->hash_lo;
    pos->history_hi[0] = pos->hash_hi;
    pos->history_len = 1;
    return 1;
}

int gc_make_move(GCPosition *pos, const GCRules *rules, GCPackedAction action,
                 GCUndo *undo) {
    GCSquare to = (GCSquare)GC_ACTION_TO(action);
    GCSquare from = (GCSquare)GC_ACTION_FROM(action);
    GCTypeIndex promo = (GCTypeIndex)GC_ACTION_PROMO(action);
    GCTypeIndex base = (GCTypeIndex)GC_ACTION_BASE(action);
    uint8_t kind = (uint8_t)GC_ACTION_KIND(action);
    uint8_t side = pos->side_to_move;

    memset(undo, 0, sizeof(GCUndo));
    undo->to = to;
    undo->old_side = side;
    undo->old_ply = pos->ply;
    undo->old_history_len = pos->history_len;
    undo->old_hash_lo = pos->hash_lo;
    undo->old_hash_hi = pos->hash_hi;

    if (kind == GC_ACTION_KIND_DROP) {
        if (to >= rules->squares || pos->board[to].occupied) {
            return 0;
        }
        if (pos->hand_counts[side][base] == 0) {
            return 0;
        }
        undo->from = GC_NO_SQUARE;
        undo->was_drop = 1;
        GCPiece piece;
        piece.base_type = base;
        piece.current_type = base;
        piece.owner = side;
        piece.promoted = 0;
        piece.occupied = 1;
        gc_hash_remove_hand((GCRules *)rules, pos, side, base);
        pos->hand_counts[side][base]--;
        pos->board[to] = piece;
        gc_hash_xor_piece((GCRules *)rules, pos, &piece, to);
    } else {
        if (from >= rules->squares || to >= rules->squares) {
            return 0;
        }
        GCPiece moved = pos->board[from];
        GCPiece captured = pos->board[to];
        if (!moved.occupied || moved.owner != side) {
            return 0;
        }
        if (captured.occupied && captured.owner == side) {
            return 0;
        }
        undo->from = from;
        undo->moved = moved;
        undo->captured = captured;
        /* The action's promo field is 8-bit: 0xFF is the "no promotion"
         * sentinel (GC_NO_TYPE is the 16-bit sentinel). */
        undo->was_promotion = (promo != 0xFF);

        GCPiece placed = moved;
        if (undo->was_promotion) {
            placed.current_type = promo;
            placed.promoted = 1;
        }

        gc_hash_xor_piece((GCRules *)rules, pos, &moved, from);
        if (captured.occupied) {
            gc_hash_xor_piece((GCRules *)rules, pos, &captured, to);
            gc_hash_add_hand((GCRules *)rules, pos, side, captured.base_type);
            pos->hand_counts[side][captured.base_type]++;
        }
        memset(&pos->board[from], 0, sizeof(GCPiece));
        pos->board[to] = placed;
        gc_hash_xor_piece((GCRules *)rules, pos, &placed, to);
    }

    gc_hash_xor_side((GCRules *)rules, pos, side); /* remove old side */
    pos->side_to_move = 1 - side;
    gc_hash_xor_side((GCRules *)rules, pos, 1 - side); /* add new side */
    pos->ply++;
    pos->history_lo[pos->history_len] = pos->hash_lo;
    pos->history_hi[pos->history_len] = pos->hash_hi;
    pos->history_len++;
    return 1;
}

void gc_unmake_move(GCPosition *pos, const GCRules *rules, const GCUndo *undo) {
    (void)rules;
    uint8_t side = undo->old_side;
    if (undo->was_drop) {
        GCPiece dropped = pos->board[undo->to];
        gc_hash_xor_piece((GCRules *)rules, pos, &dropped, undo->to);
        memset(&pos->board[undo->to], 0, sizeof(GCPiece));
        gc_hash_add_hand((GCRules *)rules, pos, side, dropped.base_type);
        pos->hand_counts[side][dropped.base_type]++;
    } else {
        GCPiece placed = pos->board[undo->to];
        gc_hash_xor_piece((GCRules *)rules, pos, &placed, undo->to);
        pos->board[undo->from] = undo->moved;
        if (undo->captured.occupied) {
            pos->board[undo->to] = undo->captured;
            gc_hash_xor_piece((GCRules *)rules, pos, &undo->captured, undo->to);
            gc_hash_remove_hand((GCRules *)rules, pos, side,
                                undo->captured.base_type);
            pos->hand_counts[side][undo->captured.base_type]--;
        } else {
            memset(&pos->board[undo->to], 0, sizeof(GCPiece));
        }
    }
    pos->side_to_move = side;
    pos->ply = undo->old_ply;
    pos->history_len = undo->old_history_len;
    pos->hash_lo = undo->old_hash_lo;
    pos->hash_hi = undo->old_hash_hi;
}

int gc_make_move_verify(GCPosition *pos, const GCRules *rules,
                        GCPackedAction action, GCUndo *undo) {
    int ok = gc_make_move(pos, rules, action, undo);
    if (ok) {
        ok = gc_hash_verify(rules, pos);
    }
    return ok;
}
