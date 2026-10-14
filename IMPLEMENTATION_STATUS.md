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
- `text_card`, `space_crawl`, custom emoji, Halloween emoji plugins, Blender
  `gothic_metal_title`, and the two 0.8.0 character plugins `glamour_letters` / `comedy_stage`.
- Pinned external character artwork, CPU rendering, Telegram presets with revision guards,
  isolated runner asset forwarding and read-only Compose artwork mounts.
- Operations commands: migrations, backup, healthcheck, safe cleanup dry run, status.
- Local CI-quality tooling and GitHub workflow skeleton.

## Verified offline

Latest 0.8.0 validation:

- Full `make check`: 113 passed, 1 skipped (host Blender absent), coverage 93.15%;
  Ruff/mypy, lock check, pip-audit and Bandit passed.
- Real PNG and 6/8-second MP4, ffprobe, isolated runner outside repository cwd,
  process-group cancellation, wheel packaging and actual artwork review passed.
- Docker build and real renders for both new plugins passed as UID 10001, without
  network/token, with read-only root/artwork and a writable temporary workspace.
- [Detailed acceptance and CPU measurements](docs/character-plugin-acceptance.md).

Earlier 0.7.0 baseline (retained as historical evidence):

- Full `make check` with Blender 5.2.2 on PATH: 73 tests passed, 91.05% coverage, Ruff/mypy,
  lock check, pip-audit, and Bandit passed.
- `gothic_metal_title` generated a real 1280×720 Blender 5.2.2 frame and `.blend` during a smoke
  test. The full-duration scene was not benchmarked.
- Alembic migrations reached head on a new SQLite database.

## Still required before production claims

- Production Compose lifecycle, persistent-volume recovery and deploy acceptance beyond the
  isolated Docker renderer smoke above.
- Live Telegram acceptance for progress edits, result delivery, custom emoji, access/revoke,
  resend, and all video plugins.
- Full Blender title visual review, CPU timing benchmark, long-job cancellation, and timeout tuning.
- Complete Stage B reliability work: atomic attempt-directory finalization, worker shutdown handling,
  render failure status-card updates, and more delivery/429 acceptance tests.
- Remaining Stage E/F retention/restore/docs/deployment acceptance as described in the plan.
