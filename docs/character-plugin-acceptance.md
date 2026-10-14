# Character plugins: offline acceptance, 2026-10-14

Version: 0.8.0. Both plugins were rendered with the actual generated artwork pack,
not only synthetic fixtures. Live Telegram acceptance has not been run.

## Automated checks

- `make check UV=/tmp/phantasy-tools/bin/uv`: passed. 113 tests passed, one Blender test
  skipped because host Blender is absent; coverage 93.15%. Lock, Ruff, mypy, pip-audit
  and Bandit passed. Existing plugin regressions are included.
- `uv build`: sdist/wheel built. The wheel includes `media_bot/assets/characters-v1.json`
  and excludes generated artwork; version files and package metadata are 0.8.0.
- CI test setup explicitly installs FFmpeg and DejaVu fonts. The first implementation CI
  run exposed their absence on the hosted runner; real media tests remain mandatory.
- Real isolated `run-payload` calls from `/tmp`, with only PATH in the environment:
  short/max PNG and 6/8-second MP4 passed. No Telegram token or `.env` is loaded.
- Real process-group SIGTERM during frame production stopped the runner and encoder;
  no successful result manifest was written. Separate tests cover encoder termination
  when a frame generator raises and draining 2 MB of stderr without deadlock.
- A Cyrillic phrase that exceeds the physical board layout was rejected before rendering;
  the 100-character boundary case uses narrow Latin glyphs. Character count alone does
  not promise every phrase fits at the minimum readable font size.

## Docker

`docker build -t phantasy-bot:characters-check .` passed. The final source image was run
with `--network none --read-only --tmpfs /tmp:rw,size=128m`, a read-only artwork mount,
and no BOT_TOKEN. The smoke asserted UID 10001 and version 0.8.0, validated the pinned
pack, then rendered both plugins through runner_exec. PNG dimensions and MP4 codec,
dimensions, fps, pixel format, duration, absence of audio and faststart passed.
The optional Compose overlay documents the same resource mount for bot and worker.
This is an isolated renderer/runtime smoke, not a production bot/worker deployment.

## CPU measurements

Host: Linux, Intel Core i7-1255U, Python 3.12.3, Pillow 12.3.0, FFmpeg 6.1.1.
Each job ran in a fresh process outside repository cwd. Times include Python startup;
peak RSS is reported by `/usr/bin/time` for the command, not total system memory.
FFmpeg uses two encoding threads. These are measurements on this host, not latency guarantees.

| Case | Wall seconds | Peak RSS KiB | Output bytes |
|---|---:|---:|---:|
| glamour-short | 2.00 | 107112 | 615132 |
| glamour-max | 3.06 | 107320 | 777843 |
| comedy-short | 19.59 | 247904 | 345690 |
| comedy-max | 24.39 | 248984 | 441577 |

The 8-second video used approximately the same peak RSS as the 6-second video; frames
are streamed rather than accumulated. All outputs are below the configured 10/20 MiB limits.

## Visual inspection

Inspected actual short and 12-letter two-row posters, Cyrillic Ё/Й and mixed Latin text,
and extracted beginning/middle/end frames from the real videos. Letters rest on the
models' palms without covering faces. The comedy hosts are recognizable caricatures;
the board stays readable while poses and lights move. Four models repeat on long inputs.
This is the implementing agent's visual review, not the owner's live Telegram approval.

Local, Git-ignored deliverables:

- `output/characters-v1.tar.gz`: artwork, manifest, provenance and exact accepted prompts.
- `output/plugin-assets/v1/`: installed immutable artwork pack.
- `output/acceptance/glamour-short/glamour-letters.png`: poster example.
- `output/acceptance/comedy-short/comedy-stage.mp4`: six-second video example.
- `output/acceptance/benchmark.json`: measurements for the four scenarios.

## Remaining live acceptance

On a configured bot: catalog/search and every preset, confirmation/options persistence,
PNG/MP4 delivery on Desktop/mobile, progress and cancel, restart, resend, revoke and
actual Telegram upload/429 behavior. No real Telegram messages were sent during this work.
