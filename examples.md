# Examples — Whistle DSL

> Writing and compiling intent programs for Working Animal Architecture.

## Example 1: Daily Operations Review

A recurring ops review whistle program.

```whistle
whistle daily_ops_review {
  breed: "claude-3-opus",
  pasture: "ops-review",
  fence: "conservation/budget_decay.bin",
  herd: "incident-reports",
  rotate: every_1_hours,
  recall: on_drift
}
```

Compile and inspect:

```python
from whistle import parse, validate, compile

program = parse(open("daily_ops_review.whistle").read())
result = validate(program)

if result.valid:
    config = compile(program)
    print(config["plato"])    # {"room": "ops-review", "mode": "auto"}
    print(config["schedule"]) # {"interval": 3600}
else:
    for err in result.errors:
        print(f"✗ {err}")
```

## Example 2: Medical Records Auditor

A working animal that audits medical records for compliance.

```whistle
whistle medical_audit {
  breed: "gpt-4",
  pasture: "compliance-room",
  fence: "conservation/medical_fence.bin",
  herd: "medical-records",
  rotate: every_6_hours,
  recall: on_violation
}
```

Compile to infrastructure configs:

```bash
$ whistle compile medical_audit.whistle --output medical_audit.json
✓ Compiled: medical_audit
  PLATO room:    compliance-room
  Conservation:  medical_fence.bin
  Schedule:      every 6 hours
  Recall:        on_violation

$ cat medical_audit.json | python -m json.tool
{
    "plato": {"room": "compliance-room", "mode": "auto"},
    "conservation": {"policy": "medical_fence.bin"},
    "flux": {"breed": "gpt-4"},
    "schedule": {"interval": 21600},
    "recall": {"trigger": "violation"}
}
```

## Example 3: Fleet Coordination with Multiple Breeds

Deploy a coordinated fleet using multiple whistle programs.

```whistle
whistle scout_pattern_detection {
  breed: "deepseek-v4-flash",
  pasture: "pattern-scanning",
  fence: "conservation/cheap_scan.bin",
  herd: "log-stream",
  rotate: every_15_minutes,
  recall: on_detection
}

whistle elder_analysis {
  breed: "claude-3-opus",
  pasture: "deep-analysis",
  fence: "conservation/budget_decay.bin",
  herd: "scout-findings",
  rotate: on_event,
  recall: on_drift
}
```

The scout runs cheap and fast. When it detects something, the elder
gets triggered for deep analysis. Two whistle programs, one pipeline.

## Example 4: Validation Error Recovery

Handle validation failures when references don't resolve.

```python
from whistle import parse, validate

# Breed not in registry, fence file missing
source = '''
whistle broken_program {
  breed: "nonexistent-model",
  pasture: "undefined-room",
  fence: "missing/fence.bin",
  herd: "no-data",
  rotate: every_1_hours,
  recall: on_drift
}
'''

program = parse(source)
result = validate(program)

if not result.valid:
    print(f"{len(result.errors)} validation errors:")
    for err in result.errors:
        print(f"  ✗ {err.field}: {err.message}")
        print(f"    Fix: {err.suggestion}")
```

Output:
```
3 validation errors:
  ✗ breed: 'nonexistent-model' not in breed registry
    Fix: Check available breeds with `whistle breeds`
  ✗ fence: File 'missing/fence.bin' not found
    Fix: Check path or install policy with `flux install`
  ✗ herd: Data source 'no-data' not configured
    Fix: Add data source in PLATO config
```

## Example 5: CLI Workflow — Validate, Compile, Deploy

End-to-end whistle workflow from the command line.

```bash
# 1. Validate the program
$ whistle validate examples/fleet_scan.whistle
✓ Valid: fleet_scan
  breed:     deepseek-v4-flash (registered)
  pasture:   pattern-scanning (exists)
  fence:     cheap_scan.bin (32 bytes)
  herd:      log-stream (configured)
  schedule:  every 15 minutes
  recall:    on_detection

# 2. Compile to JSON config
$ whistle compile examples/fleet_scan.whistle --output fleet_scan.json
✓ Compiled → fleet_scan.json

# 3. List available breeds
$ whistle breeds
claude-3-opus        Anthropic   flagship, expensive
deepseek-v4-flash    DeepSeek    cheap workhorse
gpt-4                OpenAI      general purpose
glm-5.2              Zhipu      mid-tier, good caching

# 4. Dry-run the compiled config
$ whistle dry-run fleet_scan.json
✓ PLATO room 'pattern-scanning' reachable
✓ Conservation policy loads (32 bytes, 4 instructions)
✓ Data source 'log-stream' active (last event: 2s ago)
✓ Schedule: next run in 12 minutes
```
