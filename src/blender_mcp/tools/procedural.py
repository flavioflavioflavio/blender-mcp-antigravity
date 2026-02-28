"""
Procedural Generation Tool — Trees, rocks, terrain, buildings.
Ported from mezallastudio (TypeScript → Python).
"""
from __future__ import annotations
import json, logging, random as _random, math
logger = logging.getLogger("BlenderMCP.Procedural")

_COMPLEXITY = {"SIMPLE": 1, "MEDIUM": 2, "COMPLEX": 3}

def _tree(sz, seed, loc, style, cplx):
    th = sz * 0.6; tr = sz * 0.08; fr = sz * 0.4
    L = [
        "import bpy, random, math",
        f"random.seed({seed})", "",
        f"bpy.ops.mesh.primitive_cylinder_add(radius={tr}, depth={th}, location=({loc[0]}, {loc[1]}, {loc[2]+th/2}))",
        'trunk = bpy.context.active_object; trunk.name = "Tree_Trunk"',
        'mat = bpy.data.materials.new("Bark"); mat.use_nodes = True',
        'bsdf = mat.node_tree.nodes["Principled BSDF"]',
        'bsdf.inputs["Base Color"].default_value = (0.35,0.25,0.15,1)',
        'bsdf.inputs["Roughness"].default_value = 0.85',
        'trunk.data.materials.append(mat)', 'created = [trunk]', '',
    ]
    _random.seed(seed)
    for i in range(cplx + 1):
        ox = _random.uniform(-0.3,0.3)*sz; oy = _random.uniform(-0.3,0.3)*sz
        oz = th + _random.uniform(-0.15,0.15)*sz; r = fr*_random.uniform(0.7,1.0)
        g = 0.45+_random.uniform(0,0.15)
        L += [
            f'bpy.ops.mesh.primitive_uv_sphere_add(radius={r:.3f}, location=({loc[0]+ox:.3f},{loc[1]+oy:.3f},{loc[2]+oz:.3f}))',
            f'f=bpy.context.active_object; f.name="Foliage_{i}"',
        ]
        if style == "LOW_POLY":
            L += ["bpy.ops.object.modifier_add(type='DECIMATE')", "f.modifiers['Decimate'].ratio=0.3"]
        L += [
            f'fm=bpy.data.materials.new("Leaves_{i}"); fm.use_nodes=True',
            f'fb=fm.node_tree.nodes["Principled BSDF"]',
            f'fb.inputs["Base Color"].default_value=(0.2,{g:.2f},0.12,1)',
            'f.data.materials.append(fm); created.append(f)', '',
        ]
    L.append('result = f"Created tree with {len(created)} parts"')
    return "\n".join(L)

def _rock(sz, seed, loc, style, cplx):
    seg = 3 + cplx; n = sz*0.1
    L = [
        "import bpy, random, bmesh", f"random.seed({seed})", "",
        f"bpy.ops.mesh.primitive_ico_sphere_add(subdivisions={seg}, radius={sz*0.5}, location=({loc[0]},{loc[1]},{loc[2]}))",
        'rock=bpy.context.active_object; rock.name="Rock"', "",
        "bm=bmesh.new(); bm.from_mesh(rock.data)",
        "for v in bm.verts:",
        f"    v.co.x+=random.uniform(-{n:.3f},{n:.3f})",
        f"    v.co.y+=random.uniform(-{n:.3f},{n:.3f})",
        f"    v.co.z+=random.uniform(-{sz*0.05:.3f},{sz*0.05:.3f})",
        "bm.to_mesh(rock.data); bm.free()", "",
    ]
    if style == "LOW_POLY":
        L += ["bpy.ops.object.modifier_add(type='DECIMATE')", "rock.modifiers['Decimate'].ratio=0.4",
              "bpy.ops.object.modifier_apply(modifier='Decimate')"]
    else:
        L.append("bpy.ops.object.shade_smooth()")
    L += [
        'mat=bpy.data.materials.new("Rock_Mat"); mat.use_nodes=True',
        'bsdf=mat.node_tree.nodes["Principled BSDF"]',
        'bsdf.inputs["Base Color"].default_value=(0.4,0.38,0.35,1)',
        'bsdf.inputs["Roughness"].default_value=0.9',
        'rock.data.materials.append(mat)', '',
        'result=f"Created rock with {len(rock.data.vertices)} vertices"',
    ]
    return "\n".join(L)

