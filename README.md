# Whistle — Intent DSL for Working Animal Architecture

> Replaces system-prompt sprawl with structured, compiled commands.

In the working-dog paradigm, a shepherd communicates with dogs using whistle cues — short, precise signals that carry complete instructions. **Whistle** brings the same discipline to LLM orchestration: instead of 500-word system prompt paragraphs that are impossible to validate or version, you write declarative `.whistle` files that compile into the configs your infrastructure already expects.

## Why It Exists

System prompts are the assembly language of LLM ops — verbose, unstructured, untestable. You copy-paste them between scripts, tweak them by hand, and hope nothing breaks. Whistle gives you:

- **Declarative syntax** — describe *what* the working animal should do, not *how* in prose
- **Validation** — referential integrity checks before deployment, not at runtime
- **Compilation** — a single `.whistle` file produces configs for PLATO rooms, conservation fences, flux routing, schedules, and recall wiring
- **Versioning** — whistle programs are text files you can diff, review, and roll back

| System Prompt | Whistle |
|---------------|---------|
| 500-word paragraph | 7-line declaration |
| No validation | Referential integrity checks |
| Copy-paste between scripts | Versioned, importable programs |
| Manual wiring to each service | One `compile()` call outputs all configs |

## Installation

```bash
pip install whistle-dsl
```

Requires Python 3.10+.

## Quick Start

Create a file `roundup.whistle`:

```
# Medical records review working animal
whistle round_up_medical {
    breed: "gpt-4o",
    pasture: "medical-review",
    fence: "conservation/budget_decay.bin",
    herd: "medical-records",
    rotate: every_30_min,
    recall: on_alarm
}
```

Compile it:

```python
from whistle import parse, compile, validate

source = open("roundup.whistle").read()

program = parse(source)          # → WhistleProgram (AST)
result = validate(program)       # → ValidationResult

if result.valid:
    config = compile(program)    # → deployment-ready config dict
    print(config)
else:
    for err in result.errors:
        print(f"  [{err.whistle}] {err.field}: {err.message}")
```

Or use the CLI:

```bash
# Validate a whistle file
whistle validate roundup.whistle

# Compile to JSON
whistle compile roundup.whistle --output medical-config.json

# List known model breeds
whistle breeds
```

## DSL Reference

### Syntax

```
whistle NAME {
    field: value,
    field: value,
    ...
}
```

Comments start with `#`. Multiple `whistle` blocks per file are allowed — each compiles to a separate entry.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `breed` | string | **Yes** | Model identifier — must be a known breed or flagged as custom |
| `pasture` | string | No | PLATO room / conversation space to run in (defaults to whistle name) |
| `fence` | string | No | Conservation policy file path |
| `herd` | string | No | Data source / knowledge corpus |
| `rotate` | schedule | No | Rotation interval |
| `recall` | trigger | No | Recall signal |
| `flank` | string | No | Side-runnable preprocessor |
| `drive` | string | No | Direction of work (`inbound` or `outbound`) |
| `stock` | string/int | No | Stock ratio for multi-breed ensembles |

### Schedule Syntax

| Expression | Meaning |
|------------|---------|
| `every_30_min` | Every 30 minutes |
| `every_2_hours` | Every 2 hours |
| `every_day_at_09:00` | Daily at 09:00 |

### Recall Triggers

| Trigger | Meaning |
|---------|---------|
| `on_alarm` | External alarm signal |
| `on_drift` | Semantic drift detected |
| `on_budget` | Budget threshold crossed |

Any `on_*` identifier is accepted as a trigger.

### Known Breeds

| Breed | Provider | Context Window |
|-------|----------|----------------|
| `gpt-4` | OpenAI | 128,000 |
| `gpt-4o` | OpenAI | 128,000 |
| `gpt-4-turbo` | OpenAI | 128,000 |
| `claude-3-opus` | Anthropic | 200,000 |
| `claude-3-sonnet` | Anthropic | 200,000 |
| `claude-3-haiku` | Anthropic | 200,000 |
| `gemini-pro` | Google | 1,000,000 |
| `gemini-1.5-pro` | Google | 2,000,000 |
| `llama-3-70b` | Meta | 8,000 |
| `mistral-large` | Mistral | 32,000 |

Unknown breeds trigger a warning and are treated as custom models with default 8,192 context window.

## Architecture

