# Contributing to Phantasy Bot

Thank you for contributing. This repository is a private-media Telegram bot that may be published
for collaborative development; it is **not** a public media-hosting service.

## Before opening an issue

- Do not include bot tokens, `.env` files, SQLite databases, Telegram chat IDs, user input,
  generated media, private sticker-set links, or full HTTP URLs containing credentials.
- Report security issues through [SECURITY.md](SECURITY.md), not public issues.
- Search existing issues first. Include a minimal reproducible example and the relevant version.

## Local development

```sh
uv sync --all-groups
cp .env.example .env
make check
```

`make check` validates the lockfile, formatting, linting, types, tests/coverage, dependency audit,
and Bandit. Use the absolute `uv` path or ensure `uv` is on `PATH` if your shell cannot find it.

Docker and live Telegram checks require local tools and credentials; never add credentials to a PR.
Run the available offline checks and explicitly state any checks you could not run.

## Change guidelines

- Read [AGENTS.md](AGENTS.md) and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
- Keep Telegram code in `src/media_bot/adapters/telegram`, persistence in `infrastructure`, and
  rendering algorithms in `plugins` or `services`.
- Keep jobs, plugins, and delivery behavior backwards compatible unless a documented decision says
  otherwise. New plugin IDs are immutable.
- Add or update focused tests. Do not reduce coverage exclusions to make a gate pass.
- Add an Alembic migration for persisted schema changes; never alter existing migrations.
- Record substantial architectural deviations in `docs/decisions/`.
- Update `VERSION`, `src/media_bot/VERSION`, and `CHANGELOG.md` for user-visible releases.

## Pull requests

Keep PRs small and explain: purpose, test evidence, operational impact, migration requirements,
and any unavailable Docker/live-Telegram checks. A maintainer must review all changes to ACL,
queue/worker behavior, delivery, dependency updates, workflows, and security policy.

By contributing, you agree that your contribution may be distributed under the repository's future
published license. Until a license is selected, no broad reuse rights are granted.
