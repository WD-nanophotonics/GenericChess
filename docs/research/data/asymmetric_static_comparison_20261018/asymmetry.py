"""Descriptive owner-asymmetry evidence for the six frozen generated rules.

Reads the frozen rules.json only; produces no new game outcomes.
"""
from pathlib import Path
from collections import defaultdict
import json

from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.core.movement import LeapAtom

D = Path('.local_agent/asymmetric-static-20261018')
RULES = json.loads((D / 'rules.json').read_bytes())


def atom_key(atom):
    if isinstance(atom, LeapAtom):
        return 'leap', tuple(atom.offset)
    return 'ray', tuple(atom.direction), atom.max_steps


def negate(key):
    if key[0] == 'leap':
        return 'leap', (-key[1][0], -key[1][1])
    return 'ray', (-key[1][0], -key[1][1]), key[2]


def mirror_lr(key):
    if key[0] == 'leap':
        return 'leap', (-key[1][0], key[1][1])
    return 'ray', (-key[1][0], key[1][1]), key[2]


rows = []
for seed in sorted(RULES['rules'], key=int):
    rule = ruleset_from_dict(json.loads(json.dumps(RULES['rules'][seed])))
    c = compile_legacy_ruleset_for_semantic_execution(rule)
    n = c.board_size
    counts = defaultdict(lambda: defaultdict(int))
    mobility = {0: 0, 1: 0}
    for row, cells in enumerate(rule.initial_position):
        for col, piece in enumerate(cells):
            if piece is None:
                continue
            idx = row * n + col
            counts[piece.owner][piece.base_type_id] += 1
            tiles = c.leap_targets[piece.base_type_id][piece.owner][idx]
            rays = c.ray_paths[piece.base_type_id][piece.owner][idx]
            mobility[piece.owner] += (sum(len(x) for x in tiles)
                                      + sum(len(x) for x in rays))
    types = {}
    fwd = back = 0
    for tid, t in c.types_by_id.items():
        keys = [atom_key(a) for a in t.movement_atoms]
        ks = set(keys)
        if tid != 'K':
            for k in keys:
                dr = k[1][1]
                fwd += dr > 0
                back += dr < 0
        types[tid] = dict(
            atoms=len(keys),
            left_right_symmetric=all(mirror_lr(k) in ks for k in ks),
            rotation_180_invariant=all(negate(k) in ks for k in ks),
            atoms_repr=[list(k) for k in keys])
    # Layout symmetry: is the owner-1 half the 180-degree rotation of owner 0?
    layout_rot180 = True
    for row in range(n):
        for col in range(n):
            a = rule.initial_position[row][col]
            b = rule.initial_position[n - 1 - row][n - 1 - col]
            ok = (a is None and b is None) or (
                a is not None and b is not None
                and a.base_type_id == b.base_type_id and a.owner != b.owner)
            layout_rot180 = layout_rot180 and ok
    rows.append(dict(
        rule=int(seed),
        initial_pieces={str(o): dict(counts[o]) for o in (0, 1)},
        initial_total={str(o): sum(counts[o].values()) for o in (0, 1)},
        initial_pseudo_targets={str(o): mobility[o] for o in (0, 1)},
        nonanchor_forward_atoms=fwd, nonanchor_backward_atoms=back,
        layout_rot180_symmetric=layout_rot180,
        types=types,
        owner_mirror_image=all(v['rotation_180_invariant'] for v in types.values()),
        left_right_symmetric=all(v['left_right_symmetric'] for v in types.values())))

out = dict(
    rules=rows,
    any_owner_mirror_image=any(r['owner_mirror_image'] for r in rows),
    all_owner_mirror_image=all(r['owner_mirror_image'] for r in rows),
    any_left_right_symmetric=any(r['left_right_symmetric'] for r in rows),
    scope='Atom sets are owner-relative; rotation_180_invariant means the two '
          'owners have mirror-image move sets (owner-symmetric rule). Movement '
          'symmetry=none applies no left-right mirroring. Pseudo-target counts '
          'are on the initial position with no attack/anchor filtering.')
(D / 'asymmetry.json').write_text(json.dumps(out, indent=1, sort_keys=True))
print(json.dumps(out, indent=1, sort_keys=True))