```
 .whistle source
       │
       ▼
┌─────────────┐
│   Parser    │  ← hand-written tokenizer + recursive descent
│             │     produces WhistleProgram AST
└──────┬──────┘
       │  WhistleProgram
       ▼
┌─────────────┐
│  Validator  │  ← checks required fields, breed names,
│             │     fence paths, schedule/trigger types
└──────┬──────┘
       │  ValidationResult (errors + warnings)
       ▼
┌─────────────┐
│  Compiler   │  → transforms each WhistleStatement into
│             │     a CompiledConfig with 5 target sections
└─────────────┘
```

### Compilation Targets

Each `whistle compile` produces a dict with these sections, consumed by companion services:

| Section | Consumer | What It Contains |
|---------|----------|------------------|
| `plato` | PLATO room system | Room name, model, corpus, drive direction |
| `conservation` | Conservation fence enforcer | Policy file, enforcer class, token limits |
| `flux` | Flux model router | Breed, provider, context window, preprocessor |
| `schedule` | Cron / interval scheduler | Rotation type, interval in seconds, raw expression |
| `recall` | Recall signal handler | Trigger event, action (`halt_and_return`) |

Example compiled output:

```json
{
  "whistles": {
    "round_up_medical": {
      "name": "round_up_medical",
      "plato": {
        "room": "medical-review",
        "model": "gpt-4o",
        "corpus": "medical-records",
        "drive": "inbound"
      },
      "conservation": {
        "policy_file": "conservation/budget_decay.bin",
        "enforcer": "conservation.BudgetDecay",
        "defaults": { "max_tokens_per_turn": 4096 }
      },
      "flux": {
        "breed": "gpt-4o",
        "routing": {
          "provider": "openai",
          "family": "gpt-4o",
          "context_window": 128000
        }
      },
      "schedule": {
        "type": "interval",
        "interval_seconds": 1800,
        "raw": "every_30_min"
      },
      "recall": {
        "trigger": "alarm",
        "action": "halt_and_return",
        "raw": "on_alarm"
      }
    }
  }
}
```

## API Reference

### `parse(source: str) -> WhistleProgram`

Parse a whistle DSL source string into a `WhistleProgram` AST. Raises `SyntaxError` on malformed input.

### `validate(program: WhistleProgram) -> ValidationResult`

Validate all whistle statements. Returns a `ValidationResult` with `valid: bool`, `errors: list[FieldIssue]` (blocking), and `warnings: list[FieldIssue]` (non-blocking).

### `compile(program: WhistleProgram) -> dict`

Compile a validated program into a deployment-ready config dict. Returns `{"whistles": {name: config_dict, ...}}`.

### `compile_one(stmt: WhistleStatement) -> CompiledConfig`

Compile a single statement into a `CompiledConfig` with `.plato`, `.conservation`, `.flux`, `.schedule`, `.recall`, and `.raw` attributes.

### CLI: `whistle`

```bash
whistle validate <file>          # Validate a .whistle file
whistle compile <file> [-o OUT]  # Compile to JSON (stdout or file)
whistle breeds                   # List known model breeds
```

## Testing

```bash
git clone https://github.com/SuperInstance/whistle.git
cd whistle
pip install -e ".[dev]"
pytest

# With coverage
pytest --cov=whistle --cov-report=term-missing
```

## Ecosystem

| Repo | Role |
|------|------|
| `SuperInstance/PLATO` | Conversation rooms & pastures (consumes `plato` config) |
| `SuperInstance/conservation` | Budget / safety fences (consumes `conservation` config) |
| `SuperInstance/flux` | Model routing & ensemble registry (consumes `flux` config) |
| **`SuperInstance/whistle`** | **DSL compiler — this repo** |
| `SuperInstance/baton` | Generational handoff between model lifecycles |
| `SuperInstance/trawl` | Commercial fishing implementation |
| `SuperInstance/a2ui` | Adaptive interface generation |
| `SuperInstance/shepherds-console` | Operations dashboard |

## Philosophy

You don't explain a task to a sheepdog in a 500-word monologue. You give a cue — a whistle — and the dog understands the terrain. Whistle applies the same principle to LLM orchestration: the intent is small and precise, the infrastructure handles the rest.

System prompts conflate *what the model should do* with *how the infrastructure should be configured*. Whistle separates them. Your `.whistle` file declares intent; the compiler wires it into every system that needs configuration. One source of truth, validated before deployment, diffable in version control.

## License

MIT
