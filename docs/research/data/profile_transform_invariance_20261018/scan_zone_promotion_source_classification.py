"""Why does an in-zone paid piece have no legal promotion in that position?

DEEPSEEK_AUX private probe, 2026-10-18, session
``3d8dc073-5fcc-456e-933c-a7b6646296e5``.  Stage 8 counted in-zone bonus
payments that coincide with a legal promotion action.  The zone/promotion
disjointness artifact then showed, per seed, whether the zone meets any
promotion source at all.  Neither tells us how the remaining mass splits for
the pieces that were actually paid, which is what decides whether the
non-coincidence is fixed by the compiled rules or by the played position.

Replay only, of the same six stored game files as Stage 8.  No search, no new
games, no evaluator edit, no rate contrast between zone arms.  The endpoint is
pre-written in ``plan_zone_promotion_source_classification.json`` (with one
amendment recorded before the run, derived from reading movegen, not results).
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.actions import BoardMove, DropMove  # noqa: E402
from generic_chess.core.coordinates import Square, index_to_square, square_to_index  # noqa: E402
from generic_chess.core.movegen import _expanded_pseudo_actions, legal_actions  # noqa: E402
from generic_chess.core.movement import LeapAtom  # noqa: E402
from generic_chess.core.transition import apply_action, initial_state, legal_successors  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

SESSION = "3d8dc073-5fcc-456e-933c-a7b6646296e5"
GAMES_DIR = ROOT / ".local_agent" / "hand-utility-games-20261018"
FILES = [
    "results_hand_term_match_served-blind_d2_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d2_n20000_s71-94.json",
    "results_hand_term_match_served-blind_d3_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d3_n20000_s71-94.json",
    "results_hand_term_match_served-served_d2_n20000_s59-70.json",
    "results_hand_term_match_served-served_d2_n20000_s71-94.json",
]

START_PLY = 8
MIN_START_ACTIONS = 6
_NAMESPACE = {"Square": Square, "BoardMove": BoardMove, "DropMove": DropMove}


def parse_move(text: str):
    expression = ast.parse(text, mode="eval")
    return eval(compile(expression, "<stored-move>", "eval"), {"__builtins__": {}}, _NAMESPACE)


def sample_start(compiled, seed: int):
    """Exactly the start-position walker of the stored-game generator path."""
    for offset in range(4):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 60:
            if state.terminal_status.is_terminal:
                break
            if state.ply_count >= START_PLY:
                children = legal_successors(state, compiled)
                if len(legal_actions(state, compiled)) >= MIN_START_ACTIONS:
                    if not any(child.terminal_status.is_terminal for _, child in children):
                        return state
            children = legal_successors(state, compiled)
            if not children:
                break
            _, state = rng.choice(children)
    return None


def zone_squares(evaluator, piece):
    """The evaluator's paid zone for this piece, or None when no zone applies."""
    base = piece.base_type_id
    if piece.promoted or base not in evaluator._profile.promotion_gain_by_type:
        return None
    if evaluator._profile.promotion_gain_by_type[base] <= 0:
        return None
    return evaluator._zones.get((base, piece.owner))


def pseudo_targets(state, compiled, idx: int, piece) -> list[Square]:
    """Pseudo-legal destinations of this piece alone, read from compiled tables.

    Mirrors ``movegen._piece_actions`` for one piece so that the idle side can be
    classified too (``legal_actions`` only ever yields the side to move).
    """
    n = compiled.board_size
    side = piece.owner
    tid = piece.current_type_id
    board = state.position.board
    atoms = compiled.types_by_id[tid].movement_atoms
    leap_row = compiled.leap_targets[tid][side][idx]
    ray_row = compiled.ray_paths[tid][side][idx]
    out: list[Square] = []
    for a_idx, atom in enumerate(atoms):
        if isinstance(atom, LeapAtom):
            for target in leap_row[a_idx]:
                occupant = board[square_to_index(target, n)]
                if occupant is None:
                    out.append(target)
                elif (
                    occupant.owner != side
                    and not compiled.types_by_id[occupant.current_type_id].is_anchor
                ):
                    out.append(target)
            continue
        for target in ray_row[a_idx]:
            occupant = board[square_to_index(target, n)]
            if occupant is None:
                out.append(target)
                continue
            if occupant.owner != side and not compiled.types_by_id[
                occupant.current_type_id
            ].is_anchor:
                out.append(target)
            break
    return out


