"""Development preview: dump piece textures as SVG files (+ optional HTML).

Run with::

    python -m generic_chess.visual.preview [--out DIR] [--size 128] [--seed 42]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core.movement import LeapAtom, RayAtom
from ..core.pieces import PieceType
from ..generation.config import GenerationError, GeneratorConfig
from ..generation.generator import generate_game
from .textures import generate_piece_texture


def _classic_piece_types() -> list[tuple[str, PieceType]]:
    king = PieceType("K", "King", tuple(LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)), is_anchor=True)
    rook_ray = PieceType(
        "R", "Rook (ray)",
        (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))),
    )
    false_rook = PieceType(
        "F", "Rook (leap)",
        (LeapAtom((0, 1)), LeapAtom((0, -1)), LeapAtom((1, 0)), LeapAtom((-1, 0))),
    )
    bishop_ray = PieceType(
        "B", "Bishop (ray)",
        (RayAtom((1, 1)), RayAtom((1, -1)), RayAtom((-1, 1)), RayAtom((-1, -1))),
    )
    false_bishop = PieceType(
        "X", "Bishop (leap)",
        (LeapAtom((1, 1)), LeapAtom((1, -1)), LeapAtom((-1, 1)), LeapAtom((-1, -1))),
    )
    queen = PieceType(
        "Q", "Queen",
        tuple(RayAtom(v) for v in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))),
    )
    pawn = PieceType("P", "Pawn", (LeapAtom((0, 1)),))
    return [
        ("king", king),
        ("rook_ray", rook_ray),
        ("false_rook", false_rook),
        ("bishop_ray", bishop_ray),
        ("false_bishop", false_bishop),
        ("queen", queen),
        ("pawn", pawn),
    ]


def _suffix(owner: int) -> str:
    return "w" if owner == 0 else "b"


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generic_chess.visual.preview",
        description="Generate piece texture SVG files for preview/debugging.",
    )
    parser.add_argument("--out", default="visual_preview", help="output directory (default visual_preview)")
    parser.add_argument("--size", type=int, default=128, help="texture size in pixels (default 128)")
    parser.add_argument("--seed", type=int, default=42, help="seed for the random ruleset sample")
    parser.add_argument("--no-html", action="store_true", help="skip the index.html preview page")
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists() and not out.is_dir():
        print(f"error: --out must be a directory, got {out}", file=sys.stderr)
        return 1
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create output directory: {exc}", file=sys.stderr)
        return 1

    entries: list[tuple[str, int, str]] = []  # (label, owner, svg)
    try:
        for name, piece_type in _classic_piece_types():
            for owner in (0, 1):
                tex = generate_piece_texture(piece_type, owner=owner, size=args.size)
                filename = f"{name}_{_suffix(owner)}.svg"
                _write_text(out / filename, tex.svg)
                entries.append((f"{name} ({owner})", owner, tex.svg))

        game = generate_game(GeneratorConfig(seed=args.seed))
        for pt in game.ruleset.piece_types:
            for owner in (0, 1):
                tex = generate_piece_texture(pt, owner=owner, size=args.size)
                filename = f"rand_{pt.type_id}_{_suffix(owner)}.svg"
                _write_text(out / filename, tex.svg)
                entries.append((f"rand {pt.type_id} ({owner})", owner, tex.svg))
    except (OSError, GenerationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.no_html:
        try:
            _write_text(out / "index.html", _render_html(entries))
        except OSError as exc:
            print(f"error: cannot write index.html: {exc}", file=sys.stderr)
            return 1

    print(f"wrote {len(entries)} SVG textures to {out}")
    return 0


def _render_html(entries: list[tuple[str, int, str]]) -> str:
    cells = []
    for label, owner, svg in entries:
        cells.append(
            f'<div style="display:inline-block;text-align:center;margin:8px;">'
            f'<div>{label}</div>{svg}</div>'
        )
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>GenericChess texture preview</title></head><body>"
        + "".join(cells)
        + "</body></html>"
    )


if __name__ == "__main__":
    raise SystemExit(main())
