"""
Whistle DSL parser.

Grammar (informal):

    program     := statement+
    statement   := 'whistle' IDENT '{' field* '}'
    field       := key ':' value (',' | newline)
    key         := IDENT
    value       := STRING | SCHEDULE | TRIGGER | IDENT | NUMBER
    SCHEDULE    := 'every_' NUMBER ('min' | 'hours' | 'hours_at' TIME)
    TRIGGER     := 'on_' IDENT
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Union

# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------


@dataclass
class WhistleField:
    """A single key: value pair inside a whistle block."""

    key: str
    value: Any  # str | int | Schedule | Trigger
    line: int = 0


@dataclass
class WhistleStatement:
    """A complete `whistle name { ... }` block."""

    name: str
    fields: list[WhistleField] = dc_field(default_factory=list)
    line: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        for f in self.fields:
            if f.key == key:
                return f.value
        return default


@dataclass
class WhistleProgram:
    """A parsed whistle file — one or more whistle statements."""

    statements: list[WhistleStatement] = dc_field(default_factory=list)

    def find(self, name: str) -> WhistleStatement | None:
        for s in self.statements:
            if s.name == name:
                return s
        return None


@dataclass
class Schedule:
    """Parsed rotation schedule."""

    raw: str
    interval_seconds: int
    kind: str = "interval"  # "interval" | "daily"
    at_time: str | None = None  # "HH:MM" for daily


@dataclass
class Trigger:
    """Parsed recall trigger."""

    raw: str
    event: str


# ---------------------------------------------------------------------------
# Tokenizer helpers
# ---------------------------------------------------------------------------

_STRING_RE = re.compile(r'"([^"]*)"')
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_NUMBER_RE = re.compile(r"\d+")
_COMMENT_RE = re.compile(r"#.*$")


def _strip_comments(source: str) -> str:
    """Remove # comments."""
    lines = []
    for line in source.splitlines():
        lines.append(_COMMENT_RE.sub("", line))
    return "\n".join(lines)


def _parse_schedule(raw: str, line: int) -> Schedule:
    """Parse schedule tokens like `every_30_min`, `every_2_hours`, `every_day_at_09:00`."""
    token = raw.strip()

    # every_day_at_HH:MM
    m = re.match(r"every_day_at_(\d{2}:\d{2})$", token)
    if m:
        return Schedule(raw=token, interval_seconds=86400, kind="daily", at_time=m.group(1))

    # every_N_min
    m = re.match(r"every_(\d+)_min$", token)
    if m:
        n = int(m.group(1))
        return Schedule(raw=token, interval_seconds=n * 60)

    # every_N_hours
    m = re.match(r"every_(\d+)_hours$", token)
    if m:
        n = int(m.group(1))
        return Schedule(raw=token, interval_seconds=n * 3600)

    # Fallback — treat as opaque interval, try to extract a number.
    m = re.match(r"every_(\d+)_?(\w+)?$", token)
    if m:
        n = int(m.group(1))
        unit = (m.group(2) or "min").lower()
        multiplier = 3600 if unit.startswith("hour") else 60
        return Schedule(raw=token, interval_seconds=n * multiplier)

    raise SyntaxError(f"Unparseable schedule '{raw}' on line {line}")


def _parse_trigger(raw: str, line: int) -> Trigger:
    """Parse on_* trigger tokens."""
    token = raw.strip()
    if not token.startswith("on_"):
        raise SyntaxError(f"Invalid trigger '{raw}' on line {line} — must start with 'on_'")
    event = token[3:]  # strip "on_"
    return Trigger(raw=token, event=event)


def _is_schedule(token: str) -> bool:
    return token.startswith("every_")


