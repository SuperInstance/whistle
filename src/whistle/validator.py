"""
Whistle validator — checks referential integrity of a WhistleProgram.

Validates:
    - Required fields present
    - breed is known (or flagged as custom)
    - pasture is a non-empty string
    - fence path is well-formed
    - rotate is a valid Schedule
    - recall is a valid Trigger
    - No unknown fields (warns)
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from .parser import WhistleProgram, WhistleStatement, Schedule, Trigger
from .compiler import _KNOWN_BREEDS


@dataclass
class FieldIssue:
    level: str  # "error" | "warning"
    whistle: str
    field: str
    message: str


@dataclass
class ValidationResult:
    """Result of validating a WhistleProgram."""

    valid: bool
    errors: list[FieldIssue] = dc_field(default_factory=list)
    warnings: list[FieldIssue] = dc_field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


# Known field names — anything else triggers a warning.
_KNOWN_FIELDS = {
    "breed",
    "pasture",
    "fence",
    "herd",
    "rotate",
    "recall",
    "flank",
    "drive",
    "stock",
}

_REQUIRED_FIELDS = {"breed"}


def validate(program: WhistleProgram) -> ValidationResult:
    """
    Validate all whistle statements in the program.

    Returns a ValidationResult with errors (blocking) and warnings (non-blocking).
    """
    errors: list[FieldIssue] = []
    warnings: list[FieldIssue] = []

    for stmt in program.statements:
        _validate_statement(stmt, errors, warnings)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _validate_statement(
    stmt: WhistleStatement,
    errors: list[FieldIssue],
    warnings: list[FieldIssue],
) -> None:
    # Check required fields
    present_keys = {f.key for f in stmt.fields}

    for req in _REQUIRED_FIELDS:
        if req not in present_keys:
            errors.append(FieldIssue(
                level="error",
                whistle=stmt.name,
                field=req,
                message=f"Missing required field '{req}'",
            ))

    # Check field types
    for f in stmt.fields:
        if f.key not in _KNOWN_FIELDS:
            warnings.append(FieldIssue(
                level="warning",
                whistle=stmt.name,
                field=f.key,
                message=f"Unknown field '{f.key}' — will be ignored",
            ))

        # Type-specific validation
        if f.key == "breed":
            if not isinstance(f.value, str):
                errors.append(FieldIssue("error", stmt.name, "breed", "breed must be a string"))
            elif f.value not in _KNOWN_BREEDS:
                warnings.append(FieldIssue(
                    "warning", stmt.name, "breed",
                    f"Unknown breed '{f.value}' — treating as custom model",
                ))

        elif f.key == "pasture":
            if not isinstance(f.value, str) or not f.value:
                errors.append(FieldIssue("error", stmt.name, "pasture", "pasture must be a non-empty string"))

        elif f.key == "fence":
            if not isinstance(f.value, str):
                errors.append(FieldIssue("error", stmt.name, "fence", "fence must be a string path"))
            elif "/" not in f.value and "\\" not in f.value and not f.value.endswith(".bin"):
                warnings.append(FieldIssue(
                    "warning", stmt.name, "fence",
                    f"fence '{f.value}' doesn't look like a path",
                ))

        elif f.key == "herd":
            if not isinstance(f.value, str) or not f.value:
                errors.append(FieldIssue("error", stmt.name, "herd", "herd must be a non-empty string"))

        elif f.key == "rotate":
            if not isinstance(f.value, (Schedule, str)):
                errors.append(FieldIssue("error", stmt.name, "rotate", "rotate must be a schedule"))

        elif f.key == "recall":
            if not isinstance(f.value, (Trigger, str)):
                errors.append(FieldIssue("error", stmt.name, "recall", "recall must be a trigger"))

        elif f.key == "drive":
            if isinstance(f.value, str) and f.value not in ("inbound", "outbound"):
                warnings.append(FieldIssue(
                    "warning", stmt.name, "drive",
                    f"drive should be 'inbound' or 'outbound', got '{f.value}'",
                ))

        elif f.key == "flank":
            if not isinstance(f.value, str):
                errors.append(FieldIssue("error", stmt.name, "flank", "flank must be a string"))

        elif f.key == "stock":
            if not isinstance(f.value, (str, int)):
                errors.append(FieldIssue("error", stmt.name, "stock", "stock must be a string or int"))
