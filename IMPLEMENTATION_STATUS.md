# Implementation Status

Updated: 2026-10-14

This checklist records code and checks that exist today. It does not claim unavailable Docker or
live Telegram acceptance.

## Implemented

- Python 3.12 / uv project, SQLite WAL + Alembic migrations, persistent drafts/jobs/deliveries.
- Owner/allowlist and access requests; private-chat Telegram routing.
- Queue claims, lease/fencing tokens, heartbeats, one recovery retry, queue/user limits, cancellation
  requests, runner timeout handling, JSON input/result boundary and artifact validation.
- Persistent options/confirmation, search/category catalog, status cards, basic frame-progress
  protocol, separate delivery states/retry/resend/suppression.
- `text_card`, `space_crawl`, custom emoji, Halloween emoji plugins, and Blender
  `gothic_metal_title`.
- Operations commands: migrations, backup, healthcheck, safe cleanup dry run, status.
- Local CI-quality tooling and GitHub workflow skeleton.

## Verified offline

- Full `make check` with Blender 5.2.2 on PATH: 73 tests passed, 91.05% coverage, Ruff/mypy,
  lock check, pip-audit, and Bandit passed.
- `gothic_metal_title` generated a real 1280×720 Blender 5.2.2 frame and `.blend` during a smoke
  test. The full-duration scene was not benchmarked.
- Alembic migrations reached head on a new SQLite database.

## Still required before production claims

- Docker build/runtime smoke; Docker is unavailable in this environment.
- Live Telegram acceptance for progress edits, result delivery, custom emoji, access/revoke,
  resend, and all video plugins.
- Full Blender title visual review, CPU timing benchmark, long-job cancellation, and timeout tuning.
- Complete Stage B reliability work: atomic attempt-directory finalization, worker shutdown handling,
  render failure status-card updates, and more delivery/429 acceptance tests.
- Remaining Stage E/F retention/restore/docs/deployment acceptance as described in the plan.
