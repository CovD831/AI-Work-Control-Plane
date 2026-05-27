# AI Work Control Plane Runtime Measurement RC Phase 2: CLI Capture

## Goal

Expose runtime measurement facts through existing CLI/runtime surfaces.

## Work Items

- Ensure command-runtime jobs persist start/end/duration/exit-code measurement facts.
- Show measurement facts in `team runtime inspect <job_id> --format json`.
- Add runtime measurement readiness to `team setup --runtime command --format json`.
- Keep attach/send/cancel as recorded support/receipt facts only.

## Targeted Tests

```bash
pytest tests/test_command.py tests/test_jobs.py tests/test_tmux_runtime.py tests/test_cli.py -q
```
