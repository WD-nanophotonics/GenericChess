"""F86F bounded ordinary-piece mate-capacity census."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from generic_chess.benchmark.mate_capacity import MateCapacityProfile
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import has_legal_action
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.core.coordinates import Square
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleSet, ruleset_from_dict


SAMPLES = ("V4-3", "V5-3")
CELLS = ("ORTHO4_CURRENT", "FULL8_CURRENT")
CAP_PER_CELL = 2048
TOTAL_CAP = 8192


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _load_rulesets(root: Path) -> dict[tuple[str, str], RuleSet]:
    result: dict[tuple[str, str], RuleSet] = {}
    f86d = _load_json(root, "artifacts/f86d_mobility_ablation/counterfactual_rulesets.json")
    for row in f86d["rows"]:
        if row["sample_id"] in SAMPLES and row["profile"] == "A_FULL_ANCHOR":
            result[(row["sample_id"], "FULL8_CURRENT")] = ruleset_from_dict(row["ruleset"])
    f86e = _load_json(root, "artifacts/f86e_anchor_placement_ablation/counterfactual_rulesets.json")
    for row in f86e["rows"]:
        if row["sample_id"] in SAMPLES and row["cell"] == "ORTHO4_CURRENT":
            result[(row["sample_id"], "ORTHO4_CURRENT")] = ruleset_from_dict(row["ruleset"])
    return result


def _anchor_type_id(compiled) -> str:
    return next(piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor)


def _ordinary_multiset(compiled) -> tuple[str, ...]:
    anchor_ids = {piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor}
    return tuple(sorted(
        piece.current_type_id
        for piece in compiled.initial_position.board
        if piece is not None and piece.owner == 0 and piece.current_type_id not in anchor_ids
    ))


def _attack_masks(compiled, type_ids: Iterable[str], zone_mask: int) -> dict[str, tuple[int, ...]]:
    n = compiled.board_size
    masks: dict[str, tuple[int, ...]] = {}
    for type_id in sorted(set(type_ids)):
        rows = []
        for square_index in range(n * n):
            mask = 0
            for target in compiled.empty_mobility[type_id][0][square_index]:
                target_index = target.rank * n + target.file
                if zone_mask & (1 << target_index):
                    mask |= 1 << target_index
            rows.append(mask)
        masks[type_id] = tuple(rows)
    return masks


def _iter_placements(
    type_ids: tuple[str, ...],
    board_size: int,
    forbidden: int,
    masks: dict[str, tuple[int, ...]],
) -> Iterable[tuple[tuple[str, int], ...]]:
    placement: list[tuple[str, int]] = []
    used: set[int] = set()

    def visit(index: int):
        if index == len(type_ids):
            yield tuple(placement)
            return
        type_id = type_ids[index]
        start = placement[-1][1] + 1 if index and type_ids[index - 1] == type_id else 0
        for square_index in range(start, board_size * board_size):
            if square_index == forbidden or square_index in used:
                continue
            used.add(square_index)
            placement.append((type_id, square_index))
            yield from visit(index + 1)
            placement.pop()
            used.remove(square_index)

    yield from visit(0)


def _iter_type_subsets(type_ids: tuple[str, ...]) -> Iterable[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    for count in range(1, len(type_ids) + 1):
        for indices in combinations(range(len(type_ids)), count):
            subset = tuple(sorted(type_ids[index] for index in indices))
            if subset not in seen:
                seen.add(subset)
                yield subset


def _zone_mask(compiled, anchor_index: int, defender: int = 1) -> int:
    n = compiled.board_size
    targets = compiled.empty_mobility[_anchor_type_id(compiled)][defender][anchor_index]
    mask = 1 << anchor_index
    for target in targets:
        mask |= 1 << (target.rank * n + target.file)
    return mask


def _square_payload(index: int, board_size: int) -> list[int]:
    return [index % board_size, index // board_size]


def _build_position(
    compiled,
    defender_anchor: int,
    attacker_anchor: int,
    placement: tuple[tuple[str, int], ...],
) -> Position:
    n = compiled.board_size
    anchor_type = _anchor_type_id(compiled)
    board: list[Piece | None] = [None] * (n * n)
    board[defender_anchor] = Piece(1, anchor_type, anchor_type)
    board[attacker_anchor] = Piece(0, anchor_type, anchor_type)
    for type_id, square_index in placement:
        board[square_index] = Piece(0, type_id, type_id)
    return Position(
        board=tuple(board),
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=1,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )


def _census_cell(sample_id: str, cell: str, compiled) -> tuple[MateCapacityProfile, list[dict[str, Any]]]:
    n = compiled.board_size
    type_ids = _ordinary_multiset(compiled)
    all_zone_coverages: list[float] = []
    full_net_squares = 0
    checkable_squares = 0
    minimum_geometric: dict[str, int] = {}
    full_material_validated: dict[str, int] = {}
    validated_anchor_squares: set[int] = set()
    examples: list[dict[str, Any]] = []
    checked_positions = 0
    candidate_positions = 0
    truncated = False
    anchor_type = _anchor_type_id(compiled)

    for defender_anchor in range(n * n):
        zone = _zone_mask(compiled, defender_anchor)
        zone_size = zone.bit_count()
        masks = _attack_masks(compiled, type_ids, zone)
        anchor_bit = 1 << defender_anchor
        can_check = any(
            masks[type_id][square_index] & anchor_bit
            for type_id in type_ids
            for square_index in range(n * n)
            if square_index != defender_anchor
        )
        checkable_squares += int(can_check)

        max_coverage = 0
        exact_full_net = False
        for placement in _iter_placements(type_ids, n, defender_anchor, masks):
            coverage = 0
            for type_id, square_index in placement:
                coverage |= masks[type_id][square_index]
            max_coverage = max(max_coverage, (coverage & zone).bit_count())
            if coverage & zone == zone:
                exact_full_net = True
        all_zone_coverages.append(max_coverage / zone_size if zone_size else 0.0)

        minimum = None
        for subset in _iter_type_subsets(type_ids):
            subset_found = False
            for placement in _iter_placements(subset, n, defender_anchor, masks):
                coverage = 0
                for type_id, square_index in placement:
                    coverage |= masks[type_id][square_index]
                if coverage & zone == zone:
                    subset_found = True
                    break
            if subset_found:
                minimum = len(subset)
                break
        if minimum is not None:
            minimum_geometric[str(minimum)] = minimum_geometric.get(str(minimum), 0) + 1
        if not exact_full_net:
            continue
        full_net_squares += 1

        # Re-enumerate canonical full-material nets for engine validation.
        for placement in _iter_placements(type_ids, n, defender_anchor, masks):
            coverage = 0
            for type_id, square_index in placement:
                coverage |= masks[type_id][square_index]
            if coverage & zone != zone:
                continue
            occupied = {defender_anchor, *(square_index for _type_id, square_index in placement)}
            for attacker_anchor in range(n * n):
                if attacker_anchor in occupied:
                    continue
                if candidate_positions >= CAP_PER_CELL:
                    truncated = True
                    break
                candidate_positions += 1
                position = _build_position(compiled, defender_anchor, attacker_anchor, placement)
                checked_positions += 1
                if is_in_check(position, 0, compiled):
                    continue
                if not is_in_check(position, 1, compiled):
                    continue
                if has_legal_action(position, compiled):
                    continue
                validated_anchor_squares.add(defender_anchor)
                attacker_count = len(type_ids)
                full_material_validated[str(attacker_count)] = full_material_validated.get(str(attacker_count), 0) + 1
                if len(examples) < 3:
                    examples.append({
                        "defender_anchor": _square_payload(defender_anchor, n),
                        "attacker_anchor": _square_payload(attacker_anchor, n),
                        "ordinary": [
                            {"type_id": type_id, "square": _square_payload(square_index, n)}
                            for type_id, square_index in placement
                        ],
                    })
            if truncated:
                break
        if truncated:
            break

    profile = MateCapacityProfile(
        sample_id=sample_id,
        cell=cell,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        board_size=n,
        ordinary_type_multiset=type_ids,
        anchor_square_count=n * n,
        anchor_square_checkable_fraction=checkable_squares / (n * n),
        mean_anchor_zone_coverage_fraction=sum(all_zone_coverages) / len(all_zone_coverages),
        max_anchor_zone_coverage_fraction=max(all_zone_coverages) if all_zone_coverages else 0.0,
        geometric_full_net_anchor_fraction=full_net_squares / (n * n),
        minimum_geometric_attackers_distribution=minimum_geometric,
        engine_validated_mate_exists=bool(validated_anchor_squares),
        engine_validated_mate_anchor_fraction=len(validated_anchor_squares) / (n * n),
        full_material_validated_mate_position_count_by_attacker_count=full_material_validated,
        checked_position_count=checked_positions,
        candidate_position_count=candidate_positions,
        truncation=truncated,
        canonical_mate_examples=tuple(examples),
    )
    return profile, examples


def _routing(profiles: list[MateCapacityProfile]) -> dict[str, Any]:
    labels: list[str] = []
    if any(profile.truncation for profile in profiles):
        labels.append("MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP")
    else:
        if all(profile.geometric_full_net_anchor_fraction == 0.0 for profile in profiles):
            labels.append("ORDINARY_GEOMETRIC_MATE_CAPACITY_ABSENT")
        elif all(not profile.engine_validated_mate_exists for profile in profiles):
            labels.append("GEOMETRIC_NET_EXISTS_BUT_RULE_LEGAL_MATE_ABSENT")
        if any(profile.engine_validated_mate_exists for profile in profiles):
            labels.append("STRIPPED_ANCHOR_MATE_CAPACITY_EXISTS")
        by_sample = {sample_id: {profile.cell: profile for profile in profiles if profile.sample_id == sample_id} for sample_id in SAMPLES}
        if all(
            by_sample[sample_id]["ORTHO4_CURRENT"].geometric_full_net_anchor_fraction > 0.0
            and by_sample[sample_id]["FULL8_CURRENT"].geometric_full_net_anchor_fraction == 0.0
            for sample_id in SAMPLES
        ):
            labels.append("ANCHOR_ESCAPE_PROFILE_LIMITS_MATE_CAPACITY")
    return {"labels": labels, "by_sample_cell": {
        f"{profile.sample_id}:{profile.cell}": (
            ["MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP"] if profile.truncation else
            ["STRIPPED_ANCHOR_MATE_CAPACITY_EXISTS"] if profile.engine_validated_mate_exists else
            ["GEOMETRIC_NET_EXISTS_BUT_RULE_LEGAL_MATE_ABSENT"] if profile.geometric_full_net_anchor_fraction > 0.0 else
            ["ORDINARY_GEOMETRIC_MATE_CAPACITY_ABSENT"]
        )
        for profile in profiles
    }}


def run(output_dir: Path, root: Path) -> dict[str, Any]:
    rulesets = _load_rulesets(root)
    profiles: list[MateCapacityProfile] = []
    examples: list[dict[str, Any]] = []
    for sample_id in SAMPLES:
        for cell in CELLS:
            compiled = compile_ruleset(rulesets[(sample_id, cell)])
            profile, cell_examples = _census_cell(sample_id, cell, compiled)
            profiles.append(profile)
            examples.extend({"sample_id": sample_id, "cell": cell, **example} for example in cell_examples)
    total_checked = sum(profile.checked_position_count for profile in profiles)
    if total_checked > TOTAL_CAP:
        raise RuntimeError(f"candidate position cap exceeded: {total_checked} > {TOTAL_CAP}")
    routing = _routing(profiles)
    census = {
        "schema_version": 1,
        "sample_ids": list(SAMPLES),
        "cell_names": list(CELLS),
        "candidate_position_cap_per_cell": CAP_PER_CELL,
        "candidate_position_cap_total": TOTAL_CAP,
        "profiles": [profile.to_dict() for profile in profiles],
        "total_checked_position_count": total_checked,
        "total_candidate_position_count": sum(profile.candidate_position_count for profile in profiles),
        "any_truncation": any(profile.truncation for profile in profiles),
        "routing": routing,
        "real_games": 0,
        "teacher_search_compute": 0,
        "f85_actual_compute": 0,
        "default_generator_changed": False,
        "no_ruleset_replacement": True,
    }
    _write_json(output_dir / "census.json", census)
    _write_json(output_dir / "examples.json", {"schema_version": 1, "examples": examples})
    return census


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86f_mate_capacity"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.output_dir, args.root)
    print(json.dumps({key: result[key] for key in (
        "total_checked_position_count", "total_candidate_position_count", "any_truncation", "routing",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
