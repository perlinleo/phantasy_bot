# Publication and Release Checklist

This repository is not published, tagged, or released by this checklist. A maintainer performs
those actions separately.

## Before first public push

- [ ] Revoke and replace any Telegram token ever exposed outside a private secret store.
- [ ] Verify `.env`, `data/`, backups, generated media, and local logs are ignored and not staged.
- [ ] Inspect the staged diff: `git diff --cached --check` and `git diff --cached`.
- [ ] Confirm the no-license policy in README, or select and add a project `LICENSE`. Public
  visibility alone grants no reuse rights.
- [ ] Enable GitHub private vulnerability reporting, Dependabot, secret scanning, and push protection.
- [ ] Confirm the account in [MAINTAINERS.md](MAINTAINERS.md) is correct.
- [ ] Review public contact links in `SECURITY.md` and issue templates.

## Before a versioned release

- [ ] Synchronize `pyproject.toml`, `VERSION`, `src/media_bot/VERSION`, and `CHANGELOG.md`.
- [ ] Run `make check`.
- [ ] Run Docker build/smoke and relevant media integration tests.
- [ ] Run required manual Telegram acceptance; state unavailable checks honestly.
- [ ] Create a backup and verify migration/restore guidance for persistence changes.
- [ ] Review `git status` for user data, media, caches, artifacts, and `.DS_Store`.

## Publication after approval

- [ ] Commit reviewed changes.
- [ ] Push the reviewed commit to the intended repository.
- [ ] Create a signed/annotated tag and GitHub release only after explicit maintainer approval.
