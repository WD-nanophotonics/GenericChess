#include "native_rules.h"

#include <stdlib.h>
#include <string.h>

static uint64_t gc_splitmix64(uint64_t *state) {
    uint64_t z = (*state += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}

static void gc_hash_init(GCRules *rules) {
    uint64_t state = 0x243F6A8885A308D3ull;
    size_t i;
    for (i = 0; i < 64 && rules->fingerprint[i]; i++) {
        state ^= ((uint64_t)rules->fingerprint[i]) << ((i % 8) * 8);
        state ^= state >> 33;
        state *= 0xFF51AFD7ED558CCDull;
    }
    int stream, owner, sq, type, slot;
    for (stream = 0; stream < 2; stream++) {
        for (owner = 0; owner < 2; owner++) {
            for (sq = 0; sq < GC_MAX_SQUARES; sq++) {
                rules->piece_owner_square_hash[stream][owner][sq] =
                    gc_splitmix64(&state);
            }
            for (sq = 0; sq < GC_MAX_SQUARES; sq++) {
                rules->piece_promoted_hash[stream][sq] = gc_splitmix64(&state);
            }
            for (type = 0; type < GC_MAX_TYPES; type++) {
                for (slot = 0; slot < GC_MAX_HAND; slot++) {
                    rules->hand_piece_hash[stream][owner][type][slot] =
                        gc_splitmix64(&state);
                }
            }
            rules->side_hash[stream][owner] = gc_splitmix64(&state);
        }
        for (sq = 0; sq < GC_MAX_SQUARES; sq++) {
            for (type = 0; type < GC_MAX_TYPES; type++) {
                rules->piece_base_hash[stream][sq][type] =
                    gc_splitmix64(&state);
                rules->piece_current_hash[stream][sq][type] =
                    gc_splitmix64(&state);
            }
        }
    }
}

GCRules *gc_rules_compile(const GCCompiledPayload *payload) {
    GCRules *rules = (GCRules *)calloc(1, sizeof(GCRules));
    if (rules == NULL) {
        return NULL;
    }
    memcpy(rules->fingerprint, payload->fingerprint, 65);
    rules->width = (uint8_t)payload->width;
    rules->height = (uint8_t)payload->height;
    rules->squares = (uint16_t)(payload->width * payload->height);
    rules->type_count = (uint8_t)payload->type_count;
    rules->repetition_limit = (uint8_t)payload->repetition_limit;
    rules->max_ply = (uint16_t)payload->max_ply;

    int t, owner, atom;
    for (t = 0; t < payload->type_count; t++) {
        rules->is_anchor[t] = payload->is_anchor[t];
        rules->is_promotable[t] = payload->is_promotable[t];
        rules->atom_count[t] = payload->atom_count[t];
        for (atom = 0; atom < payload->atom_count[t]; atom++) {
            rules->atoms[t][atom] = payload->atoms[t][atom];
        }
        rules->promo_target_count[t] = payload->promo_target_count[t];
        for (atom = 0; atom < payload->promo_target_count[t]; atom++) {
            rules->promo_targets[t][atom] = payload->promo_targets[t][atom];
        }
        for (owner = 0; owner < 2; owner++) {
            uint32_t count = payload->promo_pair_count[t][owner];
            rules->promo_pair_count[t][owner] = count;
            if (count > 0) {
                rules->promo_pairs[t][owner] = (uint32_t *)malloc(
                    count * sizeof(uint32_t));
                if (rules->promo_pairs[t][owner] == NULL) {
                    gc_rules_free(rules);
                    return NULL;
                }
                memcpy(rules->promo_pairs[t][owner], payload->promo_pairs[t][owner],
                       count * sizeof(uint32_t));
            }
            memcpy(rules->promo_forced[t][owner], payload->promo_forced[t][owner],
                   sizeof(uint64_t) * 4);
            memcpy(rules->alive_promo[t][owner], payload->alive_promo[t][owner],
                   sizeof(uint64_t) * GC_MAX_SQUARES);
            memcpy(rules->drop_mask[t][owner], payload->drop_mask[t][owner],
                   sizeof(uint64_t) * 4);
        }
    }
    gc_hash_init(rules);
    return rules;
}

void gc_rules_free(GCRules *rules) {
    if (rules == NULL) {
        return;
    }
    int t, owner;
    for (t = 0; t < GC_MAX_TYPES; t++) {
        for (owner = 0; owner < 2; owner++) {
            free(rules->promo_pairs[t][owner]);
        }
    }
    free(rules);
}

void gc_payload_free_pairs(GCCompiledPayload *payload) {
    int t, owner;
    for (t = 0; t < GC_MAX_TYPES; t++) {
        for (owner = 0; owner < 2; owner++) {
            free(payload->promo_pairs[t][owner]);
            payload->promo_pairs[t][owner] = NULL;
        }
    }
}
