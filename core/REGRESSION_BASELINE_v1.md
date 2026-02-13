# QTMoS Regression Baseline v1

Date: 2026-02-07

## Goal
Quickly validate core runtime + pack/memory introspection + bridge launch path.

## Run (main shell)
```text
python main.py
```
Then at `>`:
```text
run-script regression_baseline_v1.txt
live
```

## Run (bridge shell)
At `bridge>`:
```text
/status
live
state
/quit
```

## Expected
- `state`: operational
- `pack-list epi`: shows `pack_empty.json` and `pack_openclaw_epi.json`
- `claw status --json`: adapters true, memory core/epi counts present
- `scan`: `[SCAN]: ok`
- `live`: launches bridge
- bridge `/status`: prints core/epi/llm summary
- bridge `live`: inferstructured ON + periodic status + epi tail preview

## Notes
- This is the first stable baseline after live bridge integration.
- Use this before/after changes to detect drift fast.
