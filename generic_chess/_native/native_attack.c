#include "native_attack.h"

#include <stdint.h>

static int16_t gc_abs_direction(const GCRules *rules, const GCAtom *atom,
                                uint8_t owner, int16_t *df, int16_t *dr) {
    (void)rules;
    if (owner == 0) {
        *df = atom->vec.df;
        *dr = atom->vec.dr;
    } else {
        *df = (int16_t)(-atom->vec.df);
        *dr = (int16_t)(-atom->vec.dr);
    }
    return 1;
}

GCSquare gc_find_anchor(const GCRules *rules, const GCPosition *pos,
                        uint8_t owner) {
    GCSquare sq;
    for (sq = 0; sq < rules->squares; sq++) {
        if (pos->board[sq].occupied && pos->board[sq].owner == owner &&
            rules->is_anchor[pos->board[sq].current_type]) {
            return sq;
        }
    }
    return GC_NO_SQUARE;
}

bool gc_is_square_attacked(const GCRules *rules, const GCPosition *pos,
                           GCSquare square, uint8_t by_owner) {
    GCSquare sq;
    for (sq = 0; sq < rules->squares; sq++) {
        const GCPiece *piece = &pos->board[sq];
        if (!piece->occupied || piece->owner != by_owner) {
            continue;
        }
        const GCAtom *atoms = rules->atoms[piece->current_type];
        uint8_t atom_count = rules->atom_count[piece->current_type];
        uint8_t ai;
        for (ai = 0; ai < atom_count; ai++) {
            const GCAtom *atom = &atoms[ai];
            int16_t df, dr;
            gc_abs_direction(rules, atom, by_owner, &df, &dr);
            if (atom->kind == 0) { /* leap */
                int16_t nf = (int16_t)((int16_t)(sq % rules->width) + df);
                int16_t nr = (int16_t)((int16_t)(sq / rules->width) + dr);
                if (nf >= 0 && nf < rules->width && nr >= 0 &&
                    nr < rules->height &&
                    (GCSquare)(nr * rules->width + nf) == square) {
                    return true;
                }
            } else { /* ray */
                GCSquare cur = sq;
                uint8_t steps = 0;
                while (atom->max_steps == 0 || steps < atom->max_steps) {
                    int16_t nf = (int16_t)((int16_t)(cur % rules->width) + df);
                    int16_t nr = (int16_t)((int16_t)(cur / rules->width) + dr);
                    if (nf < 0 || nf >= rules->width || nr < 0 ||
                        nr >= rules->height) {
                        break;
                    }
                    GCSquare nxt = (GCSquare)(nr * rules->width + nf);
                    if (nxt == square) {
                        return true;
                    }
                    if (pos->board[nxt].occupied) {
                        break;
                    }
                    cur = nxt;
                    steps++;
                }
            }
        }
    }
    return false;
}
