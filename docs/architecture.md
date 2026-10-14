# Architecture

## Runtime

One image runs three roles: one-shot Alembic migration, aiogram long-polling bot, and one SQLite
worker. Bot and worker share `/data`; only the bot role receives `BOT_TOKEN`. SQLite is configured
with WAL, foreign keys, and busy timeout. One worker claims one job at a time by default.

## Boundaries

- `domain`: state types without aiogram, SQLAlchemy, or renderer imports.
- `application`: drafts, jobs, leases, cancellation, access, and delivery state transitions.
- `infrastructure`: SQLite, filesystem, worker subprocesses, runner JSON protocol, backups.
- `adapters/telegram`: routers, keyboards, status cards, and result delivery.
- `plugins`: trusted repository renderers. They accept typed input/options and `JobContext`, write
  only to their workspace, and return relative artifact paths.
- `services`: shared renderer utilities such as FFmpeg, typography, and emoji publishing.

## Job lifecycle

1. A user creates a persistent draft and confirms a revision.
2. SQLite atomically creates an idempotent queued job; the worker claims it with a lease/fencing
   token.
3. Parent worker writes `input.json` and launches a token-free `run-payload` child process.
4. The child emits bounded JSONL progress and writes `result.json`; it does not access SQLite.
5. The parent validates artifact containment, size, signature, and media type before completing the
   job and creating a delivery record.
6. The bot claims delivery separately. Send/commit ambiguity is represented by delivery states such
   as `uncertain`; retry and resend do not rerender the artifact.

The Blender title renderer remains a plugin-local subprocess implementation: it reuses this same
protocol and does not alter queue, database, ACL, or Telegram core behavior.
