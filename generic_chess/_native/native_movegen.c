#include "native_movegen.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "native_attack.h"
#include "native_state.h"

/* ------------------------------------------------------------- move lists */

void gc_move_list_init(GCMoveList *list) {
    list->data = NULL;
    list->count = 0;
    list->capacity = 0;
    list->error = GC_MOVE_ERROR_NONE;
}

void gc_move_list_clear(GCMoveList *list) {
    list->count = 0;
    list->error = GC_MOVE_ERROR_NONE;
}

void gc_move_list_destroy(GCMoveList *list) {
    free(list->data);
    list->data = NULL;
    list->count = 0;
    list->capacity = 0;
    list->error = GC_MOVE_ERROR_NONE;
}

int gc_move_list_reserve(GCMoveList *list, size_t required) {
    if (required <= list->capacity) {
        return 1;
    }
    size_t new_cap = list->capacity ? list->capacity : 64;
    while (new_cap < required) {
        if (new_cap > (size_t)-1 / 2) {
            list->error = GC_MOVE_ERROR_OVERFLOW;
            return 0;
        }
        new_cap *= 2;
    }
    if (new_cap > (size_t)-1 / sizeof(GCPackedAction)) {
        list->error = GC_MOVE_ERROR_OVERFLOW;
        return 0;
    }
    GCPackedAction *grown =
        (GCPackedAction *)realloc(list->data, new_cap * sizeof(GCPackedAction));
    if (grown == NULL) {
        list->error = GC_MOVE_ERROR_ALLOC;
        return 0;
    }
    list->data = grown;
    list->capacity = new_cap;
    return 1;
}

int gc_move_list_append(GCMoveList *list, GCPackedAction action) {
    if (!gc_move_list_reserve(list, list->count + 1)) {
        return 0;
    }
    list->data[list->count++] = action;
    return 1;
}

/* ---------------------------------------------------------- move generation */

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

static int gc_append_board_move(GCMoveList *out, GCSquare to, GCSquare from,
                                GCTypeIndex base) {
    return gc_move_list_append(out, GC_ACTION_BOARD(to, from, base));
}

static int gc_expand_promotion(const GCRules *rules, GCPosition *pos,
                               GCMoveList *out, GCSquare to, GCSquare from) {
    uint8_t side = pos->side_to_move;
    const GCPiece *moved = &pos->board[from];
    GCTypeIndex base = moved->base_type;
    if (!rules->is_promotable[base] || moved->promoted) {
        return gc_append_board_move(out, to, from, base);
    }
    if (!gc_promo_pair_exists(rules, base, side, from, to)) {
        return gc_append_board_move(out, to, from, base);
    }
    uint64_t alive = rules->alive_promo[base][side][to];
    int forced = gc_promo_forced(rules, base, side, to);
    if (!forced && !gc_append_board_move(out, to, from, base)) {
        return 0;
    }
    uint8_t t;
    for (t = 0; t < rules->promo_target_count[base]; t++) {
        GCTypeIndex target = rules->promo_targets[base][t];
        if ((alive >> target) & 1u) {
            if (!gc_move_list_append(
                    out, GC_ACTION_PROMOTED(to, from, target, base))) {
                return 0;
            }
        }
    }
    return 1;
}

int gc_pseudo_actions(const GCRules *rules, GCPosition *pos, GCMoveList *out) {
    gc_move_list_clear(out);
    uint8_t side = pos->side_to_move;
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
                if (!gc_expand_promotion(rules, pos, out, to, sq)) {
                    return 0;
                }
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
                            if (!gc_expand_promotion(rules, pos, out, to, sq)) {
                                return 0;
                            }
                        }
                        break;
                    }
                    if (!gc_expand_promotion(rules, pos, out, to, sq)) {
                        return 0;
                    }
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
                if (!gc_move_list_append(out, GC_ACTION_DROP(to, type))) {
                    return 0;
                }
            }
        }
    }
    return 1;
}

int gc_legal_filter(const GCRules *rules, GCPosition *pos,
                    const GCMoveList *pseudo, GCMoveList *legal) {
    gc_move_list_clear(legal);
    uint8_t side = pos->side_to_move;
    size_t i;
    for (i = 0; i < pseudo->count; i++) {
        GCPackedAction action = pseudo->data[i];
        GCUndo undo;
        int status = gc_make_move(pos, rules, action, &undo);
        if (status != GC_STATUS_OK) {
            /* A trusted make failure for a move produced by the native pseudo
             * generator is a kernel/invariant/capacity error, not an ordinary
             * illegal move: propagate it instead of silently skipping. */
            legal->error = GC_MOVE_ERROR_TRUSTED_MAKE;
            legal->trusted_status = status;
            legal->failed_action = action;
            return 0;
        }
        GCSquare anchor = gc_find_anchor(rules, pos, side);
        int legal_move = anchor != GC_NO_SQUARE &&
                         !gc_is_square_attacked(rules, pos, anchor,
                                                1 - side);
        gc_unmake_move(pos, rules, &undo);
        if (legal_move && !gc_move_list_append(legal, action)) {
            return 0;
        }
    }
    return 1;
}

int gc_legal_actions(const GCRules *rules, GCPosition *pos, GCMoveList *out) {
    GCMoveList pseudo;
    gc_move_list_init(&pseudo);
    int ok = gc_pseudo_actions(rules, pos, &pseudo);
    if (ok) {
        ok = gc_legal_filter(rules, pos, &pseudo, out);
    } else {
        out->error = pseudo.error;
    }
    gc_move_list_destroy(&pseudo);
    return ok;
}
