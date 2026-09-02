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

/* Apply one exact semantic action to a copied position.  This first validates
 * the action's pattern/geometry/target binding, then executes the declared
 * board, hand, type and auxiliary effects in order.  Returns 1 on success;
 * the destination is untouched on failure. */
int gc_semantic_runtime_make_checked(GCSemanticPosition *child,
                                      const GCSemanticRules *rules,
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

#endif
