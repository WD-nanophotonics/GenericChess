#include "native_semantic_state.h"

#include <string.h>

static void gc_semantic_aux_default(GCSemAuxValue *out,
                                    const GCSemAuxSlot *slot) {
    memset(out, 0, sizeof(*out));
    out->kind = slot->value_kind;
    if (slot->initial_kind == 1) {
        out->has_value = 1;
        out->bool_value = slot->initial_int;
    } else if (slot->initial_kind == 2) {
        out->has_value = 1;
        out->square = (uint16_t)(slot->initial_rank * 16u + slot->initial_file);
    }
}

int gc_semantic_position_pack(GCSemanticPosition *pos,
                              const GCSemanticRules *rules,
                              const GCSemanticBoardPayload *payload) {
    if (pos == NULL || rules == NULL || payload == NULL ||
        payload->side_to_move > 1 || payload->ply > rules->max_ply) {
        return 0;
    }
    memset(pos, 0, sizeof(*pos));
    pos->side_to_move = payload->side_to_move;
    pos->ply = payload->ply;
    memcpy(pos->board, payload->board, sizeof(GCPiece) *
           (size_t)(rules->board_size * rules->board_size));
    memcpy(pos->hand_counts, payload->hand_counts, sizeof(pos->hand_counts));
    for (uint16_t sq = 0; sq < (uint16_t)(rules->board_size * rules->board_size); sq++) {
        const GCPiece *piece = &pos->board[sq];
        if (!piece->occupied) continue;
        if (piece->owner > 1 || piece->base_type >= rules->type_count ||
            piece->current_type >= rules->type_count || piece->promoted > 1) {
            return 0;
        }
    }
    for (uint8_t slot_i = 0; slot_i < rules->aux_slot_count; slot_i++) {
        const GCSemAuxSlot *slot = &rules->aux_slots[slot_i];
        gc_semantic_aux_default(&pos->aux[slot_i][0], slot);
        if (slot->scope == 1) {
            gc_semantic_aux_default(&pos->aux[slot_i][1], slot);
            gc_semantic_aux_default(&pos->aux[slot_i][2], slot);
        }
    }
    return 1;
}
