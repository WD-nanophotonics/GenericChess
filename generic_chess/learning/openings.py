"""Evaluator-neutral deterministic opening corpus for arena matches.

Openings are generated from Core legal actions only (GameSession + a
local deterministic PRNG), never from search scores or checkpoint
evaluators, so the same corpus is a fixed holdout set for every checkpoint.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..core.actions import Action, action_from_dict, action_to_dict
from ..core.identity import position_identity_key
from ..session.session import GameSession
from .serialization import stable_sha256


class ArenaOpeningGenerationError(RuntimeError):
    """Raised when a terminal-free opening cannot be generated."""


@dataclass(frozen=True, slots=True)
class ArenaOpening:
    index: int
    opening_seed: int
    target_plies: int
    actions: tuple[Action, ...]
    final_position_key: str


@dataclass(frozen=True, slots=True)
class ArenaOpeningCorpus:
    schema_version: int = 1
    ruleset_fingerprint: str = ""
    seed: int = 0
    min_plies: int = 2
    max_plies: int = 6
    openings: tuple[ArenaOpening, ...] = ()

    @property
    def corpus_id(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "seed": self.seed,
            "min_plies": self.min_plies,
            "max_plies": self.max_plies,
            "openings": [
                {
                    "index": o.index,
                    "opening_seed": o.opening_seed,
                    "target_plies": o.target_plies,
                    "actions": [action_to_dict(a) for a in o.actions],
                    "final_position_key": o.final_position_key,
                }
                for o in self.openings
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArenaOpeningCorpus":
        if data.get("schema_version") != 1:
            raise ValueError(
                f"unsupported opening corpus schema {data.get('schema_version')}"
            )
        return cls(
            ruleset_fingerprint=str(data["ruleset_fingerprint"]),
            seed=int(data["seed"]),
            min_plies=int(data["min_plies"]),
            max_plies=int(data["max_plies"]),
            openings=tuple(
                ArenaOpening(
                    index=int(o["index"]),
                    opening_seed=int(o["opening_seed"]),
                    target_plies=int(o["target_plies"]),
                    actions=tuple(action_from_dict(a) for a in o["actions"]),
                    final_position_key=str(o["final_position_key"]),
                )
                for o in data["openings"]
            ),
        )

    def validate(self, compiled) -> None:
        if self.ruleset_fingerprint != compiled.ruleset_fingerprint:
            raise ValueError(
                "opening corpus ruleset fingerprint does not match the "
                "compiled ruleset"
            )
        for opening in self.openings:
            session = GameSession(compiled)
            for action in opening.actions:
                if action not in session.legal_actions():
                    raise ValueError(
                        f"opening {opening.index}: action {action} is not "
                        "legal at replay"
                    )
                session.submit(action)
            if session.result.status.value != "ongoing":
                raise ValueError(
                    f"opening {opening.index} ended before the target ply "
                    f"({session.result.status.value})"
                )
            key = position_identity_key(session.state.position, compiled)
            if key != opening.final_position_key:
                raise ValueError(
                    f"opening {opening.index} replay key mismatch: "
                    f"{key} != {opening.final_position_key}"
                )
            if len(opening.actions) != opening.target_plies:
                raise ValueError(
                    f"opening {opening.index}: ply count mismatch"
                )


def _canonical_order_key(action: Action) -> str:
    import json

    return json.dumps(action_to_dict(action), sort_keys=True)


def generate_arena_openings(
    compiled,
    *,
    count: int,
    seed: int,
    min_plies: int = 2,
    max_plies: int = 6,
    max_attempts: int = 100,
) -> ArenaOpeningCorpus:
    """Generate ``count`` terminal-free openings using only Core legal
    actions and a local deterministic PRNG."""
    openings: list[ArenaOpening] = []
    base_rng = random.Random(seed)
    for index in range(count):
        target_plies = base_rng.randint(min_plies, max_plies)
        generated = None
        for attempt in range(max_attempts):
            opening_seed = seed * 1000 + index * 100 + attempt
            rng = random.Random(opening_seed)
            session = GameSession(compiled)
            actions: list[Action] = []
            ok = True
            for _ in range(target_plies):
                legal = session.legal_actions()
                if not legal:
                    ok = False
                    break
                ordered = sorted(legal, key=_canonical_order_key)
                action = ordered[rng.randrange(len(ordered))]
                session.submit(action)
                actions.append(action)
                if session.result.status.value != "ongoing":
                    ok = False
                    break
            if ok and session.result.status.value == "ongoing":
                generated = ArenaOpening(
                    index=index,
                    opening_seed=opening_seed,
                    target_plies=target_plies,
                    actions=tuple(actions),
                    final_position_key=position_identity_key(
                        session.state.position, compiled
                    ),
                )
                break
        if generated is None:
            raise ArenaOpeningGenerationError(
                f"could not generate a terminal-free opening for index "
                f"{index} after {max_attempts} attempts"
            )
        openings.append(generated)
    return ArenaOpeningCorpus(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        seed=seed,
        min_plies=min_plies,
        max_plies=max_plies,
        openings=tuple(openings),
    )
