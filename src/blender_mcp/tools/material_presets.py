"""Material Presets Tool — Apply PBR material presets."""
from __future__ import annotations
import json, logging
logger = logging.getLogger("BlenderMCP.MaterialPresets")

PRESETS = {
    "METALLIC":  {"base": [0.8, 0.8, 0.85], "metallic": 0.95, "roughness": 0.2},
    "PLASTIC":   {"base": [0.8, 0.2, 0.2],  "metallic": 0.0,  "roughness": 0.4},
    "GLASS":     {"base": [0.9, 0.95, 1.0],  "metallic": 0.0,  "roughness": 0.05, "transmission": 0.95},
    "WOOD":      {"base": [0.4, 0.28, 0.15], "metallic": 0.0,  "roughness": 0.7},
    "STONE":     {"base": [0.45, 0.42, 0.4], "metallic": 0.0,  "roughness": 0.85},
    "FABRIC":    {"base": [0.3, 0.25, 0.4],  "metallic": 0.0,  "roughness": 0.9},
    "EMISSIVE":  {"base": [1.0, 0.5, 0.0],   "metallic": 0.0,  "roughness": 0.5, "emission": 5.0},
    "MATTE":     {"base": [0.5, 0.5, 0.5],   "metallic": 0.0,  "roughness": 0.6},
    "RUBBER":    {"base": [0.1, 0.1, 0.1],   "metallic": 0.0,  "roughness": 0.95},
    "GOLD":      {"base": [1.0, 0.76, 0.33], "metallic": 1.0,  "roughness": 0.15},
    "CHROME":    {"base": [0.95, 0.95, 0.95],"metallic": 1.0,  "roughness": 0.05},
}

def register_tools(mcp_instance, get_connection_fn):
    @mcp_instance.tool()
    def set_material_preset(
        object_name: str, preset: str,
        color_r: float = None, color_g: float = None, color_b: float = None,
    ) -> str:
        """
        Apply a PBR material preset to an object.

        Parameters:
        - object_name: Name of the object
        - preset: METALLIC, PLASTIC, GLASS, WOOD, STONE, FABRIC, EMISSIVE, MATTE, RUBBER, GOLD, or CHROME
        - color_r, color_g, color_b: Optional custom base color (0.0-1.0 each)
        """
        try:
            p = PRESETS.get(preset.upper())
            if not p:
                return json.dumps({"ok": 0, "error": f"Unknown preset '{preset}'", "available": list(PRESETS)})

            base = list(p["base"])
            if color_r is not None: base[0] = color_r
            if color_g is not None: base[1] = color_g
            if color_b is not None: base[2] = color_b

            extra = ""
            if p.get("transmission"):
                extra += f'\nbsdf.inputs["Transmission Weight"].default_value = {p["transmission"]}'
            if p.get("emission"):
                extra += f'\nbsdf.inputs["Emission Strength"].default_value = {p["emission"]}'
                extra += f'\nbsdf.inputs["Emission Color"].default_value = ({base[0]},{base[1]},{base[2]},1)'

            code = f'''import bpy
obj = bpy.data.objects.get("{object_name}")
if obj:
    mat = bpy.data.materials.new("{object_name}_{preset.upper()}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = ({base[0]},{base[1]},{base[2]},1)
    bsdf.inputs["Metallic"].default_value = {p["metallic"]}
    bsdf.inputs["Roughness"].default_value = {p["roughness"]}{extra}
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    result = f"Applied {{mat.name}} to {{obj.name}}"
else:
    result = "Error: Object not found"
'''
            bl = get_connection_fn()
            res = bl.send_command("execute_code", {"code": code})
            return json.dumps({"ok": 1, "name": object_name, "preset": preset.upper(), "result": res.get("result", "")})
        except Exception as e:
            logger.error(f"Material preset error: {e}")
            return json.dumps({"ok": 0, "error": str(e)})
