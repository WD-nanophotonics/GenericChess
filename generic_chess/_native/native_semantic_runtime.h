#ifndef GENERIC_CHESS_NATIVE_RUNTIME_H
#define GENERIC_CHESS_NATIVE_RUNTIME_H

#include "native_semantic_key.h"

/* Apply one exact semantic action to a copied position.  This first validates
 * the action's pattern/geometry/target binding, then executes the declared
 * board, hand, type and auxiliary effects in order.  Returns 1 on success;
 * the destination is untouched on failure. */
int gc_semantic_runtime_make_checked(GCSemanticPosition *child,
                                     const GCSemanticRules *rules,
                                     const GCSemanticPosition *parent,
                                     uint64_t action);

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
