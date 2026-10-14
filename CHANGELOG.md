# Changelog

All notable changes follow [Semantic Versioning](https://semver.org/). Until `1.0.0`, minor
versions may include incompatible changes while the product remains in beta.

## [0.8.0] - 2026-10-14

### Added

- Opt-in `glamour_letters` («Крутые тёлки»): four adult fictional models supporting
  metallic user letters, Cyrillic-aware bounded layout and three PNG poster palettes.
- Opt-in `comedy_stage`: recognizable illustrated Pavel Volya and Garik Kharlamov,
  interpolated poses, animated lighting, readable user text and silent 720p H.264 MP4.
- Pinned external artwork pack with SHA-256, sprite bounds and palm anchors, startup
  validation, token-free runner asset-path forwarding and a read-only Compose overlay.
- Explicit Telegram presets, refreshed confirmation after settings changes, and tests
  for text/layout, assets, actual media encoding, subprocess failures and SQLite persistence.
- [Implementation plan](docs/plans/glamour-and-comedy-plugins.md),
  [setup instructions](docs/character-plugins.md) and documented visual/asset decisions.

### Fixed

- Reject stale, foreign and cross-plugin preset callbacks; make revision updates atomic.
- Reject confirmation replay by a different user, including already-submitted drafts.
- Drain FFmpeg stderr continuously with bounded diagnostics and reap the encoder on
  renderer failure or broken pipe; validate positive duration and the new animation's
  frame rate, pixel format and faststart atom order.
- Exclude generated artwork and media from the Docker build context.
- Install FFmpeg and Cyrillic fonts in the CI test job for real media integration checks.

### Limitations

- Generated artwork is supplied separately, never committed; new plugins require its installation.
- Live Telegram acceptance still requires a real deployment. Comedy uses illustrated poses,
  without voices or lip sync; longer glamour strings reuse the four models.

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
