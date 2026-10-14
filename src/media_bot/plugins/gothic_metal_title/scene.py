"""Blender-only scene template. Executed by Blender's bundled Python, not the bot interpreter."""

SCENE_SCRIPT = r"""
import bpy
import json
import math
import random
import sys
from pathlib import Path
from mathutils import Vector

config = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text())
if bpy.app.version < (3, 4, 0):
    raise RuntimeError('Blender 3.4 or newer is required')
root = Path(config['workspace'])
rng = random.Random(17)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = config['samples']
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.fps = config['fps']
scene.frame_end = config['duration_seconds'] * config['fps']
scene.world.color = (0.008, 0.009, 0.014)
scene.view_settings.view_transform = 'AgX'

def material(name, color, metallic=0, roughness=0.3, emission=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    emission_color = shader.inputs.get('Emission Color') or shader.inputs.get('Emission')
    if emission_color is not None:
        emission_color.default_value = (*color, 1)
    shader.inputs['Emission Strength'].default_value = emission
    return mat

chrome = material('Mirror chrome', (0.8, 0.85, 0.94), 1, 0.12)
blood = material('Wet dark crimson', (0.18, 0.001, 0.004), 0, 0.16)
floor_mat = material('Wet obsidian', (0.012, 0.014, 0.021), 0.75, 0.18)
rain_mat = material('Cold rain streaks', (0.23, 0.36, 0.5), 0.5, 0.12, 0.4)
lightning_mat = material('Lightning', (0.65, 0.8, 1), emission=12)

def curve(name, points, radius, mat):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for p, xyz in zip(spline.points, points):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def light(name, location, color, power, size, target=(0, 0, 0)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.color = color
    data.shape = 'RECTANGLE'
    data.size = size
    data.size_y = 0.5
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj

bpy.ops.object.empty_add()
title_root = bpy.context.object
title_root.name = 'Animated title and blood'
text = bpy.data.curves.new('Extruded gothic lettering', 'FONT')
text.body = config['text']
text.align_x = 'CENTER'
text.align_y = 'CENTER'
text.extrude = 0.13
text.bevel_depth = 0.022
text.bevel_resolution = 4
text.space_line = 1.15
font_candidates = [
    Path(config['font']),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'),
]
if any(ord(c) > 127 for c in config['text']):
    font_candidates = font_candidates[1:]
for font_path in font_candidates:
    if font_path.exists():
        text.font = bpy.data.fonts.load(str(font_path))
        break
obj = bpy.data.objects.new('Chrome title', text)
scene.collection.objects.link(obj)
obj.data.materials.append(chrome)
obj.parent = title_root
bpy.context.view_layer.update()
scale = min(8 / max(obj.dimensions.x, 0.1), 2.4 / max(obj.dimensions.y, 0.1))
obj.scale = (scale,) * 3
bpy.context.view_layer.update()

# Find occupied glyph surface positions instead of putting blood in spaces.
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.convert(target='MESH')
obj = bpy.context.object
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
front = max(v.co.z for v in obj.data.vertices)
vertices = [v.co.copy() for v in obj.data.vertices if v.co.z > front - 0.03]
for i in range(min(12, len(vertices))):
    start = rng.choice(vertices)
    length = rng.uniform(0.18, 0.6)
    drip = curve('Blood rivulet', [
        (start.x, start.y, front + 0.012),
        (start.x + 0.018, start.y - length * 0.5, front + 0.018),
        (start.x, start.y - length, front + 0.02),
    ], rng.uniform(0.009, 0.018), blood)
    drip.parent = title_root
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
        radius=0.035, location=(start.x, start.y - length, front + 0.025))
    drop = bpy.context.object
    drop.data.materials.append(blood)
    drop.parent = title_root
    drop.scale = (0.65, 1.4, 0.7)
    drop.keyframe_insert('location', frame=1)
    drop.location.y -= 0.22
    drop.keyframe_insert('location', frame=scene.frame_end)

for frame, angle in [(1, -8), (scene.frame_end // 2, 8), (scene.frame_end, -8)]:
    title_root.rotation_euler = (math.radians(3), math.radians(angle), math.radians(-1))
    title_root.keyframe_insert('rotation_euler', frame=frame)

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, -1.9, 0))
floor = bpy.context.object
floor.rotation_euler.x = math.pi / 2
floor.data.materials.append(floor_mat)
key = light('White moving softbox', (-4, 3, 6), (1, 0.95, 0.9), 1800, 5)
key.keyframe_insert('location', frame=1)
key.location.x = 4
key.keyframe_insert('location', frame=scene.frame_end)
light('Chrome edge strip', (4, 1, 4), (0.6, 0.75, 1), 1200, 3)
light('Crimson rim', (0, 2, -2), (1, 0.005, 0.01), 2400, 6)
light('Red floor glow', (0, -1.5, 2), (1, 0.01, 0.015), 500, 5)

# A bounded volumetric fog bank below the face, not an opaque overlay.
fog_mat = bpy.data.materials.new('Low storm fog')
fog_mat.use_nodes = True
nodes = fog_mat.node_tree.nodes
nodes.clear()
out = nodes.new('ShaderNodeOutputMaterial')
volume = nodes.new('ShaderNodeVolumePrincipled')
volume.inputs['Density'].default_value = 0.035
volume.inputs['Color'].default_value = (0.28, 0.32, 0.4, 1)
fog_mat.node_tree.links.new(volume.outputs['Volume'], out.inputs['Volume'])
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -1.5, -0.8))
fog = bpy.context.object
fog.scale = (13, 1.1, 5)
fog.data.materials.append(fog_mat)
fog.keyframe_insert('location', frame=1)
fog.location.x = 1.3
fog.keyframe_insert('location', frame=scene.frame_end)

rain = []
for i in range(160):
    x, y, z = rng.uniform(-7, 7), rng.uniform(-2.5, 4), rng.uniform(-3, 4)
    streak = curve('Rain', [(0, 0, 0), (-0.035, -0.18, 0)], 0.003, rain_mat)
    streak.location = (x, y, z)
    rain.append((streak, x, y, z))

bolts = []
for x in (-4.6, 4.6):
    points = [(x + rng.uniform(-0.35, 0.35), 3.5 - j * 0.35, -3) for j in range(13)]
    bolts.append(curve('Distant lightning', points, 0.015, lightning_mat))
flash = light('Storm flash', (0, 4, 2), (0.65, 0.8, 1), 0, 8)

bpy.ops.object.camera_add(location=(0, 0.7, 14))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 42
scene.camera = camera
camera.keyframe_insert('location', frame=1)
camera.location.z = 13
camera.keyframe_insert('location', frame=scene.frame_end)
# Glow comes from actual crimson lights and emissive lightning. Blender 5.2's compositor
# Glare node no longer exposes the former glare_type/threshold properties, so no fragile
# post-process effect is used here.
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'scene.blend'))
for frame in range(1, scene.frame_end + 1):
    scene.frame_set(frame)
    for streak, x, y, z in rain:
        streak.location = (x - (frame % 18) * 0.025, (y - frame * 0.17 + 2.5) % 6.5 - 2.5, z)
        streak.keyframe_insert('location', frame=frame)
    pulse = any(abs(frame - int(scene.frame_end * t)) < 2 for t in (0.23, 0.63, 0.82))
    for bolt in bolts:
        bolt.hide_render = not pulse
        bolt.keyframe_insert('hide_render', frame=frame)
    flash.data.energy = 2800 if pulse else 0
    flash.data.keyframe_insert('energy', frame=frame)
    scene.render.filepath = str(root / 'frames' / f'{frame:04d}.png')
    bpy.ops.render.render(write_still=True)
    print(f'PHANTASY_FRAME {frame}', flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'scene.blend'))
"""
