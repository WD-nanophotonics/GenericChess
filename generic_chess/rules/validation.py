"""Structured validation errors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One structured validation problem.

    ``path`` is a human-readable field path such as
    ``piece_types[0].movement_atoms[1].direction``.
    """

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.path}: {self.message}"


class RuleValidationError(ValueError):
    """Raised by the compiler when a RuleSet is invalid.

    All discovered issues are collected before raising so the caller sees the
    full list instead of one error at a time.
    """

    def __init__(self, issues: list[ValidationIssue] | tuple[ValidationIssue, ...]):
        self.issues: tuple[ValidationIssue, ...] = tuple(issues)
        if not self.issues:
            raise ValueError("RuleValidationError requires at least one issue")
        super().__init__("; ".join(str(i) for i in self.issues))
