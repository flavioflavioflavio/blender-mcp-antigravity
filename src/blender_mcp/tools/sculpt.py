"""
Sculpt Tool — AI-assisted mesh modification via template-based bpy operations.

Uses keyword matching against natural language operation descriptions
to select pre-built bpy code templates.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("BlenderMCP.Sculpt")


# ---------------------------------------------------------------------------
# Operation Templates
# ---------------------------------------------------------------------------

@dataclass
class OperationTemplate:
    keywords: list[str]
    description: str
    bpy_code: str


OPERATIONS: dict[str, OperationTemplate] = {
    "SUBDIVIDE": OperationTemplate(
        keywords=["smooth", "detail", "subdivide", "refine"],
        description="Add more vertices for detail",
        bpy_code="""\
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.subdivide(number_cuts=2)
bpy.ops.object.mode_set(mode='OBJECT')""",
    ),
    "SPHERIFY": OperationTemplate(
        keywords=["round", "sphere", "ball", "orb"],
        description="Make mesh more spherical",
        bpy_code="""\
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.transform.tosphere(value=0.8)
bpy.ops.object.mode_set(mode='OBJECT')""",
    ),
    "EXTRUDE_UP": OperationTemplate(
        keywords=["horn", "spike", "point", "tower", "tall"],
        description="Extrude vertices upward",
        bpy_code="""\
import bmesh
bm = bmesh.new()
bm.from_mesh(obj.data)
top_verts = [v for v in bm.verts if v.co.z > 0.5 * max(v.co.z for v in bm.verts)]
for v in top_verts:
    v.co.z += 0.5
bm.to_mesh(obj.data)
bm.free()""",
    ),
    "PUSH_FORWARD": OperationTemplate(
        keywords=["nose", "snout", "beak", "forward", "front"],
        description="Push front vertices forward",
        bpy_code="""\
import bmesh
bm = bmesh.new()
bm.from_mesh(obj.data)
front_verts = [v for v in bm.verts if v.co.y > 0.3 * max(v.co.y for v in bm.verts)]
for v in front_verts:
    v.co.y += 0.3
bm.to_mesh(obj.data)
bm.free()""",
    ),
    "INDENT": OperationTemplate(
        keywords=["eye", "socket", "hole", "indent", "depression", "cave"],
        description="Create indentation",
        bpy_code="""\
import bmesh
from mathutils import Vector
bm = bmesh.new()
bm.from_mesh(obj.data)
center_l = Vector((-0.25, 0.4, 0.3))
center_r = Vector((0.25, 0.4, 0.3))
for v in bm.verts:
    dist_l = (v.co - center_l).length
    dist_r = (v.co - center_r).length
    if dist_l < 0.15 or dist_r < 0.15:
        v.co.y -= 0.1
bm.to_mesh(obj.data)
bm.free()""",
    ),
    "SCALE_BOTTOM": OperationTemplate(
        keywords=["base", "bottom", "foot", "stand", "wider", "stable"],
        description="Scale bottom part wider",
        bpy_code="""\
import bmesh
bm = bmesh.new()
bm.from_mesh(obj.data)
min_z = min(v.co.z for v in bm.verts)
max_z = max(v.co.z for v in bm.verts)
for v in bm.verts:
    factor = 1.0 - (v.co.z - min_z) / (max_z - min_z)
    v.co.x *= 1.0 + factor * 0.5
    v.co.y *= 1.0 + factor * 0.5
bm.to_mesh(obj.data)
bm.free()""",
    ),
    "STRETCH_HEIGHT": OperationTemplate(
        keywords=["tall", "stretch", "elongate", "higher"],
        description="Stretch mesh vertically",
        bpy_code="""\
obj.scale.z *= 1.5
bpy.ops.object.transform_apply(scale=True)""",
    ),
    "FLATTEN_TOP": OperationTemplate(
        keywords=["flat", "plateau", "table", "cut"],
        description="Flatten top of mesh",
        bpy_code="""\
import bmesh
bm = bmesh.new()
bm.from_mesh(obj.data)
max_z = max(v.co.z for v in bm.verts)
threshold = max_z * 0.8
for v in bm.verts:
    if v.co.z > threshold:
        v.co.z = threshold
bm.to_mesh(obj.data)
bm.free()""",
    ),
    "PINCH_WAIST": OperationTemplate(
        keywords=["waist", "narrow", "pinch", "hourglass"],
        description="Narrow the middle section",
        bpy_code="""\
import bmesh
bm = bmesh.new()
bm.from_mesh(obj.data)
min_z = min(v.co.z for v in bm.verts)
max_z = max(v.co.z for v in bm.verts)
mid_z = (min_z + max_z) / 2
for v in bm.verts:
    dist = abs(v.co.z - mid_z) / ((max_z - min_z) / 2)
    scale = 0.6 + 0.4 * dist
    v.co.x *= scale
    v.co.y *= scale
