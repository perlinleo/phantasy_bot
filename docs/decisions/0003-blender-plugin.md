# Blender is a plugin-local renderer

Requested by the owner: true 3D chrome lettering and storm effects without core changes.
`gothic_metal_title` generates a scene script and JSON in its workspace, invokes Blender
headlessly, reports frame progress through existing JobContext, and encodes H.264 with FFmpeg.
The existing animation result and Telegram handler are reused. No queue, database, worker,
runner protocol or ACL changes are needed for this plugin.

Blender is a large system dependency. CPU Cycles rendering can take minutes: configure
JOB_TIMEOUT_SECONDS explicitly (e.g. 1800; benchmark before production use). The plugin is
opt-in and assumes no GPU. Frames are removed after normal execution/failure; a hard kill can
leave scratch files. Existing worker process groups include Blender/FFmpeg children.

UnifrakturCook Latin blackletter is OFL-licensed; Cyrillic uses DejaVu Serif fallback, which is
not blackletter. Effects use authored geometry/animation rather than fluid simulation.
Blender 3.4+ is required; Blender 5.2.2 LTS successfully rendered the single-frame smoke on
2026-10-14. Docker package compatibility, full-duration performance and visual acceptance remain
unchecked.