def _terrain(sz, seed, loc, style, cplx):
    sub = 10*cplx
    L = [
        "import bpy, random, bmesh, math", f"random.seed({seed})", "",
        f"bpy.ops.mesh.primitive_grid_add(x_subdivisions={sub}, y_subdivisions={sub}, size={sz*2}, location=({loc[0]},{loc[1]},{loc[2]}))",
        'terrain=bpy.context.active_object; terrain.name="Terrain"', "",
        "bm=bmesh.new(); bm.from_mesh(terrain.data)",
        "for v in bm.verts:",
        f"    h=math.sin(v.co.x*2)*0.3+math.cos(v.co.y*3)*0.2+random.uniform(-0.1,0.1)*{sz*0.15:.3f}",
        f"    v.co.z+=h*{sz*0.3:.3f}",
        "bm.to_mesh(terrain.data); bm.free()", "",
        "bpy.ops.object.shade_smooth()", "",
        'mat=bpy.data.materials.new("Terrain_Mat"); mat.use_nodes=True',
        'bsdf=mat.node_tree.nodes["Principled BSDF"]',
        'bsdf.inputs["Base Color"].default_value=(0.3,0.45,0.2,1)',
        'bsdf.inputs["Roughness"].default_value=0.8',
        'terrain.data.materials.append(mat)', '',
        'result=f"Created terrain with {len(terrain.data.vertices)} vertices"',
    ]
    return "\n".join(L)

def _building(sz, seed, loc, style, cplx):
    floors = cplx+1; fh = sz*0.4; w = sz*0.5
    L = ["import bpy, random", f"random.seed({seed})", "", "created=[]", ""]
    for i in range(floors):
        z = loc[2]+i*fh+fh/2
        c = 0.5+i*0.05
        L += [
            f'bpy.ops.mesh.primitive_cube_add(size=1, location=({loc[0]},{loc[1]},{z:.3f}))',
            f'fl=bpy.context.active_object; fl.name="Floor_{i}"',
            f'fl.scale=({w},{w},{fh*0.45})',
            'bpy.ops.object.transform_apply(scale=True)',
            f'mat=bpy.data.materials.new("Floor_{i}_Mat"); mat.use_nodes=True',
            f'bsdf=mat.node_tree.nodes["Principled BSDF"]',
            f'bsdf.inputs["Base Color"].default_value=({c:.2f},{c:.2f},{c+0.05:.2f},1)',
            'fl.data.materials.append(mat); created.append(fl)', '',
        ]
    rz = loc[2]+floors*fh+0.05
    L += [
        f'bpy.ops.mesh.primitive_cube_add(size=1, location=({loc[0]},{loc[1]},{rz:.3f}))',
        f'roof=bpy.context.active_object; roof.name="Roof"',
        f'roof.scale=({w*1.1},{w*1.1},{fh*0.1})',
        'bpy.ops.object.transform_apply(scale=True)',
        'rmat=bpy.data.materials.new("Roof_Mat"); rmat.use_nodes=True',
        'rbsdf=rmat.node_tree.nodes["Principled BSDF"]',
        'rbsdf.inputs["Base Color"].default_value=(0.2,0.2,0.25,1)',
        'roof.data.materials.append(rmat); created.append(roof)', '',
        f'result=f"Created building with {{len(created)}} parts, {floors} floors"',
    ]
    return "\n".join(L)

_GEN = {"TREE": _tree, "ROCK": _rock, "TERRAIN": _terrain, "BUILDING": _building}

def register_tools(mcp_instance, get_connection_fn):
    @mcp_instance.tool()
    def generate_procedural(
        proc_type: str, style: str = "LOW_POLY", size: float = 2.0,
        seed: int = None, location_x: float = 0.0, location_y: float = 0.0,
        location_z: float = 0.0, complexity: str = "MEDIUM",
    ) -> str:
        """
        Generate a procedural 3D object in Blender.

        Parameters:
        - proc_type: TREE, ROCK, TERRAIN, or BUILDING
        - style: LOW_POLY, REALISTIC, or STYLIZED
        - size: Overall size in Blender units (default 2.0)
        - seed: Random seed for reproducibility (optional)
        - location_x/y/z: World position
        - complexity: SIMPLE, MEDIUM, or COMPLEX
        """
        try:
            gen = _GEN.get(proc_type.upper())
            if not gen:
                return json.dumps({"ok":0,"error":f"Unknown '{proc_type}'","available":list(_GEN)})
            s = seed if seed is not None else _random.randint(0,99999)
            _random.seed(s)
            code = gen(size, s, [location_x, location_y, location_z],
                       style.upper(), _COMPLEXITY.get(complexity.upper(), 2))
            bl = get_connection_fn()
            res = bl.send_command("execute_code", {"code": code})
            return json.dumps({"ok":1,"type":proc_type.upper(),"seed":s,"result":res.get("result","")})
        except Exception as e:
            logger.error(f"Procedural error: {e}")
            return json.dumps({"ok":0,"error":str(e)})
