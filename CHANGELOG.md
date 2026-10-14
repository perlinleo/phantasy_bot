# Changelog

All notable changes follow [Semantic Versioning](https://semver.org/). Until `1.0.0`, minor
versions may include incompatible changes while the product remains in beta.

## [0.7.0] - 2026-10-14

### Added

- Opt-in `gothic_metal_title`: Blender-generated chrome 3D lettering, crimson rim light,
  animated rain, fog, lightning and blood rivulets; measured frame progress and MP4 encoding.
- Blender runtime dependency; core job/worker/database contracts remain unchanged.
- Public contribution, conduct, security, support, maintainer, operations and plugin-authoring
  documentation plus GitHub issue/PR templates.
- Publication checklist, font notice and repository attributes for text/binary assets.

### Limitations

- Real Blender rendering and visual acceptance have not been verified in this environment.
- CPU rendering may exceed the default worker timeout; configure a longer timeout explicitly.

## [0.6.0] - 2026-10-14

### Added

- Owner status, backup, healthcheck, draft cancellation, and safe cleanup dry-run commands.
- Queue leases, fencing tokens, heartbeats, atomic delivery claims, and cancellation paths.

## [0.5.0] - 2026-10-14

### Added

- Access request workflow with owner request review, allow, and revoke commands.
- Custom emoji publisher/store implementation and successful live acceptance.
- MP4 ffprobe validation for the space crawl renderer.

## [0.4.0] - 2026-10-14

### Added

- Persistent tool options, confirmation summaries, tool search metadata, and settings presets.
- Live editable Telegram task cards with final delivery status.
- Atomic job and delivery claims, job leases, fencing tokens, heartbeats, and expired-lease recovery.
- Queued and running job cancellation, including worker process-group termination.
- Runtime bot version footer, `VERSION`, and this changelog.

## [0.3.0] - 2026-10-14

### Added

- Persistent drafts, jobs, worker subprocesses, result delivery records, and Telegram task cards.
- `space_crawl` H.264 MP4 renderer and `text_to_emoji` tile/preview renderer.
- Tool metadata, tool search, persistent options, confirmation summary, and settings presets.
- Local quality gate with tests, coverage, Ruff, mypy, dependency audit, and Bandit.

### Changed

- Bot configuration accepts comma-separated `ENABLED_PLUGINS` values.

## [0.2.0] - 2026-10-13

### Added

- SQLite/Alembic foundation, owner/allowlist access control, plugin SDK, Docker/Compose skeleton.
- Offline `text_card` renderer and minimal private Telegram bot.

## [0.1.0] - 2026-10-13

### Added

- Initial repository, implementation plan, Python 3.12/uv project setup.

## Versioning and releases

- New user-visible features increment the minor version: `0.x.0`.
- Compatible bug/security fixes increment the patch version: `0.x.y`.
- Update root `VERSION`, `src/media_bot/VERSION`, and this file together.
- Create an annotated local Git tag only after committing the matching changes:
  `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.
- Never push tags or releases without explicit user authorization.
