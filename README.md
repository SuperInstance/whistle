# Whistle — Intent DSL for Working Animal Architecture

> Replaces system-prompt sprawl with structured, compiled commands.

In the working-dog paradigm, whistles are how the shepherd communicates with the dogs.
This repo provides a structured DSL instead of unstructured system prompts.

## Quick Example

```
whistle round_up_medical {
  breed: "gpt-4",
  pasture: "medical-review",
  fence: "conservation/budget_decay.bin",
  herd: "medical-records",
  rotate: every_30_min,
  recall: on_alarm
}
```

## Why?

System prompts are the assembly language of LLM orchestration — verbose, unstructured,
and impossible to validate. Whistle gives you a declarative DSL that compiles down to
the configs your infrastructure already understands.

| System Prompt                    | Whistle                              |
|----------------------------------|--------------------------------------|
| 500-word paragraph               | 7-line declaration                   |
| No validation                    | Referential integrity checks         |
| Copy-paste between scripts       | Versioned, importable programs       |
| Manual wiring                    | Compiled to PLATO rooms, flux, fences |

## Installation

```bash
pip install whistle-dsl
```

## DSL Reference

### Keywords

| Keyword    | Type     | Description                                              |
|------------|----------|----------------------------------------------------------|
| `breed`    | string   | Model identifier (`"gpt-4"`, `"claude-3-opus"`, etc.)   |
| `pasture`  | string   | PLATO room / conversation space to run in                |
| `fence`    | string   | Conservation policy file path                            |
| `herd`     | string   | Data source / knowledge corpus                           |
| `rotate`   | schedule | Rotation interval (`every_30_min`, `every_2_hours`, ...) |
| `recall`   | trigger  | Recall trigger (`on_alarm`, `on_drift`, `on_budget`)     |
| `flank`    | string   | Optional: side-runnable preprocessor                     |
| `drive`    | string   | Optional: direction of work (`inbound`, `outbound`)      |
| `stock`    | string   | Optional: stock ratio for multi-breed ensembles          |

### Schedule Helpers

- `every_N_min` — every N minutes
- `every_N_hours` — every N hours
- `every_day_at_HH:MM` — daily at a specific time

### Recall Triggers

- `on_alarm` — external alarm signal
- `on_drift` — semantic drift detected
- `on_budget` — budget threshold crossed

## Python API

```python
from whistle import parse, compile, validate

source = '''
whistle daily_roundup {
  breed: "claude-3-opus",
  pasture: "ops-review",
  herd: "incident-reports",
  rotate: every_1_hours,
  recall: on_drift
}
'''

program = parse(source)
result = validate(program)
config = compile(program)
```

## Compilation Targets

`compile()` produces a dict with sections consumed by companion repos:

| Section       | Consumer                              |
|---------------|---------------------------------------|
| `plato`       | PLATO room configuration              |
| `conservation`| Conservation fence policy             |
| `flux`        | Flux registry entry                   |
| `schedule`    | Cron / interval scheduler             |
| `recall`      | Recall signal wiring                  |

## CLI

```bash
# Validate a whistle file
whistle validate examples/medical.whistle

# Compile to JSON
whistle compile examples/medical.whistle --output medical.json

# List known breeds
whistle breeds
```

## Ecosystem

| Repo                     | Role                                    |
|--------------------------|-----------------------------------------|
| `SuperInstance/whistle`  | DSL — **this repo**                     |
| `SuperInstance/PLATO`    | Conversation rooms & pastures           |
| `SuperInstance/conservation` | Budget / safety fences             |
| `SuperInstance/flux`     | Model routing & ensemble registry       |

## License

MIT
