# Phantasy Bot

Private, allowlisted Telegram bot for rendering media through trusted in-repository plugins. It is
designed for personal/private chats: users select a tool, create a persistent draft, confirm a job,
watch one editable status card, and receive a local result through Telegram.

> **Beta / security note:** do not commit or publish `.env`, bot tokens, SQLite databases, user
> input, generated media, or private Telegram links. If a token was exposed, revoke it in BotFather.

## Current capabilities

- PNG text cards with Cyrillic input.
- H.264 MP4 `space_crawl` renderer.
- Custom emoji composition with PNG fallback.
- Halloween emoji styles.
- `gothic_metal_title`: Blender-generated 3D mirrored chrome lettering with crimson rim light,
  blood rivulets, rain, low fog, lightning, and measured frame progress.
- SQLite queue, leases, fenced worker attempts, cancellation, artifact validation, delivery states,
  drafts/options, access control, backups, and local quality checks.

The implementation is beta software. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for
verified work and remaining live/Docker acceptance checks.

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- FFmpeg
- Docker Compose for containerized bot/worker execution
- Telegram bot token only for a live deployment
- Blender 3.4+ only when `gothic_metal_title` is enabled

## Quick start without Telegram

```sh
uv sync --all-groups
DATA_DIR=./data uv run media-bot migrate
uv run media-bot render-text-card --text 'Привет, мир!' --output ./output
make check
```

The local gate checks the lockfile, formatting, Ruff, mypy, tests with ≥90% coverage,
`pip-audit`, and Bandit. If `uv` is not on PATH, run `make UV=/absolute/path/to/uv check`.

## Local live run

1. Create a bot through BotFather and obtain your own Telegram numeric ID through `/whoami` after
   an initial trusted setup. Do not paste the token into issues, logs, or source files.
2. Create local configuration:

   ```sh
   cp .env.example .env
   ```

3. Set `BOT_TOKEN` and `OWNER_TELEGRAM_ID` in `.env` locally. Use only plugin IDs you need:

   ```env
   ENABLED_PLUGINS=text_card,space_crawl,text_to_emoji,gothic_metal_title
   JOB_TIMEOUT_SECONDS=1800
   ```

4. Start the stack:

   ```sh
   docker compose up --build
   ```

The bot accepts only private chats. Owner access is permanent; other users require explicit
approval. The bot and worker share the persistent `/data` volume.

### Blender plugin: «Грозовой хром»

`gothic_metal_title` produces an 8-second, 720p, 24fps H.264 video without sound from up to
30 title characters and two lines. It uses a bundled OFL-licensed Latin blackletter font;
Cyrillic falls back to DejaVu Serif and is not guaranteed to look like blackletter.

On macOS, expose Blender to the **worker** process before starting it:

```sh
export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"
blender --version
```

CPU Cycles rendering can take many minutes. Its progress begins after the first completed frame.
One Blender 5.2.2 LTS 1280×720 frame smoke passed locally; a full-duration render, Docker image,
visual quality, Telegram delivery, and cancellation still need target-environment acceptance.

## Project documentation

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Maintainers](MAINTAINERS.md)
- [Support](SUPPORT.md)
- [Architecture](docs/architecture.md)
- [Operations](docs/operations.md)
- [Adding a plugin](docs/adding-plugin.md)
- [Implementation plan](IMPLEMENTATION_PLAN.md)

## License

No project license has been selected yet. Public visibility alone does not grant reuse rights.
Select and add a license before inviting external code contributions or representing the project as
open source.
