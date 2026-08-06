"""Python RuleSet -> native compiled rules (payload build + validation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.movement import LeapAtom, RayAtom
from ..rules.compiled import CompiledRuleSet
from . import _module, native_available

NATIVE_SCHEMA_VERSION = "native-0.1.0"


class NativeUnsupportedRuleError(ValueError):
    """Raised when a RuleSet cannot be expressed by the native kernel."""


@dataclass(frozen=True)
class NativeCompilationReport:
    ruleset_fingerprint: str
    type_count: int
    board_squares: int
    leap_atom_entries: int
    ray_atom_entries: int
    estimated_bytes: int
    native_schema_version: str


class NativeCompiledRules:
    """Owns the native rules capsule plus the type index mapping."""

    def __init__(
        self,
        capsule,
        report: NativeCompilationReport,
        type_map: dict[str, int],
        type_ids: list[str],
    ) -> None:
        self._capsule = capsule
        self._report = report
        self._type_map = type_map
        self._type_ids = type_ids

    @property
    def capsule(self):
        return self._capsule

    @property
    def fingerprint(self) -> str:
        return self._report.ruleset_fingerprint

    @property
    def type_count(self) -> int:
        return self._report.type_count

    @property
    def type_map(self) -> dict[str, int]:
        return self._type_map

    @property
    def type_ids(self) -> list[str]:
        return self._type_ids

    @property
    def report(self) -> NativeCompilationReport:
        return self._report


def _validate(condition: bool, message: str, fingerprint: str) -> None:
    if not condition:
        raise NativeUnsupportedRuleError(
            f"{message} (ruleset fingerprint {fingerprint}, "
            f"native schema {NATIVE_SCHEMA_VERSION})"
        )


def build_compile_payload(compiled: CompiledRuleSet) -> dict[str, Any]:
    """Convert a CompiledRuleSet into the plain native payload dict."""
    n = compiled.board_size
    fingerprint = compiled.ruleset_fingerprint
    _validate(1 <= n <= 16 and n * n <= 256, "board size out of native range", fingerprint)
    types = tuple(compiled.piece_types)
    _validate(len(types) <= 64, "too many piece types for native kernel", fingerprint)
    type_ids = sorted(t.type_id for t in types)
    type_map = {tid: i for i, tid in enumerate(type_ids)}
    by_id = {t.type_id: t for t in types}

    payload_types = []
    leap_entries = ray_entries = 0
    for tid in type_ids:
        pt = by_id[tid]
        atoms = []
        for atom in pt.movement_atoms:
            if isinstance(atom, LeapAtom):
                atoms.append(
                    {
                        "kind": 0,
                        "df": atom.offset[0],
                        "dr": atom.offset[1],
                        "max_steps": 0,
                    }
                )
                leap_entries += 1
            elif isinstance(atom, RayAtom):
                atoms.append(
                    {
                        "kind": 1,
                        "df": atom.direction[0],
                        "dr": atom.direction[1],
                        "max_steps": atom.max_steps or 0,
                    }
                )
                ray_entries += 1
            else:  # pragma: no cover - MovementAtom is the closed union
                raise NativeUnsupportedRuleError(
                    f"unknown movement atom {atom!r} for type {pt.type_id!r} "
                    f"(ruleset {fingerprint}, native schema {NATIVE_SCHEMA_VERSION})"
                )
        _validate(len(atoms) <= 16, f"type {pt.type_id!r}: too many atoms", fingerprint)
        targets = []
        for tid in pt.promotion_target_ids:
            _validate(
                tid in type_map,
                f"type {pt.type_id!r}: promotion target {tid!r} missing",
                fingerprint,
            )
            targets.append(type_map[tid])
        _validate(len(targets) <= 8, f"type {pt.type_id!r}: too many promotion targets", fingerprint)

        promo_allowed = []
        promo_forced = []
        alive_promo = []
        drop_mask = []
        for owner in (0, 1):
            pairs = [
                (f.rank * n + f.file) << 16 | (t.rank * n + t.file)
                for f, t in compiled.promotion_allowed.get(pt.type_id, ((), ()))[owner]
            ]
            promo_allowed.append(sorted(pairs))
            forced = sorted(
                (s.rank * n + s.file)
                for s in compiled.promotion_forced.get(pt.type_id, (frozenset(), frozenset()))[owner]
            )
            promo_forced.append(forced)
            alive = []
            for idx in range(n * n):
                mask = 0
                for tid in pt.promotion_target_ids:
                    if compiled.empty_mobility[tid][owner][idx]:
                        mask |= 1 << type_map[tid]
                alive.append(mask)
            alive_promo.append(alive)
            allowed_squares = []
            if pt.type_id in compiled.drop_allowed:
                mask = compiled.drop_allowed[pt.type_id][owner]
                allowed_squares = [i for i, ok in enumerate(mask) if ok]
            drop_mask.append(allowed_squares)
        payload_types.append(
            {
                "is_anchor": pt.is_anchor,
                "is_promotable": pt.is_promotable,
                "atoms": atoms,
                "promo_targets": targets,
                "promo_allowed": promo_allowed,
                "promo_forced": promo_forced,
                "alive_promo": alive_promo,
                "drop_mask": drop_mask,
            }
        )

    payload = {
        "fingerprint": fingerprint,
        "width": n,
        "height": n,
        "repetition_limit": compiled.repetition_limit,
        "max_ply": compiled.max_ply,
        "types": payload_types,
    }
    estimated = (
        2 * 2 * 256 * 64 * 2 * 8  # piece hash
        + 2 * 2 * 64 * 64 * 8  # hand hash
        + 2 * 2 * 8  # side hash
        + 64 * 2 * 256 * 8  # alive promo
        + 64 * 2 * 4 * 8 * 2  # forced + drop bitsets
        + sum(len(p["promo_allowed"][0]) + len(p["promo_allowed"][1]) for p in payload_types) * 4
    )
    return payload, NativeCompilationReport(
        ruleset_fingerprint=fingerprint,
        type_count=len(types),
        board_squares=n * n,
        leap_atom_entries=leap_entries,
        ray_atom_entries=ray_entries,
        estimated_bytes=estimated,
        native_schema_version=NATIVE_SCHEMA_VERSION,
    )


def compile_native_rules(compiled: CompiledRuleSet) -> NativeCompiledRules:
    """Compile a CompiledRuleSet into the native kernel (one-time cost)."""
    if not native_available():
        raise NativeUnsupportedRuleError(
            "native extension is not built; run scripts/build_native_zig.py"
        )
    payload, report = build_compile_payload(compiled)
    capsule = _module().compile_rules(payload)
    type_ids = sorted(t.type_id for t in compiled.piece_types)
    type_map = {tid: i for i, tid in enumerate(type_ids)}
    return NativeCompiledRules(capsule, report, type_map, type_ids)