def _is_trigger(token: str) -> bool:
    return token.startswith("on_")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class _Cursor:
    """Simple line-tracking cursor over a string."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1

    def peek(self) -> str:
        if self.pos >= len(self.text):
            return ""
        return self.text[self.pos]

    def advance(self) -> str:
        ch = self.peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def skip_ws(self) -> None:
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch in " \t\r\n":
                self.advance()
            else:
                break

    def match(self, expected: str) -> bool:
        """Consume exact string if it matches (after whitespace)."""
        self.skip_ws()
        if self.text[self.pos : self.pos + len(expected)] == expected:
            for _ in expected:
                self.advance()
            return True
        return False

    def error(self, msg: str) -> SyntaxError:
        return SyntaxError(f"{msg} on line {self.line}")


def parse(source: str) -> WhistleProgram:
    """
    Parse a whistle DSL source string into a WhistleProgram.

    Raises SyntaxError on malformed input.
    """
    source = _strip_comments(source)
    cur = _Cursor(source)
    statements: list[WhistleStatement] = []

    while True:
        cur.skip_ws()
        if cur.pos >= len(cur.text):
            break

        stmt = _parse_statement(cur)
        if stmt:
            statements.append(stmt)

    return WhistleProgram(statements=statements)


def _parse_statement(cur: _Cursor) -> WhistleStatement:
    """Parse a single `whistle NAME { ... }` block."""
    cur.skip_ws()

    # Expect 'whistle' keyword
    if not cur.match("whistle"):
        raise cur.error("Expected 'whistle' keyword")

    cur.skip_ws()
    # Read identifier
    m = _IDENT_RE.match(cur.text, cur.pos)
    if not m:
        raise cur.error("Expected whistle name after 'whistle'")
    name = m.group(0)
    for _ in name:
        cur.advance()

    stmt = WhistleStatement(name=name, line=cur.line)

    cur.skip_ws()
    if not cur.match("{"):
        raise cur.error(f"Expected '{{' after whistle name '{name}'")

    # Parse fields until '}'
    while True:
        cur.skip_ws()
        if cur.peek() == "}":
            cur.advance()
            break
        if cur.pos >= len(cur.text):
            raise cur.error("Unterminated whistle block — missing '}'")

        fld = _parse_field(cur)
        if fld:
            stmt.fields.append(fld)

        # Consume optional comma
        cur.skip_ws()
        if cur.peek() == ",":
            cur.advance()

    return stmt


def _parse_field(cur: _Cursor) -> WhistleField | None:
    """Parse `key: value` (with optional trailing comma)."""
    cur.skip_ws()

    # Read key
    m = _IDENT_RE.match(cur.text, cur.pos)
    if not m:
        if cur.peek() == "}":
            return None
        raise cur.error("Expected field key")
    key = m.group(0)
    for _ in key:
        cur.advance()

    cur.skip_ws()
    if not cur.match(":"):
        raise cur.error(f"Expected ':' after field key '{key}'")

    cur.skip_ws()
    value, line = _parse_value(cur)

    return WhistleField(key=key, value=value, line=line)


def _parse_value(cur: _Cursor) -> tuple[Any, int]:
    """Parse a single value token. Returns (value, line)."""
    cur.skip_ws()
    line = cur.line
    ch = cur.peek()

    # String literal
    if ch == '"':
        cur.advance()  # opening quote
        chars: list[str] = []
        while cur.peek() and cur.peek() != '"':
            chars.append(cur.advance())
        if cur.peek() != '"':
            raise cur.error("Unterminated string literal")
        cur.advance()  # closing quote
        return "".join(chars), line

    # Number
    m = _NUMBER_RE.match(cur.text, cur.pos)
    if m:
        num_str = m.group(0)
        for _ in num_str:
            cur.advance()
        return int(num_str), line

    # Bare identifier — could be schedule, trigger, or plain keyword
    m = _IDENT_RE.match(cur.text, cur.pos)
    if m:
        token = m.group(0)
        for _ in token:
            cur.advance()

        if _is_schedule(token):
            # Schedules like every_day_at_HH:MM contain a colon the ident regex
            # won't capture — check for a trailing :MM and append it.
            if cur.peek() == ":":
                # Consume colon + the two-digit minutes portion.
                cur.advance()  # colon
                m2 = re.match(r"\d{2}", cur.text[cur.pos:])
                if m2:
                    for _ in m2.group(0):
                        cur.advance()
                    token = token + ":" + m2.group(0)
            return _parse_schedule(token, line), line
        if _is_trigger(token):
            return _parse_trigger(token, line), line
        return token, line

    raise cur.error(f"Unexpected character '{ch}'")
