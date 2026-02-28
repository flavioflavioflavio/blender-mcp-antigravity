"""Render Preview Tool — Full render to file. Ported from mezallastudio."""
from __future__ import annotations
import json, logging
logger = logging.getLogger("BlenderMCP.Render")

def register_tools(mcp_instance, get_connection_fn):
    @mcp_instance.tool()
    def render_scene(
        output_path: str, width: int = 512, height: int = 512,
        camera_angle: str = "ISOMETRIC", samples: int = 32,
        transparent: bool = False,
    ) -> str:
        """
        Render the current scene to a file.

        Parameters:
        - output_path: Output file path (.png or .jpg)
        - width: Render width in pixels (default 512)
        - height: Render height in pixels (default 512)
        - camera_angle: FRONT, TOP, SIDE, ISOMETRIC, or CURRENT (default ISOMETRIC)
        - samples: Render samples (default 32)
        - transparent: Transparent background (default False)
        """
        try:
            cam_setup = ""
            angle = camera_angle.upper()
            if angle != "CURRENT":
                cam_positions = {
                    "FRONT":     "(0, -10, 1)",
                    "TOP":       "(0, 0, 10)",
                    "SIDE":      "(10, 0, 1)",
                    "ISOMETRIC": "(7, -7, 5)",
                }
                pos = cam_positions.get(angle, "(7, -7, 5)")
                cam_setup = f'''
# Setup camera
import mathutils
cam_data = bpy.data.cameras.new("RenderCam")
cam_obj = bpy.data.objects.new("RenderCam", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
cam_obj.location = {pos}
direction = mathutils.Vector((0,0,0)) - cam_obj.location
rot = direction.to_track_quat('-Z','Y')
cam_obj.rotation_euler = rot.to_euler()
bpy.context.scene.camera = cam_obj
'''
            code = f'''import bpy, time
start = time.time()
scene = bpy.context.scene
scene.render.resolution_x = {width}
scene.render.resolution_y = {height}
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = r"{output_path}"
scene.cycles.samples = {samples} if scene.render.engine == "CYCLES" else {samples}
scene.render.film_transparent = {transparent}
{cam_setup}
bpy.ops.render.render(write_still=True)
elapsed = round(time.time() - start, 2)
import os
kb = round(os.path.getsize(r"{output_path}") / 1024, 1) if os.path.exists(r"{output_path}") else 0
result = f"Rendered to {output_path} in {{elapsed}}s ({{kb}}KB)"
'''
            bl = get_connection_fn()
            res = bl.send_command("execute_code", {"code": code})
            return json.dumps({
                "ok": 1, "path": output_path,
                "resolution": [width, height],
                "result": res.get("result", ""),
            })
        except Exception as e:
            logger.error(f"Render error: {e}")
            return json.dumps({"ok": 0, "error": str(e)})
