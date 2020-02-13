import bpy

from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add

import struct

from io import BytesIO
from math import radians
from mathutils import Vector


#############################
# original code
#############################

magic_number_compressed = b'PK01' # this is the magic number for all compressed files
magic_number_cem = b'SSMF' # this is the magic number for all CEM formats (decompressed)

header = dict()
indices = list()
materials = list()
tag_points = list()
frames = list()

## Blender specific vars
empty = list()
empty_size = 0.05

scale_x = 1
scale_y = 1
scale_z = 1
xVal = 0
yVal = 1    
zVal = 2


def get_num_CEM_parts(binary, start_pos=0, num_cem=1):
    cem_blob = BytesIO(binary)
    cem_blob.seek(start_pos)
    cem_blob.read(28)
    name_length = int.from_bytes(cem_blob.read(4), byteorder='little', signed=False)
    material_name = list()
    material_name.append(cem_blob.read(name_length)[:-1])
    #print(material_name)
    cem = cem_blob.read(-1)
    next_file = cem.find(magic_number_cem)

    if next_file == -1:
        return num_cem, material_name
    else:
        return get_num_CEM_parts(cem, start_pos=next_file+8, num_cem=num_cem+1)

def get_CEM_parts(blob: bytes):
    CEM_parts = list()

    while True:
        next_cem = blob[1:].find(magic_number_cem)
        print(next_cem)
        if next_cem == -1:
            CEM_parts.append(blob)
            return CEM_parts
        else:
            CEM_parts.append(blob[:next_cem+1])
        blob = blob[next_cem+1:]

