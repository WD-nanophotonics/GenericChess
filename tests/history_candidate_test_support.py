"""Test-only pure evaluation of verified repeated-cycle capture facts.

The result labels are factual fixture classifications only. This helper is
not a production API and does not classify chase, response intent, or rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from generic_chess.core.capture_pressure_trace import NextTurnLegalCaptureFact
from generic_chess.core.history_cycle_trace import (
    CaptureEdgeResponseFact,
    RepeatedPositionCycleTrace,
)
from generic_chess.core.history_provenance import PieceInstanceId


@dataclass(frozen=True, slots=True)
class CaptureCandidatePlyEvidence:
    """All source-token capture edges observed after one source-owner ply."""

    frame_ply: int
    capture_facts: tuple[NextTurnLegalCaptureFact, ...]
    response_facts: tuple[CaptureEdgeResponseFact, ...]


@dataclass(frozen=True, slots=True)
class RepeatedCycleCaptureCandidate:
    """Three-way, evidence-preserving result for one requested token pair."""

    status: Literal["candidate", "not_candidate", "unknown"]
    source_token: PieceInstanceId
    target_token: PieceInstanceId
    start_ply: int | None = None
    end_ply: int | None = None
    evidence: tuple[CaptureCandidatePlyEvidence, ...] = ()
    reason: str | None = None


def extract_repeated_cycle_capture_candidate(
    trace: RepeatedPositionCycleTrace,
    source_token: PieceInstanceId,
    target_token: PieceInstanceId,
) -> RepeatedCycleCaptureCandidate:
    """Assess a same-token legal-capture candidate without assigning meaning.

    A candidate needs at least two attacker turns in the verified repeat
    window. On every such turn the requested source/target edge must be
    present, and after its actual (or identity-safe wrapped) reply the exact
    edge must no longer be legally capturable. A known missing edge or a still
    legal capture is ``not_candidate``; missing or unsupported evidence is
    ``unknown``. Other target edges are retained in the per-ply evidence.
    """
    if trace.status != "verified":
        return RepeatedCycleCaptureCandidate(
            "unknown", source_token, target_token, reason=trace.reason
        )
    cycle = trace.cycle
    if cycle is None:
        return RepeatedCycleCaptureCandidate(
            "unknown", source_token, target_token,
            reason="verified history has no repeated current position",
        )

    source_edges = tuple(
        fact for fact in cycle.capture_facts
        if fact.source_token == source_token
    )
    if not source_edges:
        return RepeatedCycleCaptureCandidate(
            "not_candidate", source_token, target_token,
            cycle.start_ply, cycle.end_ply,
            reason="source token has no legal-capture edges in the repeat window",
        )
    actors = {fact.actor for fact in source_edges}
    if len(actors) != 1:
        return RepeatedCycleCaptureCandidate(
            "unknown", source_token, target_token,
            cycle.start_ply, cycle.end_ply,
            reason="one source token is associated with inconsistent actors",
        )
    attacker = next(iter(actors))
    attack_plies = tuple(
        ply for ply, actor in cycle.action_actors if actor == attacker
    )

    evidence = []
    known_failure = len(attack_plies) < 2
    missing_evidence = False
    for ply in attack_plies:
        ply_edges = tuple(fact for fact in source_edges if fact.frame_ply == ply)
        ply_responses = tuple(
            response for response in cycle.response_facts
            if response.threat_frame_ply == ply
            and response.source_token == source_token
        )
        evidence.append(
            CaptureCandidatePlyEvidence(ply, ply_edges, ply_responses)
        )
        target_edges = tuple(
            fact for fact in ply_edges if fact.target_token == target_token
        )
        if not target_edges:
            known_failure = True
            continue
        response = next(
            (
                item for item in ply_responses
                if item.target_token == target_token
            ),
            None,
        )
        if response is None:
            missing_evidence = True
            continue
        if (
            response.target_moved is None
            or response.specific_capture_still_legal is None
        ):
            missing_evidence = True
        elif response.specific_capture_still_legal:
            known_failure = True

    if known_failure:
        status: Literal["candidate", "not_candidate", "unknown"] = "not_candidate"
        reason = "a source-owner turn lacks the same resolved legal-capture edge"
    elif missing_evidence:
        status = "unknown"
        reason = "one or more cycle responses lack verified evidence"
    else:
        status = "candidate"
        reason = None
    return RepeatedCycleCaptureCandidate(
        status,
        source_token,
        target_token,
        cycle.start_ply,
        cycle.end_ply,
        tuple(evidence),
        reason,
    )
