#ifndef GENERIC_CHESS_NATIVE_RUNTIME_H
#define GENERIC_CHESS_NATIVE_RUNTIME_H

#include "native_semantic_key.h"

typedef struct {
    unsigned long long candidate_count;
    unsigned long long s3_trial_count;
    unsigned long long s4_count;
    unsigned long long nested_reply_count;
    unsigned long long child_canonical_key_computations;
    unsigned long long history_appends;
    unsigned long long attack_check_calls;
} GCSemanticRuntimeAudit;

void gc_semantic_runtime_audit_start(GCSemanticRuntimeAudit *audit);
void gc_semantic_runtime_audit_stop(void);
void gc_semantic_runtime_history_mode_start(void);
void gc_semantic_runtime_history_mode_stop(void);

/* Shared automatic adjudication authority: 0 inactive, 1 PENDING,
 * 2 configured outcome, -1 incomplete/unsupported authoritative history. */
int gc_semantic_runtime_automatic_status(const GCSemanticRules *,
    const GCSemanticPosition *);

/* Apply one exact semantic action to a copied position.  This first validates
 * the action's pattern/geometry/target binding, then executes the declared
 * board, hand, type and auxiliary effects in order.  Returns 1 on success;
 * the destination is untouched on failure. */
int gc_semantic_runtime_make_checked(GCSemanticPosition *child,
                                      const GCSemanticRules *rules,
                                      const GCSemanticPosition *parent,
                                      uint64_t action);

/* Internal status: 1 success, 0 rule/input/capacity rejection, -1 child
 * identity failure (including nested reply). Boolean callers stay 0/1. */
int gc_semantic_runtime_make_checked_status(GCSemanticPosition *,
    const GCSemanticRules *, const GCSemanticPosition *, uint64_t);

/* Discarded scoring/feature legality only; preserves postconditions and parent history.
 * Returns 1/0/-1. Never use this child for search, TT, cache or terminal checks. */
int gc_semantic_runtime_make_material_view_status(GCSemanticPosition *,
    const GCSemanticRules *, const GCSemanticPosition *, uint64_t);

/* Internal availability keeps nested execution failures distinct from no move. */
int gc_semantic_runtime_probe_action_status(const GCSemanticRules *,
    const GCSemanticPosition *, uint64_t);

/* Readonly S0-S4 action existence probe; no child identity/history output. */
int gc_semantic_runtime_probe_action(const GCSemanticRules *rules,
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

/* Scalar-equivalent S0/S1 attack map, not legal mobility. */
void gc_semantic_runtime_attacked_squares(const GCSemanticRules *rules,
                                         const GCSemanticPosition *position,
                                         uint8_t by_owner,
                                         uint8_t out[GC_MAX_SQUARES]);

typedef struct {
    uint8_t outcome;
    uint8_t has_weighted_score;
    int64_t weighted_score;
} GCSemanticDeclarationAssessment;

/* Assess a C-owned declaration against a packed semantic position.  The
 * caller supplies the declaration ID; actor binding is the position's side
 * to move, matching the public Core declaration contract. */
int gc_semantic_runtime_assess_declaration(
    const GCSemanticRules *rules,
    const GCSemanticPosition *position,
    const char *declaration_id,
    GCSemanticDeclarationAssessment *out);

typedef struct {
    GCSemanticPosition saved;
} GCSemanticUndo;

int gc_semantic_runtime_make_trusted(GCSemanticPosition *position,
                                     const GCSemanticRules *rules,
                                     uint64_t action,
                                     GCSemanticUndo *undo);
void gc_semantic_runtime_unmake(GCSemanticPosition *position,
                                const GCSemanticUndo *undo);

/* Copy all fixed fields and the complete live history, without unused tail. */
void gc_semantic_runtime_copy_live_position(GCSemanticPosition *,const GCSemanticPosition *);

#endif
