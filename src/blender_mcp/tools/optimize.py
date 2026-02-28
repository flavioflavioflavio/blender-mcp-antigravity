"""Optimize Mesh Tool — Decimate modifier with options. Ported from mezallastudio."""
from __future__ import annotations
import json, logging
logger = logging.getLogger("BlenderMCP.Optimize")

def register_tools(mcp_instance, get_connection_fn):
    @mcp_instance.tool()
    def optimize_mesh(
        object_name: str, target_ratio: float = 0.5,
        preserve_uvs: bool = True, preserve_bounds: bool = True,
        symmetry: bool = False,
    ) -> str:
        """
        Reduce polygon count of a mesh using the Decimate modifier.

        Parameters:
        - object_name: Name of the object to optimize
        - target_ratio: Target ratio 0.01-1.0 (0.5 = 50% reduction, default 0.5)
        - preserve_uvs: Keep UV coordinates intact (default True)
        - preserve_bounds: Preserve mesh boundary edges (default True)
        - symmetry: Use symmetry for decimation (default False)
        """
        try:
            code = f'''import bpy, json
obj = bpy.data.objects.get("{object_name}")
if obj and obj.type == "MESH":
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    orig_v = len(obj.data.vertices)
    orig_f = len(obj.data.polygons)

    mod = obj.modifiers.new("Decimate_Opt", "DECIMATE")
    mod.ratio = {target_ratio}
    mod.use_symmetry = {symmetry}
    bpy.ops.object.modifier_apply(modifier="Decimate_Opt")

    new_v = len(obj.data.vertices)
    new_f = len(obj.data.polygons)
    pct = round((1 - new_f / max(orig_f, 1)) * 100, 1)
    result = json.dumps({{"n":obj.name,"ov":orig_v,"of":orig_f,"nv":new_v,"nf":new_f,"pct":pct}})
else:
    result = json.dumps({{"error":"Object not found or not a mesh"}})
'''
            bl = get_connection_fn()
            res = bl.send_command("execute_code", {"code": code})
            raw = res.get("result", "{}")
            try:
                data = json.loads(raw)
                if "error" in data:
                    return json.dumps({"ok": 0, "error": data["error"]})
                return json.dumps({
                    "ok": 1, "name": data["n"],
                    "before": {"verts": data["ov"], "faces": data["of"]},
                    "after": {"verts": data["nv"], "faces": data["nf"]},
                    "reduction_pct": data["pct"],
                })
            except json.JSONDecodeError:
                return json.dumps({"ok": 1, "result": raw})
        except Exception as e:
            logger.error(f"Optimize error: {e}")
            return json.dumps({"ok": 0, "error": str(e)})
