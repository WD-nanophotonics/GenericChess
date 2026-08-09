#ifndef GENERIC_CHESS_NATIVE_SEMANTIC_STATE_H
#define GENERIC_CHESS_NATIVE_SEMANTIC_STATE_H

#include "native_semantic_rules.h"

/* Deliberately independent of legacy GCPosition.  This is the dynamic
 * semantic-runtime state; no legacy movegen/hash/search structure aliases it. */
typedef struct {
    uint8_t kind; /* 0 bool, 1 square-or-none */
    uint8_t has_value;
    int32_t bool_value;
    uint16_t square;
} GCSemAuxValue;

typedef struct {
    char rules_fingerprint[65];
    GCPiece board[GC_MAX_SQUARES];
    uint16_t hand_counts[2][GC_MAX_TYPES];
    uint8_t side_to_move;
    uint16_t ply;
    /* slot index, then global(-1 => 0) / owner0 / owner1. */
    GCSemAuxValue aux[GC_SEM_MAX_AUX_SLOTS][3];
    /* Full SHA-256 history is authoritative; lo/hi remain an explicit
     * compatibility projection for the older occurrence helper. */
    uint64_t history_lo[GC_MAX_PLY + 1];
    uint64_t history_hi[GC_MAX_PLY + 1];
    uint64_t history_digest[GC_MAX_PLY + 1][4];
    uint16_t history_len;
    uint8_t history_exact;
} GCSemanticPosition;

typedef struct {
    uint8_t side_to_move;
    uint16_t ply;
    GCPiece board[GC_MAX_SQUARES];
    uint16_t hand_counts[2][GC_MAX_TYPES];
    GCSemAuxValue aux[GC_SEM_MAX_AUX_SLOTS][3];
    uint64_t history_lo[GC_MAX_PLY + 1];
    uint64_t history_hi[GC_MAX_PLY + 1];
    uint64_t history_digest[GC_MAX_PLY + 1][4];
    uint16_t history_len;
    uint8_t history_exact;
} GCSemanticBoardPayload;

int gc_semantic_position_pack(GCSemanticPosition *pos,
                              const GCSemanticRules *rules,
                              const GCSemanticBoardPayload *payload);

int gc_semantic_position_matches_rules(const GCSemanticPosition *pos,
                                       const GCSemanticRules *rules);

#endif
