# CI/CD and Quality Pipeline Plan

## Goals

- Every pull request must be reproducible, formatted, typed, tested, and scanned before merge.
- Coverage measures meaningful behavior, rather than tests that duplicate implementation details.
- Production deployment remains explicit and auditable until server infrastructure and credentials exist.
- Pull-request jobs never receive a Telegram token, production database, or live Telegram access.

## Local quality gate

Run the complete local gate with:

```sh
make check
```

It validates the lockfile, formatting, linting, static types, tests with at least 90% line coverage,
dependency vulnerabilities, and code-security findings. `make format` applies formatting; it is the
only quality command that changes files.

## Test and coverage policy

- Coverage is measured for `src/media_bot` and reports to terminal, `coverage.xml`, and
  `coverage.json`.
- The enforced minimum is 90% line coverage. Exclusions are limited to package markers and the
  interpreter guard; all application behavior remains measurable.
- Unit tests cover domain rules, ACL, configuration, plugin validation, renderer output, and CLI
  dispatch. Integration tests cover SQLite migrations, subprocesses, media, and cleanup as those
  components are implemented.
- Every enabled plugin gets a contract test with fixture input. Docker and live Telegram checks are
  separate: the latter always require manual acceptance and never run in PR CI.

## Security policy

- `pip-audit` scans the locked, installed dependencies and fails the local gate on known advisories.
- Bandit scans `src`; high-confidence/high-severity findings fail. A suppression requires an inline
  explanation and a tracked review/removal task.
- Keep tokens, `.env`, data, generated artifacts, and user inputs out of Git. Enable GitHub secret
  scanning, push protection, Dependabot, and dependency review when GitHub configuration begins.
- Image scans (Trivy), SBOM, pinned action SHAs, and GHCR provenance belong to the later GitHub CI
  rollout.

## Future GitHub CI/CD

GitHub CI will run independent lock, quality, test/coverage, security, and Docker-smoke jobs.
Deployment is deliberately deferred: it will be a protected, manually dispatched workflow that
builds an immutable image, backs up SQLite, runs migrations once, deploys the exact image digest,
and records the backup ID and migration revision. It must not use automatic server updates or
receive `BOT_TOKEN` through GitHub Actions.

## Open deployment decisions

- Server hostname, SSH account, Compose path, backup target, and retention.
- Production-environment approver(s) and protected GitHub Environment configuration.
- Container registry selection (default proposed: GHCR).
