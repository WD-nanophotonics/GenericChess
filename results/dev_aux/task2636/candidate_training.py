"""Candidate-index training inputs for the frozen task2636 TDLeaf panel.

This module binds producer arm identity to the frozen candidate order and root
pool, provides independent episode/prefix replay, and does not register or run
the frozen experiment panel.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterator

from generic_chess.core.actions import action_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task109.adapter import PersistentStop
from results.dev_aux.task2621.fixed_scale import (
    FixedScaleSessionEnv,
    unchanged_learner,
    unchanged_model,
)
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2492.learning import BudgetEnd, Receipt


FROZEN_CHANNELS = (
    ("board", "P"), ("board", "A"), ("board", "B"), ("board", "C"),
    ("board", "X"), ("hand", "A"), ("hand", "B"), ("hand", "C"),
    ("hand", "P"), ("hand", "X"),
)


@dataclass(frozen=True)
class CandidateArmInput:
    candidate_index: int
    candidate_seed: int
    candidate_ruleset_sha256: str
    rule_path: str
    roots: tuple[dict[str, Any], ...]
    initial_weights: tuple[float, ...]


@dataclass(frozen=True)
class TrainingEpisodeInput:
    candidate_index: int
    candidate_seed: int
    episode_index: int
    root: dict[str, Any]
    learner_color: int


@dataclass
class CandidateArmRuntime:
    identity: CandidateArmInput
    model: Any
    foe: Any
    learner: Any


@dataclass(frozen=True)
class TrainingStepResult:
    actor: int
    learner_turn: bool
    complete: bool
    moved: bool
    nodes: int
    reason: str


@dataclass(frozen=True)
class TrainingEpisodeResult:
    candidate_index: int
    candidate_seed: int
    episode_index: int
    learner_color: int
    root_family: int
    initial_weights: list[float]
    final_weights: list[float]
    start_record: dict[str, Any]
    final_record: dict[str, Any]
    query_rows: tuple[dict[str, Any], ...]
    outcome: int | None
    ending: str
    nodes: int
    queries: int
    stats: dict[str, Any]

    def summary_record(self) -> dict[str, Any]:
        return {
            "candidate_index": self.candidate_index,
            "candidate_seed": self.candidate_seed,
            "episode": self.episode_index,
            "root_family": self.root_family,
            "learner_color": self.learner_color,
            "initial_weights": self.initial_weights,
            "final_weights": self.final_weights,
            "start_record": self.start_record,
            "final_record": self.final_record,
            "actual_outcome": self.outcome,
            "ending": self.ending,
            "nodes": self.nodes,
            "queries": self.queries,
            "stats": self.stats,
        }


@dataclass(frozen=True)
class TrainingArmResult:
    candidate_index: int
    candidate_seed: int
    candidate_ruleset_sha256: str
    ending: str
    episodes: int
    actual_terminals: int
    unknown_episodes: int
    combined_nodes: int
    final_weights: list[float]

    def summary_record(self) -> dict[str, Any]:
        return {
            "candidate_index": self.candidate_index,
            "candidate_seed": self.candidate_seed,
            "candidate_ruleset_sha256": self.candidate_ruleset_sha256,
            "ending": self.ending,
            "episodes": self.episodes,
            "actual_terminals": self.actual_terminals,
            "unknown_episodes": self.unknown_episodes,
            "combined_candidate_and_foe_nodes": self.combined_nodes,
            "final_weights": self.final_weights,
        }


def initialize_candidate_arm(arm: CandidateArmInput) -> CandidateArmRuntime:
    """Create task2625-compatible model/foe/TD state for one frozen candidate."""
    model = unchanged_model(list(arm.initial_weights))
    foe = unchanged_model([1.0] * len(arm.initial_weights))
    learner = unchanged_learner()
    if (model.fixed != 0 or model.scale != 10.0 or model.weights[0] != 1.0
            or foe.fixed != 0 or foe.scale != 10.0
            or foe.weights != [1.0] * len(arm.initial_weights)):
        raise ValueError("candidate model/foe initialization differs from task2625 contract")
    return CandidateArmRuntime(arm, model, foe, learner)


def validate_root_record_binding(root: dict[str, Any]) -> str:
    record = root.get("record")
    if not isinstance(record, dict):
        raise ValueError("frozen root record is missing")
    canonical_record = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    record_hash = hashlib.sha256(canonical_record).hexdigest()
    if (root.get("record_sha256") != record_hash
            or root.get("ruleset_fingerprint") != record.get("ruleset_fingerprint")):
        raise ValueError("frozen root record hash/fingerprint mismatch")
    return record_hash


class CandidateTrainingJournal:
    """Write-once JSONL prefix writer; no resume, retry, or slot creation."""

    def __init__(self, started_path: Path, query_path: Path,
                 episode_path: Path, result_path: Path, started: dict[str, Any]):
        self.started_path = Path(started_path)
        self.query_path = Path(query_path)
        self.episode_path = Path(episode_path)
        self.result_path = Path(result_path)
        self._finished = False
        self._closed = False
        opened: list[Any] = []
        try:
            self._started = self.started_path.open("x", encoding="utf-8", newline="\n")
            opened.append(self._started)
            self._write_line(self._started, started)
            self._started.flush()
            os.fsync(self._started.fileno())
            self._queries = self.query_path.open("x", encoding="utf-8", newline="\n")
            opened.append(self._queries)
            self._episodes = self.episode_path.open("x", encoding="utf-8", newline="\n")
            opened.append(self._episodes)
        except BaseException:
            for stream in opened:
                if not stream.closed:
                    stream.close()
            self._closed = True
            raise

    @staticmethod
    def _write_line(stream: Any, value: dict[str, Any]) -> None:
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=False, allow_nan=False))
        stream.write("\n")

    def append_query(self, row: dict[str, Any]) -> None:
        if self._closed or self._finished:
            raise RuntimeError("training journal is no longer writable")
        self._write_line(self._queries, row)
        self._queries.flush()

    def close_episode(self, summary: dict[str, Any]) -> None:
        if self._closed or self._finished:
            raise RuntimeError("training journal is no longer writable")
        self._write_line(self._episodes, summary)
        self._queries.flush()
        self._episodes.flush()
        os.fsync(self._queries.fileno())
        os.fsync(self._episodes.fileno())

    def finish(self, result: dict[str, Any]) -> None:
        if self._closed or self._finished:
            raise RuntimeError("training journal cannot be finished twice")
        self._queries.flush()
        self._episodes.flush()
        os.fsync(self._queries.fileno())
        os.fsync(self._episodes.fileno())
        with self.result_path.open("x", encoding="utf-8", newline="\n") as stream:
            self._write_line(stream, result)
            stream.flush()
            os.fsync(stream.fileno())
        self._finished = True

    def close(self) -> None:
        if self._closed:
            return
        for stream in (self._started, self._queries, self._episodes):
            if not stream.closed:
                stream.close()
        self._closed = True

    def __enter__(self) -> "CandidateTrainingJournal":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()


def read_newline_jsonl_prefix(path: Path) -> tuple[tuple[dict[str, Any], ...], bytes]:
    """Read only complete newline-terminated JSON rows; preserve any byte tail."""
    return parse_newline_jsonl_prefix(Path(path).read_bytes())


def parse_newline_jsonl_prefix(raw: bytes) -> tuple[tuple[dict[str, Any], ...], bytes]:
    """Parse complete object rows from the exact supplied byte snapshot."""
    if not isinstance(raw, bytes):
        raise TypeError("JSONL prefix snapshot must be bytes")
    last_newline = raw.rfind(b"\n")
    if last_newline < 0:
        return (), raw
    complete = raw[:last_newline + 1]
    trailing = raw[last_newline + 1:]
    rows = tuple(_strict_json_loads(line) for line in complete.splitlines())
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("training JSONL prefix contains a non-object row")
    return rows, trailing


def _strict_json_loads(raw: bytes) -> Any:
    """Reject ambiguous duplicate object keys and non-standard JSON values."""
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("training JSON contains duplicate object keys")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"training JSON contains non-standard constant {value}")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys,
                          parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("training journal row is not valid UTF-8 JSON") from exc


def recovered_training_status(started_path: Path, result_path: Path) -> str:
    """Classify a read-only recovery without changing or completing receipts."""
    if Path(result_path).exists():
        try:
            rows, trailing = read_newline_jsonl_prefix(Path(result_path))
        except (OSError, ValueError, json.JSONDecodeError):
            return "NO_FINAL_RECEIPT"
        if not trailing and len(rows) == 1 and isinstance(rows[0].get("status"), str):
            return rows[0]["status"]
        return "NO_FINAL_RECEIPT"
    return "NO_FINAL_RECEIPT" if Path(started_path).exists() else "NOT_STARTED"


def finish_candidate_episode(
        runtime: CandidateArmRuntime, actual_terminal_outcome: int | float | None) -> dict[str, Any]:
    """Finish TD only with an actual W/L/D value; ``None`` stays UNKNOWN."""
    if (actual_terminal_outcome is not None
            and (type(actual_terminal_outcome) not in (int, float)
                 or not math.isfinite(actual_terminal_outcome)
                 or actual_terminal_outcome not in (-1, 0, 1))):
        raise ValueError("episode outcome must be actual terminal W/L/D or UNKNOWN None")
    return runtime.learner.finish(runtime.model, actual_terminal_outcome)


def apply_training_search_receipt(
        runtime: CandidateArmRuntime, env: Any, *, learner_color: int,
        receipt: Any) -> TrainingStepResult:
    """Apply one completed search result using task2625 learner-turn semantics.

    Incomplete searches never update TD or advance the game; the caller must
    close the episode as UNKNOWN and must not start another query for it.
    """
    if type(learner_color) is not int or learner_color not in (0, 1):
        raise ValueError("learner color must be player 0 or 1")
    actor = env.player()
    if type(actor) is not int or actor not in (0, 1):
        raise ValueError("environment actor must be player 0 or 1")
    learner_turn = actor == learner_color
    before_record = env.record()
    before_state = env.session.state
    if not receipt.complete:
        if env.record() != before_record or env.session.state != before_state:
            raise AssertionError("search changed complete history before an incomplete receipt")
        return TrainingStepResult(actor, learner_turn, False, False,
                                  receipt.nodes, receipt.reason)
    if receipt.action is None:
        raise ValueError("complete training search lacks a legal action")
    if learner_turn:
        runtime.learner.observe(runtime.model, receipt)
    env.push(receipt.action)
    env.replay()
    return TrainingStepResult(actor, learner_turn, True, True,
                              receipt.nodes, receipt.reason)


def execute_candidate_training_query(
        runtime: CandidateArmRuntime, env: Any, *, learner_color: int,
        search: Callable[..., Any], nodes: int, seconds: float, seed: int,
        cancel: Callable[[], None]) -> tuple[Any, TrainingStepResult]:
    """Search one turn without mutating history, then admit/apply its receipt."""
    if type(learner_color) is not int or learner_color not in (0, 1):
        raise ValueError("learner color must be player 0 or 1")
    if (type(nodes) is not int or nodes <= 0
            or type(seconds) not in (int, float)
            or not math.isfinite(seconds) or seconds <= 0
            or type(seed) is not int or not callable(cancel)):
        raise ValueError("training query resources must be positive and finite")
    actor = env.player()
    selected_model = runtime.model if actor == learner_color else runtime.foe
    before_record = env.record()
    before_state = env.session.state

    def cancel_as_budget_end() -> None:
        try:
            cancel()
        except PersistentStop as exc:
            raise BudgetEnd("STOPPED_USER") from exc

    receipt = search(env, selected_model, nodes=nodes, seconds=seconds,
                     seed=seed, cancel=cancel_as_budget_end)
    if env.record() != before_record or env.session.state != before_state:
        raise AssertionError("training search mutated the complete game history")
    step = apply_training_search_receipt(
        runtime, env, learner_color=learner_color, receipt=receipt)
    return receipt, step


def run_candidate_training_episode(
        runtime: CandidateArmRuntime, episode: TrainingEpisodeInput, env: Any, *,
        horizon: int, nodes_per_query: int, seconds_per_query: float,
        remaining_nodes: int, query_seed_base: int,
        search: Callable[..., Any], cancel: Callable[[], None],
        query_sink: Callable[[dict[str, Any]], None] | None = None,
        episode_sink: Callable[[dict[str, Any]], None] | None = None) -> TrainingEpisodeResult:
    """Run one bounded in-memory episode; durable rows remain caller-owned."""
    if (type(horizon) is not int or horizon <= 0
            or type(nodes_per_query) is not int or nodes_per_query <= 0
            or type(remaining_nodes) is not int or remaining_nodes < 0
            or type(query_seed_base) is not int):
        raise ValueError("invalid candidate training episode limits")
    identity = runtime.identity
    if (episode.candidate_index != identity.candidate_index
            or episode.candidate_seed != identity.candidate_seed
            or type(episode.episode_index) is not int or episode.episode_index < 0
            or type(episode.learner_color) is not int or episode.learner_color not in (0, 1)
            or episode.root not in identity.roots):
        raise ValueError("training episode does not belong to the initialized candidate arm")
    root = episode.root
    if (root.get("candidate_index") != identity.candidate_index
            or root.get("candidate_seed") != identity.candidate_seed
            or root.get("rule_sha256") != identity.candidate_ruleset_sha256
            or root.get("rule_path") != identity.rule_path):
        raise ValueError("training episode root identity changed after arm construction")
    validate_root_record_binding(root)
    start_record = env.record()
    initial_weights = list(runtime.model.weights)
    query_rows: list[dict[str, Any]] = []
    nodes = queries = 0
    outcome: int | None = None
    ending = "HORIZON_UNKNOWN"
    for ply in range(horizon):
        try:
            cancel()
        except PersistentStop:
            ending = "STOPPED_USER"
            break
        try:
            outcome = env.terminal()
        except NonScoringTerminal:
            ending = "NON_SCORING_UNKNOWN"
            outcome = None
            break
        if outcome is not None:
            ending = "ACTUAL_TERMINAL"
            break
        available = remaining_nodes - nodes
        if available <= 0:
            ending = "NODE_CAP_UNKNOWN"
            break
        actor = env.player()
        learner_turn = actor == episode.learner_color
        selected_model = runtime.model if learner_turn else runtime.foe
        weights_before = list(selected_model.weights)
        record_before = env.record()
        requested_nodes = min(nodes_per_query, available)
        query_seed = query_seed_base + ply
        receipt, step = execute_candidate_training_query(
            runtime, env, learner_color=episode.learner_color,
            search=search, nodes=requested_nodes,
            seconds=seconds_per_query, seed=query_seed, cancel=cancel)
        nodes += receipt.nodes
        queries += 1
        query_rows.append({
            "candidate_index": episode.candidate_index,
            "candidate_seed": episode.candidate_seed,
            "episode": episode.episode_index,
            "root_family": episode.root.get("family"),
            "root_record_sha256": episode.root.get("record_sha256"),
            "learner_color": episode.learner_color,
            "ply": ply,
            "actor": actor,
            "learner_turn": learner_turn,
            "weights_before_search": weights_before,
            "record_before": record_before,
            "record_after": env.record(),
            "complete": receipt.complete,
            "value": receipt.value,
            "pv_phi": list(receipt.pv_phi) if receipt.pv_phi is not None else None,
            "pv_terminal": receipt.pv_terminal,
            "nodes": receipt.nodes,
            "requested_nodes": requested_nodes,
            "search_seed": query_seed,
            "seconds": receipt.seconds,
            "search_reason": receipt.reason,
        })
        if query_sink is not None:
            query_sink(query_rows[-1])
        if not receipt.complete:
            ending = ("STOPPED_USER" if receipt.reason == "STOPPED_USER"
                      else "SEARCH_RESOURCE_UNKNOWN")
            break
        if not step.moved:
            raise AssertionError("complete training receipt did not advance the episode")

    if outcome is None and ending not in ("STOPPED_USER", "NON_SCORING_UNKNOWN"):
        try:
            outcome = env.terminal()
        except NonScoringTerminal:
            outcome = None
            ending = "NON_SCORING_UNKNOWN"
        if outcome is not None:
            ending = "ACTUAL_TERMINAL"
    stats = finish_candidate_episode(runtime, outcome)
    result = TrainingEpisodeResult(
        episode.candidate_index, episode.candidate_seed, episode.episode_index,
        episode.learner_color, episode.root["family"], initial_weights,
        list(runtime.model.weights), start_record, env.record(), tuple(query_rows),
        outcome, ending, nodes, queries, stats)
    if episode_sink is not None:
        episode_sink(result.summary_record())
    return result


def run_candidate_training_arm(
        runtime: CandidateArmRuntime, *,
        environment_for_episode: Callable[[TrainingEpisodeInput], Any],
        horizon: int, nodes_per_query: int, seconds_per_query: float,
        node_cap: int, max_episodes: int, query_seed_base: int,
        search: Callable[..., Any], cancel: Callable[[], None],
        query_sink: Callable[[dict[str, Any]], None] | None = None,
        episode_sink: Callable[[dict[str, Any]], None] | None = None
        ) -> TrainingArmResult:
    """Run one candidate arm to its frozen node/episode/stop boundary.

    The caller supplies exact-history reconstruction and owns the write-once
    journal. A stop before an episode does not construct its environment; an
    in-episode stop closes that episode as UNKNOWN and starts no successor.
    ``node_cap`` counts both candidate and foe search nodes.
    """
    if (type(node_cap) is not int or node_cap <= 0
            or type(max_episodes) is not int or max_episodes <= 0
            or type(horizon) is not int or horizon <= 0
            or type(nodes_per_query) is not int or nodes_per_query <= 0
            or type(seconds_per_query) not in (int, float)
            or not math.isfinite(seconds_per_query) or seconds_per_query <= 0
            or type(query_seed_base) is not int
            or not callable(environment_for_episode)):
        raise ValueError("invalid candidate arm limits or environment factory")

    identity = runtime.identity
    nodes = episodes = actual_terminals = unknown_episodes = 0
    ending = "EPISODE_LIMIT"
    for episode in iter_training_episodes(identity, max_episodes=max_episodes):
        try:
            cancel()
        except PersistentStop:
            ending = "STOPPED_USER"
            break
        env = environment_for_episode(episode)
        result = run_candidate_training_episode(
            runtime, episode, env, horizon=horizon,
            nodes_per_query=nodes_per_query, seconds_per_query=seconds_per_query,
            remaining_nodes=node_cap - nodes, query_seed_base=query_seed_base,
            search=search, cancel=cancel, query_sink=query_sink,
            episode_sink=episode_sink)
        if (type(result.nodes) is not int or result.nodes < 0
                or result.nodes > node_cap - nodes):
            raise ValueError("candidate and foe nodes exceeded the frozen arm cap")
        episodes += 1
        nodes += result.nodes
        actual_terminals += int(result.outcome is not None)
        unknown_episodes += int(result.outcome is None)
        if result.ending == "STOPPED_USER":
            ending = "STOPPED_USER"
            break
        if nodes >= node_cap:
            ending = "NODE_CAP"
            break

    return TrainingArmResult(
        identity.candidate_index, identity.candidate_seed,
        identity.candidate_ruleset_sha256, ending, episodes,
        actual_terminals, unknown_episodes, nodes, list(runtime.model.weights))


def replay_training_episode_prefix(
        runtime: CandidateArmRuntime, episode: TrainingEpisodeInput,
        summary: dict[str, Any] | None,
        query_rows: tuple[dict[str, Any], ...] | list[dict[str, Any]],
        env: Any, *, decode_action: Callable[[Any], Any] = action_from_dict,
        verify_root_history: bool = True
        ) -> dict[str, Any]:
    """Replay logged moves/TD updates; ``summary=None`` means open prefix only.

    ``env`` must be freshly reconstructed from the candidate-bound root (use
    :func:`replay_training_root`); incomplete queries stay stationary and do
    not update the learner. Search itself is not rerun: its complete receipts
    are the frozen targets being checked against the episode's model trajectory.
    With a summary, terminal/UNKNOWN closure is verified and TD state is
    finished. Without one, only the query prefix is replayed and no outcome,
    episode closure or reward is inferred.
    """
    identity = runtime.identity
    root = next((r for r in identity.roots
                 if r.get("family") == episode.root.get("family")), None)
    if (root is None or root != episode.root
            or episode.candidate_index != identity.candidate_index
            or episode.candidate_seed != identity.candidate_seed
            or (summary is not None and (
                summary.get("candidate_index") != identity.candidate_index
                or summary.get("candidate_seed") != identity.candidate_seed
                or summary.get("episode") != episode.episode_index
                or summary.get("root_family") != root.get("family")
                or summary.get("learner_color") != episode.learner_color))):
        raise ValueError("episode summary or root belongs to a different candidate")
    validate_root_record_binding(root)
    if verify_root_history and env.record() != root.get("record"):
        raise ValueError("episode replay environment is not at its bound frozen root")
    if (summary is not None and (
            summary.get("initial_weights") != list(runtime.model.weights)
            or summary.get("start_record") != env.record())):
        raise ValueError("episode replay start differs from its model or game history")
    if summary is not None and summary.get("queries") != len(query_rows):
        raise ValueError("episode query count differs from its durable rows")

    total_nodes = 0
    incomplete_seen = False
    for ply, row in enumerate(query_rows):
        if (not isinstance(row, dict)
                or row.get("candidate_index") != identity.candidate_index
                or row.get("candidate_seed") != identity.candidate_seed
                or row.get("episode") != episode.episode_index
                or row.get("root_family") != root.get("family")
                or row.get("root_record_sha256") != root.get("record_sha256")
                or row.get("learner_color") != episode.learner_color
                or row.get("ply") != ply or incomplete_seen):
            raise ValueError("query row identity, order, or incomplete suffix is invalid")
        before = env.record()
        if row.get("record_before") != before:
            raise ValueError("query row starts from a different game history")
        actor = env.player()
        learner_turn = actor == episode.learner_color
        if (row.get("actor") != actor or row.get("learner_turn") is not learner_turn):
            raise ValueError("query row actor/learner-turn binding is invalid")
        model = runtime.model if learner_turn else runtime.foe
        if row.get("weights_before_search") != list(model.weights):
            raise ValueError("query row model snapshot does not follow the replayed updates")
        complete = row.get("complete")
        nodes = row.get("nodes")
        requested_nodes = row.get("requested_nodes")
        seconds = row.get("seconds")
        search_seed = row.get("search_seed")
        pv_phi = row.get("pv_phi")
        pv_terminal = row.get("pv_terminal")
        if (type(complete) is not bool or type(nodes) is not int or nodes < 0
                or type(requested_nodes) is not int or requested_nodes <= 0
                or nodes > requested_nodes or type(search_seed) is not int
                or type(seconds) not in (int, float) or not math.isfinite(seconds)
                or type(pv_terminal) is not bool
                or (pv_phi is not None and (type(pv_phi) is not list
                    or len(pv_phi) != len(runtime.model.weights)
                    or any(type(v) not in (int, float) or not math.isfinite(v)
                           for v in pv_phi)))):
            raise ValueError("query row receipt fields are malformed")

        after = row.get("record_after")
        action = None
        if complete:
            if isinstance(before, dict) and isinstance(after, dict):
                before_actions, after_actions = before.get("actions"), after.get("actions")
                stable_fields = {k: v for k, v in before.items() if k != "actions"}
                after_stable = {k: v for k, v in after.items() if k != "actions"}
            elif isinstance(before, list) and isinstance(after, list):
                before_actions, after_actions = before, after
                stable_fields = after_stable = None
            else:
                raise ValueError("query history records have incompatible shapes")
            if (type(before_actions) is not list or type(after_actions) is not list
                    or len(after_actions) != len(before_actions) + 1
                    or after_actions[:-1] != before_actions
                    or stable_fields != after_stable):
                raise ValueError("complete query did not append exactly one action")
            action = decode_action(after_actions[-1])
        elif after != before:
            raise ValueError("incomplete query changed the game history")

        value = row.get("value")
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError("query value is not finite")
        if complete and (value is None or (not pv_terminal and pv_phi is None)):
            raise ValueError("complete query lacks its search target or PV features")
        reason = row.get("search_reason")
        if not isinstance(reason, str):
            raise ValueError("query search reason is missing")
        receipt = Receipt(action, value, tuple(pv_phi) if pv_phi is not None else None,
                          pv_terminal, (), nodes, complete, 0, float(seconds), reason)
        if complete:
            if learner_turn:
                runtime.learner.observe(runtime.model, receipt)
            env.push(action)
            env.replay()
            if env.record() != after:
                raise ValueError("replayed complete query does not match its after-history")
        else:
            incomplete_seen = True
        total_nodes += nodes

    if summary is None:
        return {"candidate_index": identity.candidate_index,
                "candidate_seed": identity.candidate_seed,
                "episode": episode.episode_index,
                "queries": len(query_rows), "nodes": total_nodes,
                "actual_outcome": None, "ending": "OPEN_PREFIX",
                "final_record": env.record(),
                "final_weights": list(runtime.model.weights), "stats": None}

    ending = summary.get("ending")
    outcome = summary.get("actual_outcome")
    if ending not in {"ACTUAL_TERMINAL", "NON_SCORING_UNKNOWN", "HORIZON_UNKNOWN",
                      "NODE_CAP_UNKNOWN", "SEARCH_RESOURCE_UNKNOWN", "STOPPED_USER"}:
        raise ValueError("episode ending classification is unknown")
    if ending == "ACTUAL_TERMINAL":
        if (type(outcome) not in (int, float)
                or not math.isfinite(outcome) or outcome not in (-1, 0, 1)):
            raise ValueError("actual-terminal episode lacks a W/L/D outcome")
        try:
            observed = env.terminal()
        except NonScoringTerminal as exc:
            raise ValueError("actual-terminal episode replays to a non-scoring terminal") from exc
        if observed != outcome:
            raise ValueError("actual terminal outcome differs from the episode receipt")
    elif ending == "NON_SCORING_UNKNOWN":
        try:
            env.terminal()
        except NonScoringTerminal:
            pass
        else:
            raise ValueError("non-scoring UNKNOWN episode does not replay to that terminal")
    elif outcome is not None:
        raise ValueError("UNKNOWN episode carries a terminal reward")

    stats = runtime.learner.finish(runtime.model, outcome)
    if (summary.get("final_record") != env.record()
            or summary.get("nodes") != total_nodes
            or summary.get("final_weights") != list(runtime.model.weights)
            or summary.get("stats") != stats):
        raise ValueError("episode summary differs from independent prefix replay")
    return {"candidate_index": identity.candidate_index,
            "candidate_seed": identity.candidate_seed,
            "episode": episode.episode_index,
            "queries": len(query_rows), "nodes": total_nodes,
            "actual_outcome": outcome, "ending": ending,
            "final_weights": list(runtime.model.weights), "stats": stats}


def replay_closed_training_episode(
        runtime: CandidateArmRuntime, episode: TrainingEpisodeInput,
        summary: dict[str, Any],
        query_rows: tuple[dict[str, Any], ...] | list[dict[str, Any]],
        env: Any, *, decode_action: Callable[[Any], Any] = action_from_dict,
        verify_root_history: bool = True) -> dict[str, Any]:
    """Replay a closed episode; the generic prefix API also accepts no summary."""
    if not isinstance(summary, dict):
        raise ValueError("closed episode replay requires its durable summary")
    return replay_training_episode_prefix(
        runtime, episode, summary, query_rows, env, decode_action=decode_action,
        verify_root_history=verify_root_history)


def audit_candidate_training_arm_prefix(
        arm: CandidateArmInput, *, started_path: Path, query_path: Path,
        episode_path: Path, result_path: Path,
        environment_for_episode: Callable[[TrainingEpisodeInput], Any],
        max_episodes: int, decode_action: Callable[[Any], Any] = action_from_dict,
        verify_root_history: bool = True) -> dict[str, Any]:
    """Replay closed durable episodes and classify, but never repair, a tail.

    Only newline-terminated JSONL rows are considered. A final group of query
    rows without a matching episode summary is preserved as an unclosed
    episode prefix; its training updates are deliberately not credited. A
    missing/torn final receipt remains ``NO_FINAL_RECEIPT`` even when all
    currently visible episode rows replay successfully.
    """
    if type(max_episodes) is not int or max_episodes <= 0:
        raise ValueError("maximum episode count must be positive")
    if not callable(environment_for_episode):
        raise ValueError("episode environment factory is required")
    started_path, query_path = Path(started_path), Path(query_path)
    episode_path, result_path = Path(episode_path), Path(result_path)
    if not started_path.exists():
        if any(path.exists() for path in (query_path, episode_path, result_path)):
            raise ValueError("training rows or result exist without a start receipt")
        return {"status": "NOT_STARTED", "closed_episodes": 0,
                "replayed_episodes": 0, "trailing_query_rows": 0,
                "query_tail_bytes": 0, "episode_tail_bytes": 0,
                "final_receipt": "NOT_STARTED", "start_sha256": None,
                "query_sha256": None, "episode_sha256": None,
                "final_sha256": None}

    try:
        started_raw = started_path.read_bytes()
        if not started_raw.endswith(b"\n"):
            raise ValueError("start receipt is not newline terminated")
        started = _strict_json_loads(started_raw)
        if (not isinstance(started, dict)
                or started.get("status") != "STARTED"
                or started.get("candidate_index") != arm.candidate_index
                or started.get("candidate_seed") != arm.candidate_seed
                or started.get("candidate_ruleset_sha256") != arm.candidate_ruleset_sha256):
            raise ValueError("start receipt is not bound to this candidate arm")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("start receipt is malformed") from exc

    query_file_present, episode_file_present = query_path.exists(), episode_path.exists()
    query_raw = query_path.read_bytes() if query_file_present else None
    episode_raw = episode_path.read_bytes() if episode_file_present else None
    query_rows, query_tail = parse_newline_jsonl_prefix(query_raw or b"")
    episode_rows, episode_tail = parse_newline_jsonl_prefix(episode_raw or b"")
    scheduled = tuple(iter_training_episodes(arm, max_episodes=max_episodes))
    if len(episode_rows) > len(scheduled):
        raise ValueError("episode journal exceeds the frozen episode schedule")
    runtime = initialize_candidate_arm(arm)
    query_offset = 0
    total_nodes = actual_terminals = unknown_episodes = 0
    for index, summary in enumerate(episode_rows):
        episode = scheduled[index]
        query_count = summary.get("queries")
        if type(query_count) is not int or query_count < 0:
            raise ValueError("closed episode has an invalid query count")
        rows = query_rows[query_offset:query_offset + query_count]
        if len(rows) != query_count:
            raise ValueError("closed episode is missing one or more query rows")
        replayed = replay_closed_training_episode(
            runtime, episode, summary, rows,
            environment_for_episode(episode), decode_action=decode_action,
            verify_root_history=verify_root_history)
        query_offset += query_count
        total_nodes += replayed["nodes"]
        actual_terminals += int(replayed["actual_outcome"] is not None)
        unknown_episodes += int(replayed["actual_outcome"] is None)

    trailing = query_rows[query_offset:]
    trailing_nodes = 0
    if trailing:
        episode = scheduled[len(episode_rows)] if len(episode_rows) < len(scheduled) else None
        if episode is None:
            raise ValueError("query journal exceeds the frozen episode schedule")
        incomplete_seen = False
        for ply, row in enumerate(trailing):
            if (not isinstance(row, dict)
                    or row.get("candidate_index") != arm.candidate_index
                    or row.get("candidate_seed") != arm.candidate_seed
                    or row.get("episode") != episode.episode_index
                    or row.get("root_family") != episode.root.get("family")
                    or row.get("root_record_sha256") != episode.root.get("record_sha256")
                    or row.get("learner_color") != episode.learner_color
                    or row.get("ply") != ply or incomplete_seen):
                raise ValueError("unclosed query suffix is not a contiguous next-episode prefix")
            if row.get("complete") is not True:
                if row.get("complete") is not False or row.get("record_after") != row.get("record_before"):
                    raise ValueError("incomplete unclosed query changed game history")
                incomplete_seen = True
        replayed_prefix = replay_training_episode_prefix(
            runtime, episode, None, trailing, environment_for_episode(episode),
            decode_action=decode_action, verify_root_history=verify_root_history)
        trailing_nodes = replayed_prefix["nodes"]

    final_raw = result_path.read_bytes() if result_path.exists() else None
    final_exists = final_raw is not None
    final_rows: tuple[dict[str, Any], ...] = ()
    final_tail = b""
    final_status = "NO_FINAL_RECEIPT"
    if final_raw is not None:
        try:
            final_rows, final_tail = parse_newline_jsonl_prefix(final_raw)
            if (not final_tail and len(final_rows) == 1
                    and isinstance(final_rows[0].get("status"), str)):
                final_status = final_rows[0]["status"]
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            pass
    final_receipt_state = ("MISSING" if not final_exists else
                           "TORN_OR_INVALID" if final_status == "NO_FINAL_RECEIPT" else
                           final_status)
    final_tail_bytes = len(final_tail)
    if final_exists and final_status == "NO_FINAL_RECEIPT":
        final_receipt_state = "TORN_OR_INVALID"
    if final_status != "NO_FINAL_RECEIPT":
        if final_tail or len(final_rows) != 1 or trailing or query_tail or episode_tail:
            raise ValueError("final receipt conflicts with an open or torn journal prefix")
        final = final_rows[0]
        counters = ("episodes", "combined_candidate_and_foe_nodes",
                    "actual_terminals", "unknown_episodes")
        weights = final.get("final_weights")
        if (final.get("status") not in {"STOPPED_USER", "NODE_CAP", "EPISODE_LIMIT"}
                or type(final.get("candidate_index")) is not int
                or final.get("candidate_index") != arm.candidate_index
                or type(final.get("candidate_seed")) is not int
                or final.get("candidate_seed") != arm.candidate_seed
                or final.get("candidate_ruleset_sha256") != arm.candidate_ruleset_sha256
                or any(type(final.get(key)) is not int for key in counters)
                or final.get("episodes") != len(episode_rows)
                or final.get("combined_candidate_and_foe_nodes") != total_nodes
                or final.get("actual_terminals") != actual_terminals
                or final.get("unknown_episodes") != unknown_episodes
                or type(weights) is not list or len(weights) != len(runtime.model.weights)
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in weights)
                or weights != list(runtime.model.weights)):
            raise ValueError("final receipt does not match the replayed closed prefix")

    status = final_status
    if status == "NO_FINAL_RECEIPT" and (query_tail or episode_tail):
        status = "NO_FINAL_RECEIPT_TORN_PREFIX"
    elif status == "NO_FINAL_RECEIPT" and trailing:
        status = "NO_FINAL_RECEIPT_OPEN_EPISODE"
    return {"status": status, "closed_episodes": len(episode_rows),
            "replayed_episodes": len(episode_rows), "trailing_query_rows": len(trailing),
            "query_tail_bytes": len(query_tail), "episode_tail_bytes": len(episode_tail),
            "replayed_nodes": total_nodes, "actual_terminals": actual_terminals,
            "unknown_episodes": unknown_episodes, "final_receipt": final_receipt_state,
            "final_tail_bytes": final_tail_bytes,
            "replayed_open_queries": len(trailing),
            "open_query_nodes": trailing_nodes,
            "query_file_present": query_file_present,
            "episode_file_present": episode_file_present,
            "start_sha256": hashlib.sha256(started_raw).hexdigest(),
            "query_sha256": hashlib.sha256(query_raw).hexdigest() if query_raw is not None else None,
            "episode_sha256": hashlib.sha256(episode_raw).hexdigest() if episode_raw is not None else None,
            "final_sha256": hashlib.sha256(final_raw).hexdigest() if final_raw is not None else None}


def iter_training_episodes(
        arm: CandidateArmInput, *, max_episodes: int) -> Iterator[TrainingEpisodeInput]:
    """Yield the pinned cyclic-root, alternating-color schedule for one arm.

    This is a pure input schedule: it performs no search, learning, writes, or
    stop handling. The caller owns those runtime and durable-closure contracts.
    """
    if type(max_episodes) is not int or max_episodes <= 0:
        raise ValueError("maximum episode count must be a positive integer")
    if not arm.roots:
        raise ValueError("candidate arm has no training roots")
    for episode in range(max_episodes):
        yield TrainingEpisodeInput(
            candidate_index=arm.candidate_index,
            candidate_seed=arm.candidate_seed,
            episode_index=episode,
            root=arm.roots[episode % len(arm.roots)],
            learner_color=episode % 2,
        )


def replay_training_root(
        episode: TrainingEpisodeInput, compiled_ruleset: Any, *,
        environment_factory: Callable[[GameSession], Any] = FixedScaleSessionEnv) -> Any:
    """Reconstruct one saved complete-history root and verify exact replay."""
    validate_root_record_binding(episode.root)
    record = episode.root.get("record")
    if not isinstance(record, dict):
        raise ValueError("candidate training root has no game record")
    try:
        env = environment_factory(GameSession.replay(
            compiled_ruleset,
            deserialize_game_record(json.dumps(record, sort_keys=True, separators=(",", ":"))),
        ))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("candidate training root failed exact complete-history replay") from exc
    if env.record() != record:
        raise ValueError("candidate training root failed exact complete-history replay")
    return env


def build_candidate_arm_inputs(
        plan: dict[str, Any], candidate_index: dict[str, Any],
        root_pool: dict[str, Any], *,
        initial_vector: Callable[[int, int], list[float]]) -> tuple[CandidateArmInput, ...]:
    """Build arms in positional candidate order, preserving seed identities.

    Callers must verify source bytes against the frozen plan before invoking
    this function. Candidate index is an array position; ``candidate_seed``
    identifies rule generation; the model's initialization seed comes from the
    training plan and is never used as an arm key.
    """
    training = plan.get("training")
    if not isinstance(training, dict):
        raise ValueError("frozen plan has no training object")
    rows = candidate_index.get("rows")
    count = training.get("arms")
    if (type(count) is not int or type(rows) is not list or len(rows) != count
            or type(training.get("roots_per_rule")) is not int):
        raise ValueError("candidate index, arm count, or root count is malformed")
    if root_pool.get("root_pool_registered") or root_pool.get("learner_or_search_started"):
        raise ValueError("candidate arm construction requires unregistered frozen roots")
    if (training.get("initialization_seeds") != [1977]
            or training.get("roots_per_rule") <= 0
            or training.get("combined_candidate_plus_foe_node_cap_per_rule", 0) <= 0):
        raise ValueError("candidate training initialization or budget contract changed")

    by_candidate: dict[int, list[dict[str, Any]]] = {i: [] for i in range(count)}
    training_roots = root_pool.get("training_roots")
    if type(training_roots) is not list:
        raise ValueError("frozen training roots must be an array")
    if len(training_roots) != count * training["roots_per_rule"]:
        raise ValueError("frozen training root pool has an unexpected total size")
    for root in training_roots:
        if not isinstance(root, dict):
            raise ValueError("training root must be an object")
        index = root.get("candidate_index")
        if type(index) is not int or index not in by_candidate:
            raise ValueError("training root has an unplanned candidate index")
        by_candidate[index].append(root)

    arms: list[CandidateArmInput] = []
    seen_generation_seeds: set[int] = set()
    shared_initial_weights: tuple[float, ...] | None = None
    for index, candidate in enumerate(rows):
        if not isinstance(candidate, dict):
            raise ValueError("candidate index row must be an object")
        seed = candidate.get("seed")
        rule_sha = candidate.get("ruleset_sha256")
        rule_path = candidate.get("source_file")
        if (type(seed) is not int or seed in seen_generation_seeds
                or candidate.get("status") != "GENERATED_AND_COMPILED"):
            raise ValueError("candidate generation identity or status is invalid")
        if not isinstance(rule_sha, str) or re.fullmatch(r"[0-9a-f]{64}", rule_sha) is None:
            raise ValueError("candidate rule hash is malformed")
        if not isinstance(rule_path, str) or not rule_path:
            raise ValueError("candidate rule source path is missing")
        seen_generation_seeds.add(seed)

        roots = by_candidate[index]
        if len(roots) != training["roots_per_rule"]:
            raise ValueError(f"candidate {index}: frozen training root count mismatch")
        families: set[int] = set()
        for root in roots:
            if (root.get("candidate_seed") != seed
                    or root.get("rule_sha256") != rule_sha
                    or root.get("rule_path") != rule_path):
                raise ValueError(f"candidate {index}: root identity differs from candidate index")
            try:
                validate_root_record_binding(root)
            except ValueError as exc:
                raise ValueError(f"candidate {index}: {exc}") from exc
            family = root.get("family")
            if type(family) is not int or family in families:
                raise ValueError(f"candidate {index}: root family is invalid or duplicated")
            families.add(family)
            channels = root.get("channels")
            if (type(channels) is not list
                    or tuple(tuple(pair) if type(pair) is list else () for pair in channels)
                    != FROZEN_CHANNELS):
                raise ValueError(f"candidate {index}: root channel order differs from frozen schema")
            features = root.get("features")
            if (type(features) is not list or len(features) != len(FROZEN_CHANNELS)
                    or any(type(value) not in (int, float) or not math.isfinite(value)
                           for value in features)):
                raise ValueError(f"candidate {index}: root feature vector is malformed")

        weights = initial_vector(1977, 10)
        if (type(weights) is not list or len(weights) != 10
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in weights)
                or weights[0] != 1.0):
            raise ValueError("pinned learner initialization violates the fixed ten-weight contract")
        frozen_weights = tuple(weights)
        if shared_initial_weights is None:
            shared_initial_weights = frozen_weights
        elif frozen_weights != shared_initial_weights:
            raise ValueError("candidate arms do not share the frozen initialization vector")
        arms.append(CandidateArmInput(index, seed, rule_sha, rule_path,
                                      tuple(roots), frozen_weights))

    return tuple(arms)