def parse_file(cem_bytes: bytes):
    print("parsing..........\n")

    cemfile = BytesIO(cem_bytes)

    file_type = cemfile.read(4)

    if magic_number_cem == file_type:
        print("This is a CEM file\n")
    else:
        if magic_number_compressed == file_type:
            print("you need to decompress the file first!")
            return {'CANCELLED'}
        else:
            print("this is not a CEM file \n")
            return {'CANCELLED'}

    # lambdas in order to improve readability
    read_float_buff = lambda: struct.unpack("<f", cemfile.read(4))[0]
    read_uint32_buff = lambda: struct.unpack("<I", cemfile.read(4))[0]

    read_int_buff = lambda x: int.from_bytes(cemfile.read(x), byteorder="little", signed=False)

    header_template = [ "cem_version", "faces", "vertices", "tag_points", "materials", "frames", "child_models", "lod_levels", "name_length" ]

    values = struct.unpack("<IIIIIIIII", cemfile.read(36)) # 9 * 4 bytes = 36
    header = dict(zip(header_template, values))

    header["name"] = cemfile.read(header["name_length"])[:-1] # [:-1] removes the last byte which is a delimiter (0x00) in this case

    header["center"] = struct.unpack("<fff", cemfile.read(12))

    for key, value in header.items():
        print(key, value)
    print("\n########## Header length: %d bytes\n" % (52+header["name_length"]) )


    for _ in range(header["lod_levels"]):
        num_indices = read_uint32_buff()
        triangles = list()

        for _ in range(num_indices):
            triangles.append( struct.unpack("<III", cemfile.read(12)) )

        indices.append( (num_indices, triangles) )

    ###
    #   Structure of the indices variable: indices[LOD_lvl][0: number_faces, 1: values_faces][face][0: x-value, 1: y-value, 2: z-value]
    ###

    tmp = 0
    for x in range(header["lod_levels"]):
        print("LOD level", x+1)
        print("faces:", indices[x][0])
        # print("values:", indices[x][1])
        tmp += 4 + indices[x][0] * 3*4

    print("\n########## Indices length: %d bytes" % tmp )
    print("########## Total length up until here: %d bytes\n" % (tmp + 52+header["name_length"]) )

    ###
    # Structure of the materials variable: 
    #   - materials[material_num][<asset name>]
    #   - materials[material_num]["triangle_selections"][LOD_lvl][0: offset, 1: length]
    ###

    material_template = [ "material_name_length", "material_name", "texture_index", "triangle_selections", "vertex_offset", "vertex_count", "texture_name_length", "texture_name" ]

    for x in range(header["materials"]):
        materials.append(dict.fromkeys(material_template, 0))

        materials[x]["material_name_length"] = read_uint32_buff()
        materials[x]["material_name"] = cemfile.read(materials[x]["material_name_length"])[:-1]
        materials[x]["texture_index"] = read_uint32_buff()
        tmp = list()
        for _ in range(header["lod_levels"]):
            tmp.append( struct.unpack("<II", cemfile.read(8)) )
        materials[x]["triangle_selections"] = tmp
        materials[x]["vertex_offset"] = read_uint32_buff()
        materials[x]["vertex_count"] = read_uint32_buff()
        materials[x]["texture_name_length"] = read_uint32_buff()
        materials[x]["texture_name"] = cemfile.read(materials[x]["texture_name_length"])[:-1]


        for key, value in materials[x].items():
            print(key, value)
        print("\n########## Material%d length: %d bytes\n" % ((x+1),(20 + materials[x]["material_name_length"] + materials[x]["texture_name_length"] + header["lod_levels"]*2*4)) )


    tmp = 0
    for _ in range(header["tag_points"]):
        l = read_uint32_buff()
        tmp += 4+l
        tag_points.append(cemfile.read(l)[:-1])

    print(tag_points)
    print("\n########## Tag points length: %d bytes" % tmp )


    frames_template = [ "radius", "vertices", "tag_points", "transform_matrix", "lower_bound", "upper_bound" ]

    for i in range(header["frames"]):
        frames.append(dict.fromkeys(frames_template, 0))

        frames[i]["radius"] = read_float_buff()
        tmp = list()
        for j in range(header["vertices"]):
            tmp.append(dict())
            tmp[j]["point"] = struct.unpack("<fff", cemfile.read(12))
            tmp[j]["normal"] = struct.unpack("<fff", cemfile.read(12))
            tmp[j]["texture"] = struct.unpack("<ff", cemfile.read(8))
        frames[i]["vertices"] = tmp
        tmp = list()
        for _ in range(header["tag_points"]):
            tmp.append( struct.unpack("<fff", cemfile.read(12)) )
        frames[i]["tag_points"] = tmp
        frames[i]["transform_matrix"] = [
            [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
            [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
            [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
            [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()]
        ]
        frames[i]["lower_bound"] = struct.unpack("<fff", cemfile.read(12))
        frames[i]["upper_bound"] = struct.unpack("<fff", cemfile.read(12))


    # print(frames[0])

    print("########################")
    #print(cemfile.read(-1))

    # print(type(header))
    # print(type(indices))
    # print(type(materials))
    # print(type(tag_points))
    # print(type(frames))
    # print(type(frames[0]))


    # print(indices[9][1])
    # print(frames[0]["tag_points"])
    # print(tag_points)
    #print(materials[0]["triangle_selections"])

    return header, indices, materials, tag_points, frames

"""
saved values:
    header = dict()
    indices = list()
    materials = list()
    tag_points = list()
    frames = list()
"""
#   - materials[material_num]["triangle_selections"][LOD_lvl][0: offset, 1: length]

########################
# blender specific code
########################

def add_point(point_name: str, location: Vector, collection: bpy.types.Collection):
    
    empty.append(bpy.data.objects.new(point_name, None))
    empty[-1].empty_display_size = empty_size
    empty[-1].empty_display_type = 'PLAIN_AXES'

    #bpy.context.collection.objects.link(empty[-1])
    collection.objects.link(empty[-1])
    empty[-1].location = location

def add_object(mesh_name: str, object_name: str, verts: list(), faces: list()):
    scale_x = 1
    scale_y = 1
    
    #verts = [
    #    Vector((-1 * scale_x, 1 * scale_y, 0)),
    #    Vector((1 * scale_x, 1 * scale_y, 0)),
    #    Vector((1 * scale_x, -1 * scale_y, 0)),
    #    Vector((-1 * scale_x, -1 * scale_y, 0)),
    #]
    #faces = [[0, 1, 2, 3]]
    edges = []


    mesh = bpy.data.meshes.new(name=mesh_name)
    mesh.from_pydata(verts, edges, faces)
    mesh.validate(verbose=True)


    new_object = bpy.data.objects.new(object_name, mesh)
    bpy.context.collection.objects.link(new_object)

def rotate_object():
    new_object.rotation_euler.rotate_axis("X", radians(-90))
    # object.rotation_euler.rotate_axis("Z", radians(90))

def add_collection(name: str):
    new_col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(new_col)
    return new_col

def add_collection_child(name: str, parent_collection: bpy.types.Collection):
    new_col = bpy.data.collections.new(name)
    parent_collection.children.link(new_col)
    return new_col

def redraw():
    for area in bpy.context.screen.areas:
        if area.type in ['IMAGE_EDITOR', 'VIEW_3D']:
            area.tag_redraw()

### MAIN function
def main_function_import_file(filename: str, bTagPoints: bool, lod_lvl: int):
    #lod_lvl = 0

    vertices = list()
    faces = list()
    edges = []
    with open(filename, "rb") as f:
        CEM = f.read()
    ###################
    # main function where all the magic happens ;)
    ###################
    header, indices, materials, tag_points, frames = parse_file(CEM)

    print("LOD LEVEL: %s" % lod_lvl)

    main_col = add_collection("CEM importer.LOD %i" % lod_lvl)

    mesh_col = bpy.data.collections.new("objects")
    main_col.children.link(mesh_col)

    # print(header)
    for i in range(header["vertices"]):
        vertices.append( Vector( (frames[0]["vertices"][i]["point"][xVal], frames[0]["vertices"][i]["point"][yVal], frames[0]["vertices"][i]["point"][zVal]) ))    

    ########## add main mesh 
    m = 0
    for j in range(materials[m]["triangle_selections"][lod_lvl][1]): # Material length
        index = j + materials[m]["triangle_selections"][lod_lvl][0] # Material offset
        print(index)
        print(indices[lod_lvl][1][index][xVal])
        print(materials[m]["vertex_offset"])
        x = indices[lod_lvl][1][index][xVal] + materials[m]["vertex_offset"]
        y = indices[lod_lvl][1][index][yVal] + materials[m]["vertex_offset"]
        z = indices[lod_lvl][1][index][zVal] + materials[m]["vertex_offset"]
        faces.append( [x, y, z] )

    plane_mesh = bpy.data.meshes.new(name="Scene Root")
    plane_mesh.from_pydata(vertices, list(), faces)
    plane_mesh.validate(verbose=True)
    plane_object = bpy.data.objects.new("ME 262", plane_mesh)
    #bpy.context.collection.objects.link(plane_object)

    mesh_col.objects.link(plane_object)

    ########## add material to main_object

    if plane_object.data.materials:
        #plane_object.data.materials[0] = bpy.data.materials[0]
        None
    else:
        if bpy.data.materials:
            plane_object.data.materials.append(bpy.data.materials[0])
        else:
            plane_object.data.materials.append(bpy.data.materials.new("CEM Default"))

    ########## add player color mesh

    faces_color = list()
    m = 1
    for j in range(materials[m]["triangle_selections"][lod_lvl][1]): # Material length
        index = j + materials[m]["triangle_selections"][lod_lvl][0] # Material offset    
        x = indices[lod_lvl][1][index][xVal] + materials[m]["vertex_offset"]
        y = indices[lod_lvl][1][index][yVal] + materials[m]["vertex_offset"]
        z = indices[lod_lvl][1][index][zVal] + materials[m]["vertex_offset"]
        faces_color.append( [x, y, z] )


    pl_color_mesh = bpy.data.meshes.new(name="Scene Root")
    pl_color_mesh.from_pydata(vertices, list(), faces_color)
    pl_color_mesh.validate(verbose=True)
    pl_color_object = bpy.data.objects.new("player color", pl_color_mesh)
    #bpy.context.collection.objects.link(pl_color_object)

    mesh_col.objects.link(pl_color_object)


    ########### set player color to blue for viewport

    mat_name = "player color"
    blue_rgba_color = [0.1, 0.1, 1, 1]
    red_rgba_color = [1, 0, 0, 1]

    pl_color_index = bpy.data.materials.find(mat_name)
    if pl_color_index is -1:
        player_color_mat = bpy.data.materials.new(mat_name)
    else:
        player_color_mat = bpy.data.materials[pl_color_index]

    player_color_mat.diffuse_color = blue_rgba_color
    player_color_mat.roughness = 1
    player_color_mat.metallic = 0

    if pl_color_object.data.materials:
        pl_color_object.data.materials[0] = player_color_mat
    else:
        pl_color_object.data.materials.append(player_color_mat)


    ########## add tag points

    if bTagPoints:
        point_col = bpy.data.collections.new("tag points")
        main_col.children.link(point_col)

        for t in range(header["tag_points"]):
            tmp_vector = Vector( (frames[0]["tag_points"][t][xVal], frames[0]["tag_points"][t][yVal], frames[0]["tag_points"][t][zVal]) )
            print(tmp_vector)
            add_point(tag_points[t].decode(), location=tmp_vector, collection=point_col)

    redraw()

    return True

# testpoint = bpy.data.objects.new("test", None)
# testpoint.empty_display_size = 0.2
# testpoint.empty_display_type = "PLAIN_AXES"
# 
# bpy.context.collection.objects.link(testpoint)
# 
# testpoint.location = Vector((0,0,1))

# add_point("MANUELL", Vector((0,0,1)))

# empty.append(bpy.data.objects.new(point_name, None))
# empty[-1].empty_display_size = 0.5
# empty[-1].empty_display_type = 'PLAIN_AXES'
# 
# bpy.context.collection.objects.link(empty[-1])


def cleanup():
    for item in bpy.data.objects:
        bpy.data.objects.remove(item)

    for col in bpy.data.collections:
        bpy.data.collections.remove(col)
    
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
