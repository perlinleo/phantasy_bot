# Character artwork is an external, pinned resource pack

The two character plugins use Pillow compositing and the existing FFmpeg delivery path.
The original implementation plan is in
[glamour-and-comedy-plugins.md](../plans/glamour-and-comedy-plugins.md).

Generated artwork must stay out of Git under AGENTS.md. The accepted atlas PNGs live in
`output/plugin-assets/v1/`, with a separate archive for transfer to the operator's host.
`src/media_bot/assets/characters-v1.json` records their exact SHA-256, dimensions, sprite bounds,
and palm anchors. There is no runtime network dependency or image-generation credential.
The operator installs this pack and enables the plugins explicitly. Missing, modified or
incorrectly sized resources fail before bot polling/worker claiming; the runner checks again.
Updating artwork requires a new immutable pack and an explicit plugin version bump.

`Settings.plugin_assets_dir` passes through a fixed `run-payload --assets-root` argument into
`JobContext.assets_root`. This is a concrete SDK/CLI extension needed by these renderers.
The JSON result protocol, SQLite schema, queue and delivery handlers do not change. The child
continues receiving only the existing minimal environment; it does not load the bot's `.env`.
An optional Compose overlay supplies the same read-only path to bot and worker. The default
stack and old plugins require no artwork. Generated outputs are also excluded from Docker context.

## Visual choices made during implementation

- Models support letters on cupped palms, with per-character measured anchors. This replaced
  the proposed side-grip masks: the accepted artwork provides a visible, consistent support
  point for both narrow and wide glyphs. Letter faces, extrusion, contact shadows and glints
  are rendered in code. The original text is stored unchanged; NFC is used only for display.
- Four distinct models are reused across longer strings. Presets change the stage and metal
  palette, not the underlying dresses. There is no promise of a unique face for all 12 glyphs.
- The comedy scene uses two authored full-body poses per host, short interpolated transitions,
  small body movement and moving stage light. It does not claim skeletal animation, lip sync,
  independently articulated fingers or a real performance by either person. The characters
  are recognizably illustrated caricatures; the user's text appears on a separate board.
- Neither plugin adds custom emoji publication or sound. Telegram delivery uses existing PNG
  and silent H.264 animation support. The board stays fixed throughout its reading interval.

These choices keep the effects usable on CPU without Blender, new SaaS dependencies, or
pretending generated lettering can reproduce arbitrary user input reliably.
