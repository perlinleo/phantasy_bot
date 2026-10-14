# Operations

## Safety baseline

- Keep `.env`, `/data`, generated media, logs containing user input, and SQLite backups private.
- Rotate a Telegram token immediately if it appears in any chat, terminal capture, issue, or commit.
- Run exactly one bot polling process and one worker against the SQLite volume.
- Run migrations only through the one-shot `migrate` service/command.

## Local commands

```sh
uv sync --all-groups
DATA_DIR=./data uv run media-bot migrate
make check
```

The project uses a shared persistent `DATA_DIR`. Back up SQLite through `media-bot backup`; do not
copy a live WAL database with a plain file copy.

## Blender title renderer

`gothic_metal_title` requires Blender 3.4+ and FFmpeg. On macOS, ensure the worker shell sees
Blender before starting it:

```sh
export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"
blender --version
```

Set a deliberately high `JOB_TIMEOUT_SECONDS` after benchmarking. CPU Cycles rendering may take
many minutes. The renderer's frame progress begins only after the first completed frame.

## Live acceptance still required

Docker build/smoke, real Telegram delivery, restart recovery, cancellation of Blender/FFmpeg, and
visual review of every plugin must be performed in the target environment. Do not represent offline
tests as a production acceptance result.
