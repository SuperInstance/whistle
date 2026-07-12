"""
Whistle compiler — transforms WhistleProgram AST into deployment-ready config dicts.

Compilation targets:
    - plato:       Room configuration for PLATO
    - conservation:Fence policy for conservation enforcers
    - flux:        Registry entry for model routing
    - schedule:    Interval / cron schedule
    - recall:      Recall signal wiring
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from .parser import (
    WhistleProgram,
    WhistleStatement,
    Schedule,
    Trigger,
)


@dataclass
class CompiledConfig:
    """Result of compiling a single whistle statement."""

    name: str
    plato: dict[str, Any] = dc_field(default_factory=dict)
    conservation: dict[str, Any] = dc_field(default_factory=dict)
    flux: dict[str, Any] = dc_field(default_factory=dict)
    schedule: dict[str, Any] = dc_field(default_factory=dict)
    recall: dict[str, Any] = dc_field(default_factory=dict)
    raw: dict[str, Any] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Flatten into a single config dict."""
        return {
            "name": self.name,
            "plato": self.plato,
            "conservation": self.conservation,
            "flux": self.flux,
            "schedule": self.schedule,
            "recall": self.recall,
            "raw": self.raw,
        }


# ---------------------------------------------------------------------------
# Default maps
# ---------------------------------------------------------------------------

# Known model breeds with default flux routing params.
_KNOWN_BREEDS: dict[str, dict[str, Any]] = {
    "gpt-4": {"provider": "openai", "context_window": 128_000, "family": "gpt-4"},
    "gpt-4o": {"provider": "openai", "context_window": 128_000, "family": "gpt-4o"},
    "gpt-4-turbo": {"provider": "openai", "context_window": 128_000, "family": "gpt-4"},
    "claude-3-opus": {"provider": "anthropic", "context_window": 200_000, "family": "claude-3"},
    "claude-3-sonnet": {"provider": "anthropic", "context_window": 200_000, "family": "claude-3"},
    "claude-3-haiku": {"provider": "anthropic", "context_window": 200_000, "family": "claude-3"},
    "gemini-pro": {"provider": "google", "context_window": 1_000_000, "family": "gemini"},
    "gemini-1.5-pro": {"provider": "google", "context_window": 2_000_000, "family": "gemini"},
    "llama-3-70b": {"provider": "meta", "context_window": 8_000, "family": "llama-3"},
    "mistral-large": {"provider": "mistral", "context_window": 32_000, "family": "mistral"},
}


def compile(program: WhistleProgram) -> dict[str, Any]:
    """
    Compile a WhistleProgram into a dictionary of named CompiledConfig objects.

    Returns:
        {"whistles": {name: config_dict, ...}}
    """
    compiled: dict[str, Any] = {}
    for stmt in program.statements:
        cc = _compile_statement(stmt)
        compiled[cc.name] = cc.to_dict()
    return {"whistles": compiled}


def compile_one(stmt: WhistleStatement) -> CompiledConfig:
    """Compile a single whistle statement."""
    return _compile_statement(stmt)


def _compile_statement(stmt: WhistleStatement) -> CompiledConfig:
    cc = CompiledConfig(name=stmt.name)

    # Gather raw values
    raw: dict[str, Any] = {}
    for f in stmt.fields:
        if isinstance(f.value, Schedule):
            raw[f.key] = f.value.raw
        elif isinstance(f.value, Trigger):
            raw[f.key] = f.value.raw
        else:
            raw[f.key] = f.value
    cc.raw = raw

    # --- PLATO room config ---
    breed = stmt.get("breed", "gpt-4")
    pasture = stmt.get("pasture")
    herd = stmt.get("herd")
    cc.plato = {
        "room": pasture or stmt.name,
        "model": breed,
        "corpus": herd,
        "drive": stmt.get("drive", "inbound"),
    }

    # --- Conservation fence ---
    fence = stmt.get("fence")
    if fence:
        cc.conservation = {
            "policy_file": fence,
            "enforcer": "conservation.BudgetDecay",
            "defaults": {"max_tokens_per_turn": 4096},
        }
    else:
        cc.conservation = {"enforcer": None}

    # --- Flux registry ---
    breed_info = _KNOWN_BREEDS.get(breed, {"provider": "unknown", "context_window": 8192, "family": "custom"})
    flank = stmt.get("flank")
    stock = stmt.get("stock")

    flux_entry: dict[str, Any] = {
        "breed": breed,
        "routing": {
            "provider": breed_info["provider"],
            "family": breed_info["family"],
            "context_window": breed_info["context_window"],
        },
    }
    if flank:
        flux_entry["preprocessor"] = flank
    if stock:
        flux_entry["stock_ratio"] = stock
    cc.flux = flux_entry

    # --- Schedule ---
    rotate = stmt.get("rotate")
    if isinstance(rotate, Schedule):
        cc.schedule = {
            "type": rotate.kind,
            "interval_seconds": rotate.interval_seconds,
            "raw": rotate.raw,
            **({"at_time": rotate.at_time} if rotate.at_time else {}),
        }
    elif isinstance(rotate, str):
        # Opaque schedule string — pass through.
        cc.schedule = {"type": "custom", "raw": rotate}
    else:
        cc.schedule = {"type": "none"}

    # --- Recall ---
    recall = stmt.get("recall")
    if isinstance(recall, Trigger):
        cc.recall = {
            "trigger": recall.event,
            "action": "halt_and_return",
            "raw": recall.raw,
        }
    elif isinstance(recall, str):
        cc.recall = {"trigger": recall, "action": "halt_and_return"}
    else:
        cc.recall = {"trigger": None}

    return cc
