# Adding a plugin

1. Add a trusted package under `src/media_bot/plugins/<plugin_id>/` with `Input`, `Options`,
   `run`, and `SPEC`.
2. Give the plugin immutable `id`, explicit version, title, description, category, tags and tight
   Pydantic limits.
3. Write only to `JobContext.workspace`; return relative artifact paths. Do not import aiogram,
   SQLAlchemy, ACL, or delivery code.
4. Register the spec in `plugins/registry.py` and add tests, including a small valid media check
   when applicable.
5. Reuse existing result/delivery types. Extend the core protocol only when a concrete plugin
   requires it, and document that decision in `docs/decisions/`.
6. Add assets with their license and attribution. Never add user input or generated media.
7. Run `make check` and state unavailable live/Docker checks in the PR.

Character-based plugins can use optional `JobContext.assets_root` for operator-installed,
versioned artwork. See [character plugins](character-plugins.md) for the pinned manifest,
startup checks, process-boundary forwarding and Compose overlay. Keep generated artwork
out of Git and Docker context; do not download it during a user's render.
