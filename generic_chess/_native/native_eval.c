#include "native_eval.h"

#include <stdlib.h>
#include <string.h>

GCEvaluationTables *gc_eval_compile(const GCEvalPayload *payload) {
    GCEvaluationTables *eval = (GCEvaluationTables *)calloc(1, sizeof(GCEvaluationTables));
    if (eval == NULL) {
        return NULL;
    }
    memcpy(eval->board_value, payload->board_value,
           sizeof(int32_t) * GC_MAX_TYPES);
    memcpy(eval->hand_value, payload->hand_value,
           sizeof(int32_t) * GC_MAX_TYPES);
    memcpy(eval->promotion_gain, payload->promotion_gain,
           sizeof(int32_t) * GC_MAX_TYPES);
    eval->mate_score = payload->mate_score;
    eval->mate_threshold = payload->mate_threshold;
    eval->max_static_eval = payload->max_static_eval;
    memcpy(eval->config_hash, payload->config_hash, 65);
    memcpy(eval->evaluator_version, payload->evaluator_version, 65);
    (void)payload->type_count;
    return eval;
}

void gc_eval_free(GCEvaluationTables *eval) {
    free(eval);
}

int32_t gc_evaluate_material(const GCRules *rules,
                             const GCEvaluationTables *eval,
                             const GCPosition *pos) {
    int64_t score = 0;
    GCSquare sq;
    for (sq = 0; sq < rules->squares; sq++) {
        const GCPiece *piece = &pos->board[sq];
        if (!piece->occupied) {
            continue;
        }
        int32_t v = eval->board_value[piece->current_type];
        score += (piece->owner == 0) ? v : -v;
    }
    int owner, type;
    for (owner = 0; owner < 2; owner++) {
        for (type = 0; type < rules->type_count; type++) {
            uint16_t count = pos->hand_counts[owner][type];
            if (count == 0) {
                continue;
            }
            int64_t v = eval->hand_value[type];
            score += (owner == 0) ? count * v : -(count * v);
        }
    }
    if (pos->side_to_move == 1) {
        score = -score;
    }
    if (score > eval->max_static_eval) {
        score = eval->max_static_eval;
    } else if (score < -eval->max_static_eval) {
        score = -eval->max_static_eval;
    }
    return (int32_t)score;
}
