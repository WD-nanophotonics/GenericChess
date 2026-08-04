"""RuleSet JSON serialization and deserialization."""

from __future__ import annotations

import json

from .schema import RuleSet, canonical_json, ruleset_from_dict, ruleset_to_dict
from .validation import RuleValidationError, ValidationIssue


def serialize_ruleset(ruleset: RuleSet) -> str:
    """Canonical JSON string (stable across runs, includes metadata)."""
    return canonical_json(ruleset_to_dict(ruleset, include_metadata=True))


def deserialize_ruleset(data: str) -> RuleSet:
    """Parse a JSON string produced by :func:`serialize_ruleset`."""
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise RuleValidationError(
            [ValidationIssue("INVALID_JSON", "ruleset", f"invalid JSON: {exc}")]
        ) from exc
    return ruleset_from_dict(payload)
