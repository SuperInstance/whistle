# Whistle — Intent DSL for Working Animal Architecture

> Replaces system-prompt sprawl with structured, compiled commands. The shepherd's language for the flock.

[![Python](https://img.shields.io/python/required-version-toml?toml=pyproject.toml)](https://python.org)
[![License](https://img.shields.io/github/license/SuperInstance/whistle)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)

System prompts are the assembly language of LLM orchestration — verbose, unstructured, and impossible to validate. A 500-word paragraph telling a model how to behave is the state of the art, and it's not good enough. Whistle replaces this with a declarative DSL: seven lines of structured configuration that compile down to the infrastructure configs your system already understands. You write a whistle program; the compiler produces PLATO room configs, conservation fence policies, flux registry entries, and schedule triggers.

## What It Does

Whistle is a domain-specific language for expressing working animal infrastructure as code. A whistle program declares a breed (model), a pasture (PLATO room/workspace), a fence (conservation policy), a herd (data source), a rotation schedule, and recall triggers. These aren't metaphors — they're compiled into concrete configuration objects that companion tools consume.

The parser converts whistle source text into a `WhistleProgram` AST. The validator checks referential integrity — does the breed exist in the registry? Is the pasture defined? Is the fence policy file accessible? The compiler then produces a `CompiledConfig` dict with sections for PLATO, conservation, flux, schedule, and recall wiring. This is the same separation of concerns that makes Docker Compose work: declarative intent, compiled to concrete configuration, consumed by the runtime.

## Install

```bash
pip install whistle-dsl
```

For development:

```bash
git clone https://github.com/SuperInstance/whistle.git
cd whistle
pip install -e ".[dev]"
```

## Quick Start

```python
from whistle import parse, compile, validate

source = '''
whistle daily_roundup {
  breed: "claude-3-opus",
  pasture: "ops-review",
  fence: "conservation/budget_decay.bin",
  herd: "incident-reports",
  rotate: every_1_hours,
  recall: on_drift
}
'''

# Parse to AST
program = parse(source)
print(f"Program: {program.name}")
print(f"Breed: {program.statements['breed'].value}")

# Validate referential integrity
result = validate(program)
if result.valid:
    print("✓ All references valid")
else:
    for err in result.errors:
        print(f"✗ {err}")

# Compile to infrastructure configs
config = compile(program)
# config = {
#   "plato": {"room": "ops-review", "mode": "auto"},
#   "conservation": {"policy": "budget_decay.bin"},
#   "flux": {"breed": "claude-3-opus"},
#   "schedule": {"interval": 3600},
#   "recall": {"trigger": "drift"}
# }
```

### CLI

```bash
# Validate a whistle file
whistle validate examples/medical.whistle

# Compile to JSON
whistle compile examples/medical.whistle --output medical.json

# List known breeds (pulls from breed-registry)
whistle breeds

# Watch a directory for .whistle files and auto-compile
whistle watch ./policies/
```

## DSL Reference

### Keywords

| Keyword | Type | Description |
|---------|------|-------------|
| `breed` | string | Model identifier (`"gpt-4"`, `"claude-3-opus"`, etc.) |
| `pasture` | string | PLATO room / conversation space to run in |
| `fence` | string | Conservation policy file path |
| `herd` | string | Data source / knowledge corpus |
| `rotate` | schedule | Rotation interval (`every_30_min`, `every_2_hours`, ...) |
| `recall` | trigger | Recall trigger (`on_alarm`, `on_drift`, `on_budget`) |
| `flank` | string | Optional: side-runnable preprocessor |
| `drive` | string | Optional: direction of work (`inbound`, `outbound`) |
| `stock` | string | Optional: stock ratio for multi-breed ensembles |

### Schedule Helpers

- `every_N_min` — every N minutes
- `every_N_hours` — every N hours
- `every_day_at_HH:MM` — daily at a specific time

### Recall Triggers

- `on_alarm` — external alarm signal
- `on_drift` — semantic drift detected
- `on_budget` — budget threshold crossed

### Example Program

```
whistle round_up_medical {
  breed: "gpt-4",
  pasture: "medical-review",
  fence: "conservation/budget_decay.bin",
  herd: "medical-records",
  rotate: every_30_min,
  recall: on_alarm,
  flank: "preprocessor/intake-cleaner.py",
  stock: "3:1:gpt-4:claude-3"
}
```

## Compilation Targets

`compile()` produces a dict with sections consumed by companion repos:

| Section | Consumer | What It Configures |
|---------|----------|-------------------|
| `plato` | [plato-core](https://github.com/SuperInstance/plato-core) | Room configuration, mode, capacity |
| `conservation` | [conservation-enforcer](https://github.com/SuperInstance/conservation-enforcer) | Policy file, budget allocation |
| `flux` | [flux-registry](https://github.com/SuperInstance/flux-registry) | Model routing, breed assignment |
| `schedule` | Cron / interval scheduler | Rotation interval, timezone |
| `recall` | Recall signal wiring | Trigger conditions, escalation chain |

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Whistle Pipeline                     │
│                                                       │
│  Source Text ──▶ Parser ──▶ WhistleProgram (AST)     │
│                                  │                    │
│                                  ▼                    │
│                            Validator                  │
│                         (referential                  │
│                          integrity)                   │
│                                  │                    │
│                                  ▼                    │
│                            Compiler                   │
│                                  │                    │
│                    ┌─────────────┼──────────┐         │
│                    ▼             ▼          ▼         │
│               PLATO config  Fence config  Flux config │
│               Schedule      Recall        Flank       │
└──────────────────────────────────────────────────────┘
```

## API Reference

### `parse(source: str) -> WhistleProgram`

Parse whistle source text into a `WhistleProgram` AST.

### `validate(program: WhistleProgram) -> ValidationResult`

```python
@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
```

### `compile(program: WhistleProgram) -> CompiledConfig`

```python
@dataclass
class CompiledConfig:
    plato: dict         # room configuration
    conservation: dict  # fence policy
    flux: dict          # breed routing
    schedule: dict      # rotation timing
    recall: dict        # trigger wiring

    def to_json(self) -> str
    def to_dict(self) -> dict
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v

# Test specific modules
pytest tests/test_parser.py -v
pytest tests/test_compiler.py -v
pytest tests/test_validator.py -v
```

## Why Not Just System Prompts?

| System Prompt | Whistle |
|---------------|---------|
| 500-word paragraph | 7-line declaration |
| No validation | Referential integrity checks |
| Copy-paste between scripts | Versioned, importable programs |
| Manual wiring to infrastructure | Compiled to PLATO, flux, fences |
| No type safety | Structured AST with typed fields |
| Impossible to diff | Text-based, git-friendly |

## Philosophy

In working dog trials, the whistle is how the shepherd communicates intent. It's not a detailed instruction — it's a cue. The dog knows the terrain; the whistle tells it what the shepherd wants. Whistle (the DSL) works the same way: you state what you want (breed, pasture, fence, herd, rotation) and the system figures out the wiring. No more hand-editing YAML configs across five different services.

For more on the working animal paradigm, see [AI-Writings](https://github.com/SuperInstance/AI-Writings).

## Ecosystem

| Repo | Role |
|------|------|
| **[whistle](https://github.com/SuperInstance/whistle)** | **This repo** — intent DSL |
| [a2ui](https://github.com/SuperInstance/a2ui) | Adaptive interface (consumes whistle-compiled configs) |
| [shepherds-console](https://github.com/SuperInstance/shepherds-console) | Dashboard (renders whistle-configured infrastructure) |
| [conservation-enforcer](https://github.com/SuperInstance/conservation-enforcer) | The fence engine that whistle configures |
| [plato-core](https://github.com/SuperInstance/plato-core) | The pasture engine that whistle configures |
| [breed-registry](https://github.com/SuperInstance/breed-registry) | The breed catalog that whistle references |

## License

MIT — see [LICENSE](LICENSE).
