"""Pure path and compute-budget validation; no workflow control."""
from pathlib import Path
import re
from typing import Any

class ResourceLimitError(RuntimeError):
    pass


COMPUTE_ENVELOPE_SCHEMA = "generic-chess-resource-envelope-v1"

RESOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

def repo_relative_path(root: Path, path: str | Path) -> str:
    """Return a repository-relative POSIX path, rejecting paths outside root."""
    repository = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repository / candidate
    try:
        return candidate.resolve().relative_to(repository).as_posix()
    except ValueError as exc:
        raise ResourceLimitError(f"path is outside the repository: {path}") from exc

def _validate_resource_envelope(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema", "envelope_id", "logical_cpu_count", "intended_cpu_lanes",
        "expected_wall_minutes", "hard_wall_minutes", "expected_cpu_hours",
        "hard_cpu_hours", "arena_pairs", "maximum_games", "maximum_nodes",
        "maximum_plies", "maximum_concurrent_games", "stage_count",
    }
    if value.get("schema") != COMPUTE_ENVELOPE_SCHEMA or not required.issubset(value):
        raise ResourceLimitError("resource envelope is missing required fields")
    if not RESOURCE_ID.fullmatch(str(value["envelope_id"])):
        raise ResourceLimitError("resource envelope id is invalid")
    for key in (
        "logical_cpu_count", "intended_cpu_lanes", "hard_wall_minutes",
        "hard_cpu_hours", "arena_pairs", "maximum_games", "maximum_nodes",
        "maximum_plies", "maximum_concurrent_games", "stage_count",
    ):
        if not isinstance(value[key], int) or value[key] <= 0:
            raise ResourceLimitError(f"resource envelope field is invalid: {key}")
    for key in ("expected_wall_minutes", "expected_cpu_hours"):
        if value[key] is not None and (
            not isinstance(value[key], (int, float)) or value[key] < 0
        ):
            raise ResourceLimitError(f"resource envelope field is invalid: {key}")
    if value["intended_cpu_lanes"] > value["maximum_concurrent_games"]:
        raise ResourceLimitError("resource envelope lanes exceed concurrent-game cap")
    if value["maximum_concurrent_games"] > value["logical_cpu_count"]:
        raise ResourceLimitError("resource envelope concurrency exceeds declared CPU")
    if value["expected_wall_minutes"] is not None and value["expected_wall_minutes"] > value["hard_wall_minutes"]:
        raise ResourceLimitError("resource envelope wall estimate exceeds hard ceiling")
    if value["expected_cpu_hours"] is not None and value["expected_cpu_hours"] > value["hard_cpu_hours"]:
        raise ResourceLimitError("resource envelope CPU estimate exceeds hard ceiling")
    return value