def promotion_index(compiled, cache, base: int, side: int):
    """(from-squares, destinations-by-from) of the compiled promotion pairs.

    The cache key is the ruleset fingerprint, never ``id(compiled)``: each game
    regenerates its own compiled ruleset, the previous object is released, and a
    recycled ``id`` made a stale promotion table leak across seeds.  A first
    private run did exactly that (seed 77 lost two of its cases); its numbers
    were discarded, are recorded under ``defect_corrections`` and were never
    published.
    """
    key = (compiled.ruleset_fingerprint, base, side)
    if key not in cache:
        pairs = compiled.promotion_allowed[base][side]
        from_squares = {start for start, _ in pairs}
        dests: dict[Square, set[Square]] = {}
        for start, dest in pairs:
            dests.setdefault(start, set()).add(dest)
        cache[key] = (from_squares, dests)
    return cache[key]


def library_expansion(state, compiled):
    """The library's own pseudo-legal expansion, indexed by from-square.

    ``pseudo_targets`` above re-implements the geometry so that idle-side pieces
    (which ``legal_actions`` never yields) can be classified too.  Those two
    views must agree for the side to move; the per-position cross-check does
    exactly that and the run fails its done condition on any disagreement.
    """
    raw: dict[int, list[Square]] = {}
    promos: dict[int, list[Square]] = {}
    plains: dict[int, list[Square]] = {}
    for action in _expanded_pseudo_actions(state.position, compiled):
        if not isinstance(action, BoardMove):
            continue
        idx = square_to_index(action.from_square, compiled.board_size)
        raw.setdefault(idx, []).append(action.to_square)
        target = promos if action.promotion_target_id is not None else plains
        target.setdefault(idx, []).append(action.to_square)
    return raw, promos, plains


def classify(
    state,
    compiled,
    cache,
    idx,
    piece,
    contact_squares,
    legal_set,
    side_to_move,
    mover_promos,
    mover_plains,
):
    """Return (bucket, subclass) for one in-zone paid observation."""
    if idx in contact_squares:
        return "in_zone_contact", ""
    base = piece.base_type_id
    side = piece.owner
    from_squares, dests = promotion_index(compiled, cache, base, side)
    to_move = side == side_to_move
    # ``from_squares`` holds Square objects, not board indices; comparing the
    # integer index would always miss and silently send every observation to
    # the geometry bucket (a first run did exactly that, before publication).
    source = index_to_square(idx, compiled.board_size)
    if source not in from_squares:
        return "zone_geometry_no_source", ""
    targets = pseudo_targets(state, compiled, idx, piece)
    allowed = dests.get(source, set())
    pairs = [target for target in targets if target in allowed]
    if not pairs:
        if targets:
            return "no_reachable_allowed_destination", "moves_exist_but_none_is_an_allowed_promotion"
        return "no_reachable_allowed_destination", "no_legal_move_from_square"
    alive = False
    for target in pairs:
        to_idx = square_to_index(target, compiled.board_size)
        for tid in compiled.types_by_id[base].promotion_target_ids:
            if compiled.empty_mobility[tid][side][to_idx]:
                alive = True
                break
        if alive:
            break
    if not alive:
        return "dead_promotion_target", ""
    if to_move:
        # A promotion variant is pseudo-legal yet absent from legal_actions.
        # Separating the two causes matters: an illegal unpromoted sibling means
        # the whole move failed anchor safety (nothing promotion-specific), while
        # a legal sibling means the promoted type itself changed the verdict.
        if not set(pairs) & set(mover_promos.get(idx, ())):
            # Geometry and alive-target checks said a promotion exists, but the
            # library's own expansion produced none from this square.
            return "library_expansion_diverges", ""
        siblings = [BoardMove(source, target) for target in mover_plains.get(idx, ())]
        if any(move in legal_set for move in siblings):
            return "pseudo_promotion_filtered_by_legal_safety", "promotion_specific_legal_filter"
        forced = compiled.promotion_forced[base][side]
        if any(target in forced for target in pairs):
            # On a forced-promotion destination movegen never offers the
            # unpromoted sibling, so its absence is not evidence either way.
            return (
                "pseudo_promotion_filtered_by_legal_safety",
                "forced_square_all_variants_refuted",
            )
        return (
            "pseudo_promotion_filtered_by_legal_safety",
            "parent_move_refuted_by_anchor_safety",
        )
    return "would_promote_but_not_to_move", ""


