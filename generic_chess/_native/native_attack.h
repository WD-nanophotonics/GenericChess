#ifndef GENERIC_CHESS_NATIVE_ATTACK_H
#define GENERIC_CHESS_NATIVE_ATTACK_H

#include "native_types.h"

GCSquare gc_find_anchor(const GCRules *rules, const GCPosition *pos,
                        uint8_t owner);

/* Matches Python pseudo-attack semantics: pinned pieces still attack, ray
 * paths stop at the first occupied square (which itself is attacked), and
 * enemy anchors are attacked but not capturable. */
bool gc_is_square_attacked(const GCRules *rules, const GCPosition *pos,
                           GCSquare square, uint8_t by_owner);

#endif /* GENERIC_CHESS_NATIVE_ATTACK_H */
