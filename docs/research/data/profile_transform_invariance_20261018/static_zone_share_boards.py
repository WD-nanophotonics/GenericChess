"""How much of the board is in-zone, per board size, from the served rule data.

DEEPSEEK_AUX private check, 2026-10-18.  Stage 7 measured a 30.8% in-zone share
on *played* board-4 positions.  A small board may make that share an artefact
of board size, so this check reports the structural analogue on the boards the
published study used: for every promotable type with a positive gain, the share
of board squares whose forward mobility is empty (the served definition of
`zone`).  No search, no games: it reads `empty_forward_mobility` from the
generated rules only.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

SEEDS = list(range(292001, 292041))


def main() -> int:
    records = []
    for board in (4, 6, 8):
        shares = []
        for seed in SEEDS:
            compiled = generate_game(
                GeneratorConfig(seed=seed, board_size=board, setup_preset="classic_like")
            ).compiled_ruleset
            squares = board * board
            for piece_type in compiled.piece_types:
                if not piece_type.is_promotable:
                    continue
                for owner in (0, 1):
                    mobility = compiled.empty_forward_mobility[piece_type.type_id][owner]
                    in_zone = sum(1 for entry in mobility if not entry)
                    shares.append(in_zone / squares)
        records.append(
            dict(
                board_size=board,
                records=len(shares),
                mean_share=round(statistics.fmean(shares), 4),
                median_share=round(statistics.median(shares), 4),
                min_share=round(min(shares), 4),
                max_share=round(max(shares), 4),
            )
        )
    payload = dict(
        role="DEEPSEEK_AUX",
        question="Is the board-4 in-zone share a small-board artefact?",
        design=dict(
            seeds=[SEEDS[0], SEEDS[-1]],
            boards=[4, 6, 8],
            setup_preset="classic_like",
            measure="share of board squares whose forward mobility is empty, per promotable type and owner",
            no_new_search=True,
        ),
        records=records,
        nonclaims=[
            "structural share only; played positions need not sample squares uniformly",
            "board 4 is included for comparability with Stage 7, not as a study board",
        ],
    )
    out = Path(__file__).resolve().parent / "results_static_zone_share.json"
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(records, indent=1))
    print("output_sha256", __import__("hashlib").sha256(out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