def main() -> int:
    started = time.time()
    seen: set[tuple] = set()
    totals: Counter = Counter()
    subsets: Counter = Counter()
    per_seed: dict[int, Counter] = {}
    per_game: list[dict] = []
    problems: list[str] = []
    cache: dict = {}

    for name in FILES:
        payload = json.loads((GAMES_DIR / name).read_text(encoding="utf-8"))
        depth = payload["design"]["search"]["max_depth"]
        for game in payload["games"]:
            key = (game["seed"], depth, game["game_index"], tuple(game["moves"]))
            if key in seen:
                totals["games_deduplicated"] += 1
                continue
            seen.add(key)
            seed = game["seed"]
            compiled = generate_game(
                GeneratorConfig(seed=seed, board_size=4, setup_preset="classic_like")
            ).compiled_ruleset
            config = EvaluationConfig()
            evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
            state = sample_start(compiled, seed)
            if state is None:
                problems.append(f"no start position at seed {seed}")
                continue
            start_ply = state.ply_count
            counts: Counter = Counter()

            def scan(state) -> None:
                side_to_move = state.position.side_to_move
                actions = legal_actions(state, compiled)
                legal_set = set(actions)
                mover_raw, mover_promos, mover_plains = library_expansion(state, compiled)
                contact_squares: set[int] = set()
                for action in actions:
                    if isinstance(action, BoardMove) and action.promotion_target_id is not None:
                        contact_squares.add(
                            square_to_index(action.from_square, compiled.board_size)
                        )
                for idx, piece in enumerate(state.position.board):
                    if piece is None:
                        continue
                    zone = zone_squares(evaluator, piece)
                    if zone is None or idx not in zone:
                        continue
                    if piece.owner == side_to_move:
                        # The re-implemented geometry and the library expansion
                        # must agree for the side that actually moves.
                        mine = set(pseudo_targets(state, compiled, idx, piece))
                        theirs = set(mover_raw.get(idx, ()))
                        if mine != theirs:
                            problems.append(
                                f"seed {seed} depth {depth} game {game['game_index']} "
                                f"square {idx}: pseudo_targets {sorted(mine)} != library "
                                f"expansion {sorted(theirs)}"
                            )
                    bucket, subclass = classify(
                        state,
                        compiled,
                        cache,
                        idx,
                        piece,
                        contact_squares,
                        legal_set,
                        side_to_move,
                        mover_promos,
                        mover_plains,
                    )
                    if bucket == "library_expansion_diverges":
                        problems.append(
                            f"seed {seed} depth {depth} game {game['game_index']} "
                            f"square {idx}: promotion geometry+alive but no library variant"
                        )
                    counts["in_zone_paid_observations"] += 1
                    counts[bucket] += 1
                    counts[f"to_move_{bucket}" if piece.owner == side_to_move else f"idle_{bucket}"] += 1
                    if subclass:
                        counts[subclass] += 1
                    per_seed.setdefault(seed, Counter())[bucket] += 1
                counts["positions"] += 1

            scan(state)
            move_index = 0
            replay_error = None
            for text in game["moves"]:
                action = parse_move(text)
                try:
                    state = apply_action(state, action, compiled)
                except Exception as error:  # noqa: BLE001 - recorded, not swallowed
                    replay_error = f"{type(error).__name__}: {error}"
                    break
                move_index += 1
                scan(state)

            status = state.terminal_status
            replayed = {
                "status": status.status.value if status.is_terminal else "watchdog",
                "winner": status.winner if status.is_terminal else None,
                "plies": state.ply_count - start_ply,
            }
            stored = {"status": game["status"], "winner": game["winner"], "plies": game["plies"]}
            if replay_error is not None or replayed != stored:
                problems.append(
                    f"seed {seed} depth {depth} game {game['game_index']}: "
                    f"replay {replayed} != stored {stored} ({replay_error})"
                )
                continue

            totals.update(counts)
            totals["games_scanned"] += 1
            per_game.append(
                dict(
                    seed=seed,
                    depth=depth,
                    game_index=game["game_index"],
                    in_zone_paid_observations=counts["in_zone_paid_observations"],
                    in_zone_contact=counts["in_zone_contact"],
                    zone_geometry_no_source=counts["zone_geometry_no_source"],
                    no_reachable_allowed_destination=counts[
                        "no_reachable_allowed_destination"
                    ],
                    dead_promotion_target=counts["dead_promotion_target"],
                    pseudo_promotion_filtered_by_legal_safety=counts[
                        "pseudo_promotion_filtered_by_legal_safety"
                    ],
                    would_promote_but_not_to_move=counts["would_promote_but_not_to_move"],
                )
            )

    elapsed = time.time() - started
    n = totals["in_zone_paid_observations"]
    contact = totals["in_zone_contact"]
    moving_mass = (
        totals["to_move_zone_geometry_no_source"]
        + totals["to_move_no_reachable_allowed_destination"]
        + totals["to_move_dead_promotion_target"]
        + totals["to_move_pseudo_promotion_filtered_by_legal_safety"]
    )
    geometry = totals["to_move_zone_geometry_no_source"]
    destination_side = (
        totals["to_move_no_reachable_allowed_destination"]
        + totals["to_move_dead_promotion_target"]
    )
    if moving_mass == 0:
        decision = "no_missing_contact_mass_to_classify"
    elif geometry >= 0.5 * moving_mass:
        decision = "missing_contact_is_mostly_zone_geometry"
    elif destination_side >= 0.5 * moving_mass:
        decision = "missing_contact_is_mostly_destination_side"
    else:
        decision = "missing_contact_is_split_without_a_majority"

    payload = dict(
        role="DEEPSEEK_AUX",
        session=SESSION,
        question=(
            "When an in-zone paid promotable piece has no legal promotion action, is that "
            "because the square is no promotion source for its base type, because no allowed "
            "promotion destination is reachable, or because every promotion target is dead there?"
        ),
        plan="plan_zone_promotion_source_classification.json",
        design=dict(
            board_size=4,
            setup_preset="classic_like",
            no_new_search=True,
            no_new_games=True,
            replay_precondition="terminal status, winner and ply count must equal the stored values",
            deduplicate_by="(seed, depth, game_index, moves)",
            contact_definition="unchanged from Stage 8: in-zone paid square that is the from_square of a legal BoardMove with promotion_target_id not None",
            idle_side_note="the evaluator pays either owner; legal_actions only ever contains the side to move, so idle-side observations are tagged and reported apart",
        ),
        summary=dict(
            decision=decision,
            in_zone_paid_observations=n,
            in_zone_contact=contact,
            missing_contact_mass=n - contact,
            to_move_mass_used_by_the_decision_rule=moving_mass,
            to_move_zone_geometry_no_source=totals["to_move_zone_geometry_no_source"],
            to_move_no_reachable_allowed_destination=totals[
                "to_move_no_reachable_allowed_destination"
            ],
            to_move_dead_promotion_target=totals["to_move_dead_promotion_target"],
            to_move_pseudo_promotion_filtered_by_legal_safety=totals[
                "to_move_pseudo_promotion_filtered_by_legal_safety"
            ],
            zone_geometry_no_source=totals["zone_geometry_no_source"],
            no_reachable_allowed_destination=totals["no_reachable_allowed_destination"],
            no_legal_move_from_square=totals["no_legal_move_from_square"],
            moves_exist_but_none_is_an_allowed_promotion=totals[
                "moves_exist_but_none_is_an_allowed_promotion"
            ],
            dead_promotion_target=totals["dead_promotion_target"],
            pseudo_promotion_filtered_by_legal_safety=totals[
                "pseudo_promotion_filtered_by_legal_safety"
            ],
            of_which_promotion_specific_legal_filter=totals[
                "promotion_specific_legal_filter"
            ],
            of_which_parent_move_refuted_by_anchor_safety=totals[
                "parent_move_refuted_by_anchor_safety"
            ],
            of_which_forced_square_all_variants_refuted=totals[
                "forced_square_all_variants_refuted"
            ],
            would_promote_but_not_to_move=totals["would_promote_but_not_to_move"],
            to_move_observations=totals["to_move_zone_geometry_no_source"]
            + totals["to_move_no_reachable_allowed_destination"]
            + totals["to_move_dead_promotion_target"]
            + totals["to_move_pseudo_promotion_filtered_by_legal_safety"]
            + contact,
            idle_observations=n
            - (
                totals["to_move_zone_geometry_no_source"]
                + totals["to_move_no_reachable_allowed_destination"]
                + totals["to_move_dead_promotion_target"]
                + totals["to_move_pseudo_promotion_filtered_by_legal_safety"]
                + contact
            ),
            games_scanned=totals["games_scanned"],
            games_deduplicated=totals["games_deduplicated"],
            positions_scanned=totals["positions"],
            wall_seconds=round(elapsed, 2),
            problems=problems,
        ),
        per_seed=[
            dict(seed=seed, **dict(counts))
            for seed, counts in sorted(per_seed.items())
        ],
        per_game=per_game,
        defect_corrections=[
            dict(
                what="promotion-table cache keyed by id(compiled)",
                how_found="the independent per-case probe recorded 8 pseudo-legal-but-illegal promotions while this scan reported 6, all in seed 77",
                cause="each game builds a fresh compiled ruleset; the released object's id was recycled, so a promotion table could be reused across seeds",
                fix="cache keyed by compiled.ruleset_fingerprint",
                discarded_runs=[
                    "564bf23dac55da5ccbb9abc94be21ecb3d0512afc2b8095873122b8a19ff38da",
                    "716e993fe74cc810d6787fd5fb4a18d6f1ca9feb31a6a3ae5a53cb90d1fa160",
                ],
                status="private and unpublished; no number from either run is used in a report",
            )
        ],
        nonclaims=[
            "no rate contrast between the in-zone and outside-zone arms; the withdrawn contrast is not reproduced",
            "no claim that any term changed a chosen action, an outcome or a strength",
            "board 4, classic_like, these six stored game files only; deeper play and boards 6 and 8 are unmeasured",
            "the partition is definitionally complete because a piece either has a legal promotion action or falls in one of the named structural cases; that completeness is not evidence",
            "the idle-side split is descriptive: an idle piece has no legal action by the rules of turn order",
        ],
    )
    out = HERE / "results_zone_promotion_source_classification.json"
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=1))
    print("output_sha256", hashlib.sha256(out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
