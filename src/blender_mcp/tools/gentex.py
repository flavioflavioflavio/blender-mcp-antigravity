"""GenTex Tool — Apply texture from file/URL with auto UV projection. Ported from mezallastudio."""
from __future__ import annotations
import json, logging, os, tempfile
logger = logging.getLogger("BlenderMCP.GenTex")

def _download_image(url: str) -> str | None:
    """Download image from URL to temp file, return path or None."""
    try:
        import requests
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        ext = ".png"
        ct = resp.headers.get("content-type", "")
        if "jpeg" in ct or "jpg" in ct: ext = ".jpg"
        path = os.path.join(tempfile.gettempdir(), f"gentex_{os.getpid()}{ext}")
        with open(path, "wb") as f:
            f.write(resp.content)
        return path
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

def register_tools(mcp_instance, get_connection_fn):
    @mcp_instance.tool()
    def apply_texture_from_file(
        object_name: str, source: str,
        uv_mode: str = "AUTO", tile_x: float = 1.0, tile_y: float = 1.0,
    ) -> str:
        """
        Apply a texture image to an object from a file path or URL.

        Parameters:
        - object_name: Name of the target object
        - source: Local file path or HTTP/HTTPS URL to the texture image
        - uv_mode: UV projection mode: AUTO, BOX, SPHERE, or CYLINDER (default AUTO)
        - tile_x, tile_y: Texture tiling factors (default 1.0)
        """
        try:
            texture_path = source
            if source.startswith("http://") or source.startswith("https://"):
                texture_path = _download_image(source)
                if not texture_path:
                    return json.dumps({"ok": 0, "error": "Failed to download image"})

            if not os.path.exists(texture_path):
                return json.dumps({"ok": 0, "error": f"File not found: {texture_path}"})

            # Normalize path for bpy (forward slashes)
            bpy_path = texture_path.replace("\\", "/")
            uv = uv_mode.upper()

            uv_code = ""
            if uv == "BOX":
                uv_code = '''
    tex_coord = mat.node_tree.nodes.new("ShaderNodeTexCoord")
    mapping = mat.node_tree.nodes.new("ShaderNodeMapping")
    mat.node_tree.links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])
    mat.node_tree.links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])
'''
            elif uv in ("SPHERE", "CYLINDER"):
                uv_code = f'''
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.{"sphere" if uv == "SPHERE" else "cylinder"}_project()
    bpy.ops.object.mode_set(mode="OBJECT")
'''

            code = f'''import bpy
obj = bpy.data.objects.get("{object_name}")
if obj:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    mat = bpy.data.materials.new("{object_name}_Tex")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]

    tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(r"{bpy_path}")
    mat.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
{uv_code}
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    result = f"Applied texture to {{obj.name}} via {{mat.name}}"
else:
    result = "Error: Object not found"
'''
            bl = get_connection_fn()
            res = bl.send_command("execute_code", {"code": code})
            return json.dumps({
                "ok": 1, "name": object_name,
                "texture": os.path.basename(texture_path),
                "uv_mode": uv, "result": res.get("result", ""),
            })
        except Exception as e:
            logger.error(f"GenTex error: {e}")
            return json.dumps({"ok": 0, "error": str(e)})
