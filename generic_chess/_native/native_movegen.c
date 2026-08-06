#include "native_movegen.h"

#include <stdint.h>

#include "native_attack.h"
#include "native_state.h"

static int16_t gc_abs_df(const GCAtom *atom, uint8_t owner) {
    return owner == 0 ? atom->vec.df : (int16_t)(-atom->vec.df);
}

static int16_t gc_abs_dr(const GCAtom *atom, uint8_t owner) {
    return owner == 0 ? atom->vec.dr : (int16_t)(-atom->vec.dr);
}

static int gc_promo_pair_exists(const GCRules *rules, GCTypeIndex base,
                                uint8_t owner, GCSquare from, GCSquare to) {
    uint32_t wanted = ((uint32_t)from << 16) | (uint32_t)to;
    uint32_t count = rules->promo_pair_count[base][owner];
    uint32_t i;
    for (i = 0; i < count; i++) {
        if (rules->promo_pairs[base][owner][i] == wanted) {
            return 1;
        }
    }
    return 0;
}

static int gc_promo_forced(const GCRules *rules, GCTypeIndex base,
                           uint8_t owner, GCSquare to) {
    return (rules->promo_forced[base][owner][to / 64] >> (to % 64)) & 1u;
}

static int gc_drop_allowed(const GCRules *rules, GCTypeIndex type,
                           uint8_t owner, GCSquare sq) {
    return (rules->drop_mask[type][owner][sq / 64] >> (sq % 64)) & 1u;
}

static void gc_append_board_move(GCPackedAction *out, int *count, int cap,
                                 GCSquare to, GCSquare from,
                                 GCTypeIndex base) {
    if (*count < cap) {
        out[(*count)++] = GC_ACTION_BOARD(to, from, base);
    }
}

static void gc_expand_promotion(GCRules *rules, GCPosition *pos,
                                GCPackedAction *out, int *count, int cap,
                                GCSquare to, GCSquare from) {
    uint8_t side = pos->side_to_move;
    const GCPiece *moved = &pos->board[from];
    GCTypeIndex base = moved->base_type;
    if (!rules->is_promotable[base] || moved->promoted) {
        gc_append_board_move(out, count, cap, to, from, base);
        return;
    }
    if (!gc_promo_pair_exists(rules, base, side, from, to)) {
        gc_append_board_move(out, count, cap, to, from, base);
        return;
    }
    uint64_t alive = rules->alive_promo[base][side][to];
    int forced = gc_promo_forced(rules, base, side, to);
    if (!forced) {
        gc_append_board_move(out, count, cap, to, from, base);
    }
    uint8_t t;
    for (t = 0; t < rules->promo_target_count[base]; t++) {
        GCTypeIndex target = rules->promo_targets[base][t];
        if ((alive >> target) & 1u) {
            if (*count < cap) {
                out[(*count)++] = GC_ACTION_PROMOTED(to, from, target, base);
            }
        }
    }
}

int gc_pseudo_actions(GCRules *rules, GCPosition *pos, GCPackedAction *out,
                      int cap) {
    uint8_t side = pos->side_to_move;
    int count = 0;
    GCSquare sq;
    for (sq = 0; sq < rules->squares; sq++) {
        const GCPiece *piece = &pos->board[sq];
        if (!piece->occupied || piece->owner != side) {
            continue;
        }
        const GCAtom *atoms = rules->atoms[piece->current_type];
        uint8_t atom_count = rules->atom_count[piece->current_type];
        uint8_t ai;
        for (ai = 0; ai < atom_count; ai++) {
            const GCAtom *atom = &atoms[ai];
            int16_t df = gc_abs_df(atom, side);
            int16_t dr = gc_abs_dr(atom, side);
            if (atom->kind == 0) { /* leap */
                int16_t nf = (int16_t)((int16_t)(sq % rules->width) + df);
                int16_t nr = (int16_t)((int16_t)(sq / rules->width) + dr);
                if (nf < 0 || nf >= rules->width || nr < 0 ||
                    nr >= rules->height) {
                    continue;
                }
                GCSquare to = (GCSquare)(nr * rules->width + nf);
                const GCPiece *occupant = &pos->board[to];
                if (occupant->occupied) {
                    if (occupant->owner == side ||
                        rules->is_anchor[occupant->current_type]) {
                        continue;
                    }
                }
                gc_expand_promotion(rules, pos, out, &count, cap, to, sq);
            } else { /* ray */
                GCSquare cur = sq;
                uint8_t steps = 0;
                while (atom->max_steps == 0 || steps < atom->max_steps) {
                    int16_t nf = (int16_t)((int16_t)(cur % rules->width) + df);
                    int16_t nr = (int16_t)((int16_t)(cur / rules->width) + dr);
                    if (nf < 0 || nf >= rules->width || nr < 0 ||
                        nr >= rules->height) {
                        break;
                    }
                    GCSquare to = (GCSquare)(nr * rules->width + nf);
                    const GCPiece *occupant = &pos->board[to];
                    if (occupant->occupied) {
                        if (occupant->owner != side &&
                            !rules->is_anchor[occupant->current_type]) {
                            gc_expand_promotion(rules, pos, out, &count, cap,
                                                to, sq);
                        }
                        break;
                    }
                    gc_expand_promotion(rules, pos, out, &count, cap, to, sq);
                    cur = to;
                    steps++;
                }
            }
        }
    }
    /* Drops. */
    GCTypeIndex type;
    for (type = 0; type < rules->type_count; type++) {
        if (rules->is_anchor[type]) {
            continue;
        }
        uint16_t hand = pos->hand_counts[side][type];
        if (hand == 0) {
            continue;
        }
        GCSquare to;
        for (to = 0; to < rules->squares; to++) {
            if (!pos->board[to].occupied &&
                gc_drop_allowed(rules, type, side, to)) {
                if (count < cap) {
                    out[count++] = GC_ACTION_DROP(to, type);
                }
            }
        }
    }
    return count;
}

int gc_legal_actions(GCRules *rules, GCPosition *pos, GCPackedAction *out,
                     int cap) {
    GCPackedAction pseudo[GC_MAX_ACTIONS];
    int n = gc_pseudo_actions(rules, pos, pseudo, GC_MAX_ACTIONS);
    uint8_t side = pos->side_to_move;
    int count = 0;
    int i;
    for (i = 0; i < n; i++) {
        GCUndo undo;
        if (!gc_make_move(pos, rules, pseudo[i], &undo)) {
            continue;
        }
        GCSquare anchor = gc_find_anchor(rules, pos, side);
        int legal = anchor != GC_NO_SQUARE &&
                    !gc_is_square_attacked(rules, pos, anchor, 1 - side);
        gc_unmake_move(pos, rules, &undo);
        if (legal && count < cap) {
            out[count++] = pseudo[i];
        }
    }
    return count;
}
