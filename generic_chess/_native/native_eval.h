#ifndef GENERIC_CHESS_NATIVE_EVAL_H
#define GENERIC_CHESS_NATIVE_EVAL_H

#include "native_types.h"

/* Native-compatible material evaluation tables.
 *
 * The values are produced once on the Python side from the rule-derived
 * ``RuleSetEvaluationProfile`` (board value by current type, hand value by
 * base type); the C kernel never re-derives piece values. */
typedef struct {
    int32_t board_value[GC_MAX_TYPES];
    int32_t hand_value[GC_MAX_TYPES];
    int32_t promotion_gain[GC_MAX_TYPES];
    int32_t mate_score;
    int32_t mate_threshold;
    int32_t max_static_eval;
    char config_hash[65];
    char evaluator_version[65];
} GCEvaluationTables;

/* Plain payload filled by the Python module from a serialized dict. */
typedef struct {
    int type_count;
    int32_t board_value[GC_MAX_TYPES];
    int32_t hand_value[GC_MAX_TYPES];
    int32_t promotion_gain[GC_MAX_TYPES];
    int32_t mate_score;
    int32_t mate_threshold;
    int32_t max_static_eval;
    char config_hash[65];
    char evaluator_version[65];
} GCEvalPayload;

/* Allocate and copy the payload into an owned table.  NULL on failure. */
GCEvaluationTables *gc_eval_compile(const GCEvalPayload *payload);

void gc_eval_free(GCEvaluationTables *eval);

/* Material score from the current side-to-move perspective, clamped to
 * [-max_static_eval, max_static_eval].  Anchors carry no material value. */
int32_t gc_evaluate_material(const GCRules *rules,
                             const GCEvaluationTables *eval,
                             const GCPosition *pos);

#endif /* GENERIC_CHESS_NATIVE_EVAL_H */
