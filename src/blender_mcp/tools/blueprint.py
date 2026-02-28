"""
Blueprint Tool — Structural breakdown for complex 3D models.
Ported from mezallastudio/antigravity-blender-mcp (TypeScript → Python).

Generates bpy code from a curated database of model blueprints with
style modifiers and dynamic pattern matching for custom types.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("BlenderMCP.Blueprint")


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ComponentSpec:
    name: str
    mesh_type: str  # CUBE, CYLINDER, SPHERE, PLANE, TORUS, CONE
    relative_size: list[float]
    relative_pos: list[float]
    material: str = "MATTE"
    color: list[float] = field(default_factory=lambda: [0.5, 0.5, 0.5])
    optional: bool = False
    children: list["ComponentSpec"] = field(default_factory=list)


@dataclass
class StyleModifier:
    materials: dict[str, str] = field(default_factory=dict)
    extra_components: list[ComponentSpec] = field(default_factory=list)
    color_palette: list[list[float]] = field(default_factory=list)


@dataclass
class Blueprint:
    name: str
    category: str
    components: list[ComponentSpec]
    assembly_order: list[str]
    style_modifiers: dict[str, StyleModifier] = field(default_factory=dict)
    target_verts: int = 500
    can_join: bool = True
    bevel_width: float = 0.01


# ---------------------------------------------------------------------------
# Blueprint Database
# ---------------------------------------------------------------------------

def _c(name: str, mesh: str, size: list, pos: list,
       mat: str = "MATTE", color: list | None = None,
       optional: bool = False) -> ComponentSpec:
    """Shorthand constructor for ComponentSpec."""
    return ComponentSpec(
        name=name, mesh_type=mesh, relative_size=size,
        relative_pos=pos, material=mat,
        color=color or [0.5, 0.5, 0.5], optional=optional,
    )


BLUEPRINTS: dict[str, Blueprint] = {
    "BUILDING": Blueprint(
        name="Building", category="ARCHITECTURE",
        components=[
            _c("foundation", "CUBE", [1.2, 1.2, 0.1], [0, 0, -0.05], "STONE", [0.3, 0.3, 0.3]),
            _c("main_body", "CUBE", [1, 1, 2], [0, 0, 1]),
            _c("roof", "CUBE", [1.1, 1.1, 0.15], [0, 0, 2.1], "MATTE", [0.2, 0.2, 0.25]),
            _c("door", "CUBE", [0.2, 0.05, 0.35], [0, 0.5, 0.175], "WOOD", [0.3, 0.2, 0.1]),
            _c("window_1", "CUBE", [0.15, 0.02, 0.2], [-0.3, 0.5, 0.5], "GLASS", [0.2, 0.3, 0.8]),
            _c("window_2", "CUBE", [0.15, 0.02, 0.2], [0.0, 0.5, 0.5], "GLASS", [0.2, 0.3, 0.8]),
            _c("window_3", "CUBE", [0.15, 0.02, 0.2], [0.3, 0.5, 0.5], "GLASS", [0.2, 0.3, 0.8]),
        ],
        assembly_order=["foundation", "main_body", "roof", "door",
                        "window_1", "window_2", "window_3"],
        style_modifiers={
            "CYBERPUNK": StyleModifier(
                materials={"main_body": "METAL", "roof": "METAL"},
                extra_components=[
                    _c("neon_sign_1", "CUBE", [0.3, 0.02, 0.08], [-0.4, 0.51, 1.5], "GLOW", [0, 1, 1]),
                    _c("neon_sign_2", "CUBE", [0.2, 0.02, 0.05], [0.3, 0.51, 1.8], "GLOW", [1, 0, 1]),
                    _c("pipe_1", "CYLINDER", [0.03, 0.03, 1], [0.45, 0.45, 1], "METAL", [0.4, 0.4, 0.4]),
                    _c("ac_unit", "CUBE", [0.25, 0.15, 0.2], [0.35, 0.4, 0.6], "METAL", [0.6, 0.6, 0.6]),
                    _c("antenna", "CYLINDER", [0.01, 0.01, 0.4], [0.3, 0, 2.4], "METAL"),
                ],
            ),
            "MEDIEVAL": StyleModifier(
                materials={"main_body": "STONE", "roof": "WOOD"},
                extra_components=[
                    _c("chimney", "CUBE", [0.15, 0.15, 0.4], [0.3, 0, 2.3], "STONE", [0.4, 0.35, 0.3]),
                    _c("torch", "CYLINDER", [0.02, 0.02, 0.15], [-0.35, 0.51, 1], "WOOD"),
                    _c("torch_flame", "SPHERE", [0.05, 0.05, 0.08], [-0.35, 0.51, 1.1], "GLOW", [1, 0.5, 0]),
                ],
            ),
            "SCIFI": StyleModifier(
                materials={"main_body": "METAL", "foundation": "METAL"},
                extra_components=[
                    _c("light_strip", "CUBE", [0.9, 0.02, 0.02], [0, 0.51, 0.3], "GLOW", [0, 0.5, 1]),
                    _c("dish", "SPHERE", [0.2, 0.2, 0.1], [0, 0, 2.3], "METAL"),
                ],
            ),
        },
    ),
    "WEAPON": Blueprint(
        name="Weapon", category="PROPS",
        components=[
            _c("receiver", "CUBE", [0.15, 1.0, 0.12], [0, 0, 0], "METAL", [0.15, 0.15, 0.15]),
            _c("barrel", "CYLINDER", [0.025, 0.025, 1.2], [0, 0.9, 0.02], "METAL", [0.2, 0.2, 0.2]),
            _c("stock", "CUBE", [0.08, 0.45, 0.13], [0, -0.5, -0.02], "WOOD", [0.3, 0.2, 0.1]),
            _c("grip", "CUBE", [0.06, 0.08, 0.12], [0, -0.1, -0.12], "PLASTIC", [0.1, 0.1, 0.1]),
            _c("trigger_guard", "TORUS", [0.04, 0.04, 0.02], [0, 0, -0.08], "METAL"),
            _c("magazine", "CUBE", [0.05, 0.12, 0.18], [0, 0.1, -0.15], "METAL", [0.12, 0.12, 0.12]),
            _c("scope", "CYLINDER", [0.035, 0.035, 0.25], [0, 0.1, 0.095], "METAL", [0.1, 0.1, 0.1], optional=True),
        ],
        assembly_order=["receiver", "barrel", "stock", "grip",
                        "trigger_guard", "magazine", "scope"],
        target_verts=300, bevel_width=0.003,
    ),
    "VEHICLE": Blueprint(
        name="Vehicle", category="VEHICLES",
        components=[
            _c("body", "CUBE", [1.8, 4.0, 0.8], [0, 0, 0.5], "METAL", [0.8, 0.1, 0.1]),
            _c("cabin", "CUBE", [1.6, 1.8, 0.7], [0, 0.3, 1.1], "METAL", [0.7, 0.1, 0.1]),
            _c("windshield", "CUBE", [1.5, 0.05, 0.6], [0, 1.1, 1.1], "GLASS", [0.2, 0.3, 0.4]),
            _c("wheel_fl", "CYLINDER", [0.35, 0.35, 0.2], [-0.9, 1.2, 0.35], "PLASTIC", [0.05, 0.05, 0.05]),
            _c("wheel_fr", "CYLINDER", [0.35, 0.35, 0.2], [0.9, 1.2, 0.35], "PLASTIC", [0.05, 0.05, 0.05]),
            _c("wheel_rl", "CYLINDER", [0.35, 0.35, 0.2], [-0.9, -1.2, 0.35], "PLASTIC", [0.05, 0.05, 0.05]),
            _c("wheel_rr", "CYLINDER", [0.35, 0.35, 0.2], [0.9, -1.2, 0.35], "PLASTIC", [0.05, 0.05, 0.05]),
            _c("headlight_l", "SPHERE", [0.15, 0.1, 0.1], [-0.6, 2.0, 0.6], "GLOW", [1, 1, 0.9]),
            _c("headlight_r", "SPHERE", [0.15, 0.1, 0.1], [0.6, 2.0, 0.6], "GLOW", [1, 1, 0.9]),
        ],
        assembly_order=["body", "cabin", "windshield",
                        "wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr",
                        "headlight_l", "headlight_r"],
        can_join=False, target_verts=800, bevel_width=0.02,
    ),
    "ROBOT": Blueprint(
        name="Robot", category="CHARACTER",
        components=[
            _c("torso", "CUBE", [0.6, 0.3, 0.8], [0, 0, 1.2], "METAL", [0.7, 0.7, 0.75]),
            _c("head", "CUBE", [0.35, 0.3, 0.35], [0, 0, 1.8], "METAL", [0.6, 0.6, 0.65]),
            _c("eye_l", "SPHERE", [0.06, 0.06, 0.06], [-0.1, 0.15, 1.85], "GLOW", [0, 0.8, 1]),
            _c("eye_r", "SPHERE", [0.06, 0.06, 0.06], [0.1, 0.15, 1.85], "GLOW", [0, 0.8, 1]),
            _c("arm_l", "CYLINDER", [0.08, 0.08, 0.5], [-0.45, 0, 1.3], "METAL"),
            _c("arm_r", "CYLINDER", [0.08, 0.08, 0.5], [0.45, 0, 1.3], "METAL"),
            _c("leg_l", "CYLINDER", [0.1, 0.1, 0.6], [-0.15, 0, 0.4], "METAL"),
            _c("leg_r", "CYLINDER", [0.1, 0.1, 0.6], [0.15, 0, 0.4], "METAL"),
            _c("foot_l", "CUBE", [0.15, 0.25, 0.05], [-0.15, 0.05, 0.05], "METAL"),
            _c("foot_r", "CUBE", [0.15, 0.25, 0.05], [0.15, 0.05, 0.05], "METAL"),
        ],
        assembly_order=["torso", "head", "eye_l", "eye_r",
                        "arm_l", "arm_r", "leg_l", "leg_r",
                        "foot_l", "foot_r"],
        can_join=False, target_verts=400,
    ),
}


# ---------------------------------------------------------------------------
# Dynamic Pattern Database (for CUSTOM model_type)
# ---------------------------------------------------------------------------

@dataclass
class DynamicPattern:
    keywords: list[str]
    category: str
    suggested_material: str
    base_components: list[ComponentSpec]


DYNAMIC_PATTERNS: list[DynamicPattern] = [
    DynamicPattern(
        keywords=["dog", "cat", "wolf", "fox", "horse", "deer", "lion", "tiger", "bear"],
        category="QUADRUPED", suggested_material="MATTE",
        base_components=[
            _c("body", "SPHERE", [0.5, 1.0, 0.4], [0, 0, 0.5]),
            _c("head", "SPHERE", [0.25, 0.3, 0.25], [0, 0.7, 0.6]),
            _c("snout", "CUBE", [0.1, 0.15, 0.08], [0, 0.9, 0.55]),
            _c("leg_fl", "CYLINDER", [0.06, 0.06, 0.35], [-0.2, 0.35, 0.18]),
            _c("leg_fr", "CYLINDER", [0.06, 0.06, 0.35], [0.2, 0.35, 0.18]),
            _c("leg_bl", "CYLINDER", [0.06, 0.06, 0.35], [-0.2, -0.35, 0.18]),
            _c("leg_br", "CYLINDER", [0.06, 0.06, 0.35], [0.2, -0.35, 0.18]),
            _c("tail", "CYLINDER", [0.04, 0.04, 0.3], [0, -0.6, 0.55]),
        ],
    ),
    DynamicPattern(
        keywords=["dragon", "wyvern", "bird", "eagle", "phoenix", "griffin"],
        category="WINGED_CREATURE", suggested_material="MATTE",
        base_components=[
            _c("body", "SPHERE", [0.4, 1.2, 0.35], [0, 0, 0.5], "MATTE", [0.2, 0.5, 0.2]),
            _c("head", "SPHERE", [0.2, 0.25, 0.2], [0, 0.8, 0.7], "MATTE", [0.2, 0.5, 0.2]),
            _c("neck", "CYLINDER", [0.08, 0.08, 0.3], [0, 0.55, 0.6]),
            _c("wing_l", "PLANE", [0.8, 0.5, 0.02], [-0.6, 0.1, 0.6]),
            _c("wing_r", "PLANE", [0.8, 0.5, 0.02], [0.6, 0.1, 0.6]),
            _c("tail", "CYLINDER", [0.06, 0.06, 0.8], [0, -0.9, 0.4]),
            _c("horn_l", "CONE", [0.03, 0.03, 0.15], [-0.08, 0.75, 0.85]),
            _c("horn_r", "CONE", [0.03, 0.03, 0.15], [0.08, 0.75, 0.85]),
        ],
    ),
    DynamicPattern(
        keywords=["human", "character", "person", "man", "woman", "orc", "elf", "zombie"],
        category="HUMANOID", suggested_material="MATTE",
        base_components=[
            _c("torso", "CUBE", [0.4, 0.25, 0.6], [0, 0, 1.0], "MATTE", [0.7, 0.6, 0.5]),
            _c("head", "SPHERE", [0.18, 0.2, 0.22], [0, 0, 1.5], "MATTE", [0.8, 0.7, 0.6]),
            _c("arm_l", "CYLINDER", [0.05, 0.05, 0.35], [-0.3, 0, 1.1]),
            _c("arm_r", "CYLINDER", [0.05, 0.05, 0.35], [0.3, 0, 1.1]),
            _c("leg_l", "CYLINDER", [0.07, 0.07, 0.4], [-0.1, 0, 0.3]),
            _c("leg_r", "CYLINDER", [0.07, 0.07, 0.4], [0.1, 0, 0.3]),
        ],
    ),
    DynamicPattern(
        keywords=["chair", "sofa", "couch", "bench", "stool"],
        category="SEATING", suggested_material="WOOD",
        base_components=[
            _c("seat", "CUBE", [0.5, 0.5, 0.08], [0, 0, 0.45], "WOOD", [0.4, 0.3, 0.2]),
            _c("backrest", "CUBE", [0.5, 0.08, 0.5], [0, -0.22, 0.75], "WOOD", [0.4, 0.3, 0.2]),
            _c("leg_fl", "CYLINDER", [0.03, 0.03, 0.4], [-0.2, 0.2, 0.2], "WOOD"),
            _c("leg_fr", "CYLINDER", [0.03, 0.03, 0.4], [0.2, 0.2, 0.2], "WOOD"),
            _c("leg_bl", "CYLINDER", [0.03, 0.03, 0.4], [-0.2, -0.2, 0.2], "WOOD"),
            _c("leg_br", "CYLINDER", [0.03, 0.03, 0.4], [0.2, -0.2, 0.2], "WOOD"),
        ],
    ),
    DynamicPattern(
        keywords=["sword", "axe", "hammer", "spear", "shield", "staff"],
        category="MELEE_WEAPON", suggested_material="METAL",
        base_components=[
            _c("blade", "CUBE", [0.08, 0.02, 0.8], [0, 0, 0.6], "METAL", [0.7, 0.7, 0.75]),
            _c("guard", "CUBE", [0.2, 0.03, 0.04], [0, 0, 0.18], "METAL", [0.5, 0.4, 0.2]),
            _c("handle", "CYLINDER", [0.025, 0.025, 0.2], [0, 0, 0.05], "WOOD", [0.3, 0.2, 0.1]),
            _c("pommel", "SPHERE", [0.04, 0.04, 0.04], [0, 0, -0.05], "METAL", [0.5, 0.4, 0.2]),
        ],
    ),
    DynamicPattern(
        keywords=["tree", "plant", "palm", "pine", "oak"],
        category="TREE", suggested_material="WOOD",
        base_components=[
            _c("trunk", "CYLINDER", [0.15, 0.15, 1.0], [0, 0, 0.5], "WOOD", [0.35, 0.25, 0.15]),
            _c("branch_1", "CYLINDER", [0.05, 0.05, 0.4], [-0.2, 0, 0.9], "WOOD", [0.35, 0.25, 0.15]),
            _c("foliage", "SPHERE", [0.6, 0.6, 0.5], [0, 0, 1.3], "MATTE", [0.2, 0.5, 0.15]),
            _c("foliage_2", "SPHERE", [0.45, 0.45, 0.4], [-0.25, 0, 1.1], "MATTE", [0.2, 0.5, 0.15]),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Code Generation
# ---------------------------------------------------------------------------

_MATERIAL_BPY = {
    "METAL":   'bsdf.inputs["Metallic"].default_value = 0.9\nbsdf.inputs["Roughness"].default_value = 0.3',
    "GLASS":   'bsdf.inputs["Metallic"].default_value = 0.0\nbsdf.inputs["Roughness"].default_value = 0.1\nbsdf.inputs["Transmission Weight"].default_value = 0.9',
    "GLOW":    'bsdf.inputs["Emission Strength"].default_value = 5.0\nbsdf.inputs["Emission Color"].default_value = ({r}, {g}, {b}, 1)',
    "PLASTIC": 'bsdf.inputs["Metallic"].default_value = 0.0\nbsdf.inputs["Roughness"].default_value = 0.4',
    "WOOD":    'bsdf.inputs["Metallic"].default_value = 0.0\nbsdf.inputs["Roughness"].default_value = 0.7',
    "STONE":   'bsdf.inputs["Metallic"].default_value = 0.0\nbsdf.inputs["Roughness"].default_value = 0.8',
    "MATTE":   'bsdf.inputs["Metallic"].default_value = 0.0\nbsdf.inputs["Roughness"].default_value = 0.5',
}

_MESH_CONSTRUCTORS = {
    "CUBE":     'bpy.ops.mesh.primitive_cube_add(size=1, location=({x}, {y}, {z}))',
    "CYLINDER": 'bpy.ops.mesh.primitive_cylinder_add(radius={sx}, depth={sz}, location=({x}, {y}, {z}))',
    "SPHERE":   'bpy.ops.mesh.primitive_uv_sphere_add(radius={sx}, location=({x}, {y}, {z}))',
    "PLANE":    'bpy.ops.mesh.primitive_plane_add(size={sx2}, location=({x}, {y}, {z}))',
    "TORUS":    'bpy.ops.mesh.primitive_torus_add(major_radius={sx}, minor_radius={sx4}, location=({x}, {y}, {z}))',
    "CONE":     'bpy.ops.mesh.primitive_cone_add(radius1={sx}, depth={sz}, location=({x}, {y}, {z}))',
}


def _generate_component_code(comp: ComponentSpec, style_mod: Optional[StyleModifier],
                              base_size: float) -> list[str]:
    """Generate bpy lines for a single component."""
    sz = [s * base_size for s in comp.relative_size]
    pos = [p * base_size for p in comp.relative_pos]

    material = comp.material
    color = list(comp.color)

    # Apply style overrides
    if style_mod and comp.name in style_mod.materials:
        material = style_mod.materials[comp.name]

    mesh = comp.mesh_type
    template = _MESH_CONSTRUCTORS.get(mesh, _MESH_CONSTRUCTORS["CUBE"])

    lines = [f"# --- {comp.name} ---"]
    constructor = template.format(
        x=pos[0], y=pos[1], z=pos[2],
        sx=sz[0], sz=sz[2], sx2=sz[0] * 2, sx4=sz[0] / 4,
    )
    lines.append(constructor)
    lines.append("obj = bpy.context.active_object")

    if mesh == "CUBE":
        lines.append(f"obj.scale = ({sz[0]}, {sz[1]}, {sz[2]})")

    lines.append(f'obj.name = "{comp.name}"')
    lines.append("bpy.ops.object.transform_apply(scale=True)")

    # Material
    lines.append(f'mat = bpy.data.materials.new("{comp.name}_mat")')
    lines.append("mat.use_nodes = True")
    lines.append('bsdf = mat.node_tree.nodes["Principled BSDF"]')
    lines.append(f'bsdf.inputs["Base Color"].default_value = ({color[0]}, {color[1]}, {color[2]}, 1)')

    mat_code = _MATERIAL_BPY.get(material, _MATERIAL_BPY["MATTE"])
    mat_code = mat_code.format(r=color[0], g=color[1], b=color[2])
    lines.extend(mat_code.split("\n"))

    lines.append("obj.data.materials.append(mat)")
    lines.append("created_objects.append(obj)")
    lines.append("")
    return lines


def generate_code_from_blueprint(
    bp: Blueprint, style: Optional[str],
    detail_level: str, base_size: float = 2.0,
) -> str:
    """Generate complete bpy script from a Blueprint."""
    lines = [
        "import bpy",
        "from mathutils import Vector",
        "",
        "bpy.ops.object.select_all(action='DESELECT')",
        "created_objects = []",
        "",
    ]

    style_upper = style.upper() if style else None
    style_mod = bp.style_modifiers.get(style_upper) if style_upper else None

    all_comps = list(bp.components)
    if style_mod:
        all_comps.extend(style_mod.extra_components)

    if detail_level == "LOW":
        all_comps = [c for c in all_comps if not c.optional]

    for comp in all_comps:
        lines.extend(_generate_component_code(comp, style_mod, base_size))

    # Join objects if applicable
    if bp.can_join and detail_level != "HIGH":
        label = f"{bp.name}_{style or 'default'}"
        lines.extend([
            "# Join all objects",
            "bpy.ops.object.select_all(action='DESELECT')",
            "for obj in created_objects:",
            "    obj.select_set(True)",
            "bpy.context.view_layer.objects.active = created_objects[0]",
            "bpy.ops.object.join()",
            "final_obj = bpy.context.active_object",
            f'final_obj.name = "{label}"',
        ])
        if bp.bevel_width:
            lines.extend([
                "bpy.ops.object.modifier_add(type='BEVEL')",
                f'final_obj.modifiers["Bevel"].width = {bp.bevel_width}',
                'final_obj.modifiers["Bevel"].segments = 2',
            ])
        lines.append('result = f"Created {final_obj.name} with {len(final_obj.data.vertices)} vertices"')
    else:
        lines.append(f'result = "Created {len(all_comps)} components for {bp.name}"')

    return "\n".join(lines)


def _match_dynamic_pattern(description: str, style: Optional[str]) -> Optional[Blueprint]:
    """Find a dynamic pattern matching the description."""
    desc_lower = description.lower()
    best_pattern: Optional[DynamicPattern] = None
    best_score = 0

    for pattern in DYNAMIC_PATTERNS:
        score = sum(len(kw) for kw in pattern.keywords if kw in desc_lower)
        if score > best_score:
            best_score = score
            best_pattern = pattern

    if not best_pattern:
        return None

    bp = Blueprint(
        name=f"Custom_{best_pattern.category}",
        category=best_pattern.category,
        components=list(best_pattern.base_components),
        assembly_order=[c.name for c in best_pattern.base_components],
        target_verts=400, can_join=True, bevel_width=0.005,
    )

    # Add glow accents for cyberpunk/scifi styles
    if style and style.upper() in ("CYBERPUNK", "SCIFI"):
        bp.components.append(
            _c("glow_accent", "CUBE", [0.02, 0.5, 0.02], [0, 0, 0.8], "GLOW", [0, 1, 1])
        )

    return bp


# ---------------------------------------------------------------------------
# Tool Registration (called from server.py)
# ---------------------------------------------------------------------------

def register_tools(mcp_instance, get_connection_fn):
    """Register the blueprint tool on the MCP server."""

    @mcp_instance.tool()
    def generate_blueprint(
        model_type: str,
        style: str = None,
        detail_level: str = "MEDIUM",
        description: str = None,
    ) -> str:
        """
        Generate a structural blueprint for a complex 3D model and execute
        the corresponding bpy code in Blender.

        Parameters:
        - model_type: BUILDING, WEAPON, VEHICLE, ROBOT, or CUSTOM
        - style: CYBERPUNK, MEDIEVAL, SCIFI, MODERN, FANTASY (optional)
        - detail_level: LOW, MEDIUM, or HIGH (default MEDIUM)
        - description: For CUSTOM type, describe what to create (e.g. "dragon with wings")
        """
        try:
            model_key = model_type.upper()
            bp = BLUEPRINTS.get(model_key)
            is_dynamic = False

            if not bp and model_key == "CUSTOM" and description:
                bp = _match_dynamic_pattern(description, style)
                is_dynamic = True

            if not bp:
                available = list(BLUEPRINTS.keys()) + ["CUSTOM"]
                return json.dumps({
                    "ok": 0,
                    "error": f"Unknown model_type '{model_type}'",
                    "available": available,
                    "hint": "Use CUSTOM with a description for: dragon, dog, human, chair, sword, tree",
                })

            code = generate_code_from_blueprint(bp, style, detail_level.upper())

            blender = get_connection_fn()
            result = blender.send_command("execute_code", {"code": code})

            return json.dumps({
                "ok": 1,
                "name": bp.name,
                "category": bp.category,
                "components": len(bp.components),
                "style": style or "default",
                "detail": detail_level,
                "dynamic": is_dynamic,
                "result": result.get("result", ""),
            })
        except Exception as exc:
            logger.error(f"Blueprint error: {exc}")
            return json.dumps({"ok": 0, "error": str(exc)})
