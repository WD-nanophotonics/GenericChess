#ifndef GENERIC_CHESS_NATIVE_MOVEGEN_H
#define GENERIC_CHESS_NATIVE_MOVEGEN_H

#include "native_types.h"

int gc_pseudo_actions(GCRules *rules, GCPosition *pos, GCPackedAction *out,
                      int cap);

int gc_legal_actions(GCRules *rules, GCPosition *pos, GCPackedAction *out,
                     int cap);

#endif /* GENERIC_CHESS_NATIVE_MOVEGEN_H */
