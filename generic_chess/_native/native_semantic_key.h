#ifndef GENERIC_CHESS_NATIVE_SEMANTIC_KEY_H
#define GENERIC_CHESS_NATIVE_SEMANTIC_KEY_H

#include "native_semantic_state.h"

/* Build the frozen Python semantic_position_key canonical JSON in C and
 * return its SHA-256 hex digest.  Returns 1 on success, 0 on unsupported or
 * malformed state. */
int gc_semantic_position_key_digest(const GCSemanticRules *rules,
                                    const GCSemanticPosition *position,
                                    char out_hex[65]);

/* H18A candidate: stream the exact canonical bytes directly into SHA-256. */
int gc_semantic_position_key_digest_raw(const GCSemanticRules *rules,
                                        const GCSemanticPosition *position,
                                        uint8_t digest[32]);

#endif
