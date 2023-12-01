import bpy
import bmesh
import numpy as np
from os import listdir
from os.path import isfile, join
from os import getcwd
import argparse
import sys


def get_subdivision(obj):
    for i, mat_slot in enumerate(obj.material_slots):
        bpy.context.object.active_material_index = i
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.material_slot_select()
        me = bpy.context.object.data
        bm = bmesh.from_edit_mesh(me)
        edge_lengths = []
        for e in bm.edges:
            e.select_set(True)
            if e.select:
                edge_lengths.append(int(e.calc_length()))
            e.select_set(False)
        short = min(edge_lengths)
        long = max(edge_lengths)
        long_edges = [edge for edge in bm.edges if int(edge.calc_length()) == long]
        bm.edges.ensure_lookup_table()
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=long)
        bmesh.update_edit_mesh(me)
        bm.edges.ensure_lookup_table()
        short_edges = [edge for edge in bm.edges if int(edge.calc_length()) == short]
        bmesh.ops.subdivide_edges(bm, edges=short_edges, cuts=short)
        bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode="OBJECT")


def load_texture(material, path, freq):
    nodes = material.node_tree.nodes
    imgs = [i.filepath for i in bpy.data.images]
    color = path + "color/" + freq
    grey = path + "grey/" + freq[:-4] + "_grey.png"
    if grey not in imgs:
        map_grey = bpy.data.images.load(filepath=grey)
    else:
        idx = imgs.index(grey)
        map_grey = bpy.data.images[idx]
    if color not in imgs:
        map_color = bpy.data.images.load(filepath=color)
    else:
        idx = imgs.index(color)
        map_color = bpy.data.images[idx]
    nodes["Texture Color"].image = map_color
    nodes["Texture Grey"].image = map_grey


def prep_material(path, name):
    is_field = False
    emi_mat = ""
    for p in bpy.data.materials:
        if p.name == name:
            is_field = True
            emi_mat = p
    if not is_field:
        with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
            data_to.materials = [m for m in data_from.materials if m.startswith("emi")]
        emi_mat = bpy.data.materials[name]
        disp = emi_mat.node_tree.nodes["Displacement.001"]
        disp.inputs["Height"].default_value = 10.5
    return emi_mat


def prep_plane(material):
    is_plane = False
    emi_plane = ""
    board_size = bpy.data.objects["PCB_layer1"].dimensions
    board_loc = bpy.data.objects["PCB_layer1"].location

    heatmap_loc = board_loc.copy()
    heatmap_loc[2] = heatmap_loc[1] + 10
    for b in bpy.data.objects:
        if b.name == "Field":
            is_plane = True
            emi_plane = b
    if not is_plane:
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=heatmap_loc)
        bpy.context.active_object.name = "Field"
        emi_plane = bpy.data.objects["Field"]
        emi_plane.select_set(True)
        bpy.ops.transform.resize(value=board_size)
        bpy.ops.object.transform_apply(scale=True)
        emi_plane.data.materials.append(material)
        get_subdivision(emi_plane)
    return emi_plane


def render_settings(view):
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.feature_set = "SUPPORTED"
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.resolution_x = 880
    bpy.context.scene.render.resolution_y = 800
    for cam in bpy.data.cameras:
        if view in cam.name:
            bpy.context.scene.camera = bpy.data.objects[cam.name]
            break
        else:
            bpy.context.scene.camera = bpy.data.objects["camera_photo"]


def main():
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]
        parser = argparse.ArgumentParser(
            prog="Emi visualisation",
            description="Create a 3D map of electric/magnetic near field of your PCB.",
        )
        parser.add_argument(
            "heatmap_path",
            type=str,
            help="Path to heatmaps generated in previous stages",
        )
        parser.add_argument(
            "-c",
            "--camera",
            nargs="+",
            help="Choose a list of camera names available in board blend. Default is Camera",
            default="Camera",
        )
        parser.add_argument(
            "-rp",
            "--render_path",
            type=str,
            help="Path to save renders",
            default=getcwd(),
        )
        args = parser.parse_known_args(argv)[0]

    # asset material for EMI map shader
    map_mat_path = getcwd() + "/assets/emi_material.blend"

    # get args
    heatmaps = args.heatmap_path
    rpath = args.render_path
    views = args.camera

    # prepare scene with emi map
    hfield = prep_material(map_mat_path, "emi_map")
    prep_plane(hfield)
    cc = heatmaps + "color"
    maps = [f for f in listdir(cc) if isfile(join(cc, f))]
    load_texture(hfield, heatmaps, maps[2])
    # render
    for j in views:
        render_settings(j)
        for i in range(0, len(maps)):
            load_texture(hfield, heatmaps, maps[i])
            bpy.context.scene.render.filepath = rpath + "/" + j + "_" + maps[i]
            bpy.ops.render.render()
            print("Saving render: ", rpath + "/" + j + "_" + maps[i])
            bpy.ops.render.render(use_viewport=True, write_still=True)


if __name__ == "__main__":
    main()
