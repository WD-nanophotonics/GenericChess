#include "native_semantic_state.h"

#include <string.h>

static void gc_semantic_aux_default(GCSemAuxValue *out,
                                    const GCSemAuxSlot *slot,
                                    uint8_t board_size) {
    memset(out, 0, sizeof(*out));
    out->kind = slot->value_kind;
    if (slot->initial_kind == 1) {
        out->has_value = 1;
        out->bool_value = slot->initial_int;
    } else if (slot->initial_kind == 2) {
        out->has_value = 1;
        out->square = (uint16_t)(slot->initial_rank * board_size + slot->initial_file);
    }
}

int gc_semantic_position_pack(GCSemanticPosition *pos,
                              const GCSemanticRules *rules,
                              const GCSemanticBoardPayload *payload) {
    if (pos == NULL || rules == NULL || payload == NULL ||
        payload->side_to_move > 1 || payload->ply > rules->max_ply) {
        return 0;
    }
    GCSemAuxValue provided[GC_SEM_MAX_AUX_SLOTS][3];
    memcpy(provided, payload->aux, sizeof(provided));
    memset(pos, 0, sizeof(*pos));
    pos->side_to_move = payload->side_to_move;
    pos->ply = payload->ply;
    memcpy(pos->board, payload->board, sizeof(GCPiece) *
           (size_t)(rules->board_size * rules->board_size));
    memcpy(pos->hand_counts, payload->hand_counts, sizeof(pos->hand_counts));
    if (payload->history_len > GC_MAX_PLY + 1) return 0;
    pos->history_len = payload->history_len;
    memcpy(pos->history_lo, payload->history_lo, sizeof(pos->history_lo));
    memcpy(pos->history_hi, payload->history_hi, sizeof(pos->history_hi));
    for (uint16_t sq = 0; sq < (uint16_t)(rules->board_size * rules->board_size); sq++) {
        const GCPiece *piece = &pos->board[sq];
        if (!piece->occupied) continue;
        if (piece->owner > 1 || piece->base_type >= rules->type_count ||
            piece->current_type >= rules->type_count || piece->promoted > 1) {
            return 0;
        }
        const GCSemType *base_meta = &rules->types[piece->base_type];
        if (!piece->promoted) {
            if (piece->current_type != piece->base_type) return 0;
        } else {
            if (base_meta->is_anchor || !base_meta->is_promotable) return 0;
            int allowed = 0;
            for (uint8_t i = 0; i < base_meta->promo_target_count; i++)
                if (base_meta->promo_targets[i] == piece->current_type) { allowed = 1; break; }
            if (!allowed) return 0;
        }
    }
    for (uint8_t slot_i = 0; slot_i < rules->aux_slot_count; slot_i++) {
        const GCSemAuxSlot *slot = &rules->aux_slots[slot_i];
        gc_semantic_aux_default(&pos->aux[slot_i][0], slot, rules->board_size);
        if (slot->scope == 1) {
            gc_semantic_aux_default(&pos->aux[slot_i][1], slot, rules->board_size);
            gc_semantic_aux_default(&pos->aux[slot_i][2], slot, rules->board_size);
        }
        for (uint8_t owner = 0; owner < 3; owner++)
            if (provided[slot_i][owner].has_value)
                pos->aux[slot_i][owner] = provided[slot_i][owner];
    }
    return 1;
}
