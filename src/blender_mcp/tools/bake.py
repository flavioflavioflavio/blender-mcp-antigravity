"""Bake Textures Tool — Bake maps to image files. Ported from mezallastudio."""
from __future__ import annotations
import json, logging
logger = logging.getLogger("BlenderMCP.Bake")

VALID_TYPES = ["COMBINED", "DIFFUSE", "NORMAL", "AO", "ROUGHNESS", "METALLIC", "EMIT", "SHADOW"]

def register_tools(mcp_instance, get_connection_fn):
    @mcp_instance.tool()
    def bake_textures(
        object_name: str, output_dir: str,
        bake_types: str = "DIFFUSE,NORMAL,AO",
        resolution: int = 1024, samples: int = 64, margin: int = 4,
    ) -> str:
        """
        Bake texture maps for an object to image files.

        Parameters:
        - object_name: Name of the object to bake
        - output_dir: Directory to save baked images
        - bake_types: Comma-separated bake types: COMBINED, DIFFUSE, NORMAL, AO, ROUGHNESS, METALLIC, EMIT, SHADOW (default "DIFFUSE,NORMAL,AO")
        - resolution: Texture resolution in pixels (default 1024)
        - samples: Bake samples (default 64)
        - margin: Margin in pixels (default 4)
        """
        try:
            types = [t.strip().upper() for t in bake_types.split(",")]
            invalid = [t for t in types if t not in VALID_TYPES]
            if invalid:
                return json.dumps({"ok": 0, "error": f"Invalid bake types: {invalid}", "valid": VALID_TYPES})

            types_str = str(types)
            code = f'''import bpy, os, time, json
start = time.time()
obj = bpy.data.objects.get("{object_name}")
if not obj or obj.type != "MESH":
    result = json.dumps({{"error": "Object not found or not mesh"}})
else:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = {samples}
    out_dir = r"{output_dir}"
    os.makedirs(out_dir, exist_ok=True)
    baked = []
    for bt in {types_str}:
        img = bpy.data.images.new(f"Bake_{{bt}}", {resolution}, {resolution})
        # Ensure material has image texture node
        if obj.data.materials:
            mat = obj.data.materials[0]
            if mat.use_nodes:
                node = mat.node_tree.nodes.new("ShaderNodeTexImage")
                node.image = img
                mat.node_tree.nodes.active = node
        bpy.ops.object.bake(type=bt, margin={margin})
        fpath = os.path.join(out_dir, f"{{obj.name}}_{{bt}}.png")
        img.filepath_raw = fpath
        img.file_format = "PNG"
        img.save()
        baked.append(f"{{obj.name}}_{{bt}}.png")
    elapsed = round(time.time() - start, 2)
    result = json.dumps({{"n": obj.name, "maps": baked, "res": {resolution}, "t": elapsed}})
'''
            bl = get_connection_fn()
            res = bl.send_command("execute_code", {"code": code})
            raw = res.get("result", "{}")
            try:
                data = json.loads(raw)
                if "error" in data:
                    return json.dumps({"ok": 0, "error": data["error"]})
                return json.dumps({"ok": 1, **data})
            except json.JSONDecodeError:
                return json.dumps({"ok": 1, "result": raw})
        except Exception as e:
            logger.error(f"Bake error: {e}")
            return json.dumps({"ok": 0, "error": str(e)})