bm.to_mesh(obj.data)
bm.free()""",
    ),
    "SMOOTH": OperationTemplate(
        keywords=["smooth", "soften", "blur"],
        description="Smooth the mesh",
        bpy_code="""\
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.vertices_smooth(factor=0.5, repeat=3)
bpy.ops.object.mode_set(mode='OBJECT')""",
    ),
    "NOISE": OperationTemplate(
        keywords=["rough", "noise", "bumpy", "organic", "rocky"],
        description="Add random displacement",
        bpy_code="""\
import bmesh, random
bm = bmesh.new()
bm.from_mesh(obj.data)
for v in bm.verts:
    v.co.x += random.uniform(-0.05, 0.05)
    v.co.y += random.uniform(-0.05, 0.05)
    v.co.z += random.uniform(-0.05, 0.05)
bm.to_mesh(obj.data)
bm.free()""",
    ),
    "BEVEL_EDGES": OperationTemplate(
        keywords=["bevel", "rounded edges", "soft edges", "chamfer"],
        description="Bevel sharp edges",
        bpy_code="""\
bpy.ops.object.modifier_add(type='BEVEL')
obj.modifiers["Bevel"].width = 0.02
obj.modifiers["Bevel"].segments = 3""",
    ),
}

INTENSITY_MULTIPLIERS = {"subtle": 0.5, "normal": 1.0, "extreme": 2.0}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_matching_ops(operation_text: str) -> list[str]:
    """Find operation keys whose keywords match the natural language description."""
    text_lower = operation_text.lower()
    return [
        key for key, tmpl in OPERATIONS.items()
        if any(kw in text_lower for kw in tmpl.keywords)
    ]


def _build_sculpt_code(
    object_name: str,
    matched_ops: list[str],
    intensity: str,
) -> str:
    """Assemble the full bpy script for the sculpt operations."""
    lines = [
        "import bpy",
        "import bmesh",
        "import random",
        "from mathutils import Vector",
        "",
        f'# Sculpt operations for {object_name}',
        f'# Intensity: {intensity}',
        "",
        f'obj = bpy.data.objects.get("{object_name}")',
        'if obj and obj.type == "MESH":',
        "    bpy.context.view_layer.objects.active = obj",
        "    obj.select_set(True)",
        "",
    ]

    if matched_ops:
        for op_key in matched_ops:
            tmpl = OPERATIONS[op_key]
            lines.append(f"    # {tmpl.description}")
            for code_line in tmpl.bpy_code.strip().split("\n"):
                lines.append(f"    {code_line}")
            lines.append("")
    else:
        lines.extend([
            "    # Default: Subdivide and smooth",
            '    bpy.ops.object.mode_set(mode="EDIT")',
            '    bpy.ops.mesh.select_all(action="SELECT")',
            "    bpy.ops.mesh.subdivide(number_cuts=1)",
            "    bpy.ops.mesh.vertices_smooth(factor=0.5)",
            '    bpy.ops.object.mode_set(mode="OBJECT")',
            "",
        ])

    lines.extend([
        "    # Final smooth pass",
        "    bpy.ops.object.shade_smooth()",
        "",
        "    mesh = obj.data",
        '    result = f"Modified {obj.name}: {len(mesh.vertices)} verts, {len(mesh.polygons)} faces"',
        "else:",
        '    result = "Error: Object not found"',
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------

def register_tools(mcp_instance, get_connection_fn):
    """Register the sculpt tool on the MCP server."""

    @mcp_instance.tool()
    def sculpt_mesh(
        object_name: str,
        operation: str,
        intensity: str = "normal",
    ) -> str:
        """
        AI-assisted mesh modification using natural language descriptions.

        Parameters:
        - object_name: Name of the object to sculpt
        - operation: What to do — e.g. "add horns", "make more round", "smooth", "add noise"
        - intensity: subtle, normal, or extreme (default normal)

        Supported operations: smooth, round, horn/spike, nose/snout, eye socket,
        wider base, stretch tall, flatten top, pinch waist, noise/bumpy, bevel edges
        """
        try:
            matched = _find_matching_ops(operation)
            code = _build_sculpt_code(object_name, matched, intensity)

            blender = get_connection_fn()
            result = blender.send_command("execute_code", {"code": code})

            return json.dumps({
                "ok": 1,
                "name": object_name,
                "operation": operation,
                "intensity": intensity,
                "matched_ops": matched if matched else ["DEFAULT"],
                "result": result.get("result", "Modified"),
                "hint": (
                    "No specific operation matched. Applied default subdivide + smooth. "
                    "Try: smooth, horn, nose, eye, stretch, pinch, bevel, noise"
                ) if not matched else None,
            })
        except Exception as exc:
            logger.error(f"Sculpt error: {exc}")
            return json.dumps({"ok": 0, "error": str(exc)})
