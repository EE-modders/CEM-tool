import bpy

from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add

import struct
import numpy as np

from io import BytesIO
from math import radians
from mathutils import Vector

empty = list()

def add_point(point_name: str, location: Vector()):
    
    empty.append(bpy.data.objects.new(point_name, None))
    empty[-1].empty_display_size = 0.5
    empty[-1].empty_display_type = 'PLAIN_AXES'

    bpy.context.collection.objects.link(empty[-1])

    # empty.location = Vector((0, 0, 1))

#############################
# original code
#############################

# cemtool_version = 0.3

magic_number_compressed = b'PK01' # this is the magic number for all compressed files
magic_number_cem = b'SSMF' # this is the magic number for all CEM formats (decompressed)

header = dict()
indices = list()
materials = list()
tag_points = list()
frames = list()

### some math crap
def rot_matrix_x(matrix, degree):
    alpha = np.radians(degree)

    cos, sin = np.cos(alpha), np.sin(alpha)
    rotm = np.matrix([ [1,0,0],[0,cos,-sin],[0,sin,cos] ])

    return np.matmul(rotm, matrix)

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
            exit()
        else:
            print("this is not a CEM file \n")
            exit()

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


# write as obj file for easier debugging
def write_obj(name: str, header: dict(), indices: list(), materials: list(), tag_points: list(), frames: list()):
    filename = name + ".obj"
    xVal = 0
    yVal = 1    
    zVal = 2
    lod_lvl = 0

    with open(filename, "wt") as objfile:
        objfile.write("########## created with CEMtool v%s by zocker_160 \n" % cemtool_version)
        objfile.write("s off \n") # deactivate smooth shader
        n = header["name"].decode()
        if not n: n = "Scene Root"
        objfile.write("o %s \n" % n)

        for i in range(header["vertices"]):

            ### rotate vertices and normals by -90 degree around x axis
            vertex_tmp1 = np.matrix( [ [frames[0]["vertices"][i]["point"][xVal]], [frames[0]["vertices"][i]["point"][yVal]], [frames[0]["vertices"][i]["point"][zVal]] ] )
            vertex_rot1 = rot_matrix_x(vertex_tmp1, -90)
            vertex_tmp2 = np.matrix( [ [frames[0]["vertices"][i]["normal"][xVal]], [frames[0]["vertices"][i]["normal"][yVal]], [frames[0]["vertices"][i]["normal"][zVal]] ] )
            vertex_rot2 = rot_matrix_x(vertex_tmp2, -90)

            objfile.write("v %f %f %f \n" % (vertex_rot1[0].item(), vertex_rot1[1].item(), vertex_rot1[2].item()))
            objfile.write("vn %f %f %f \n" % (vertex_rot2[0].item(), vertex_rot2[1].item(), vertex_rot2[2].item()))
            objfile.write("vt %f %f \n" % (frames[0]["vertices"][i]["texture"][xVal], 1 - frames[0]["vertices"][i]["texture"][yVal]))

        for m in range(header["materials"]):
            objfile.write("# material name: %s, texture name: %s, vertex count: %d \n" % ( materials[m]["material_name"].decode(), materials[m]["texture_name"].decode(), materials[m]["vertex_count"] ))
            n = materials[m]["material_name"].decode()
            if not n: n = "default"
            objfile.write("g %s \n" % n)

            for j in range(materials[m]["triangle_selections"][lod_lvl][1]): # Material length
                index = j + materials[m]["triangle_selections"][lod_lvl][0] # Material offset
                x = indices[lod_lvl][1][index][xVal] + materials[m]["vertex_offset"] + 1 # we need to add 1 for some unknown reason, 0 values are not allowed in OBJ (?)
                y = indices[lod_lvl][1][index][yVal] + materials[m]["vertex_offset"] + 1
                z = indices[lod_lvl][1][index][zVal] + materials[m]["vertex_offset"] + 1

                objfile.write("f %i/%i/%i %i/%i/%i %i/%i/%i \n" % (x, x, x, y, y, y, z, z, z))

        # add tag points to the file
        objfile.write("### tag points \n")
        for t in range(header["tag_points"]):
            objfile.write("o %s \n" % (tag_points[t].decode()))

            vertex_tmp3 = np.matrix( [ [frames[0]["tag_points"][t][xVal]], [frames[0]["tag_points"][t][yVal]], [frames[0]["tag_points"][t][zVal]] ] )
            vertex_rot3 = rot_matrix_x(vertex_tmp1, -90)

            objfile.write("p %f %f %f \n" % (vertex_rot3[0].item(), vertex_rot3[1].item(), vertex_rot3[2].item()))


with open("air_me262_10.cem", "rb") as f:
    CEM = f.read()

header, indices, materials, tag_points, frames = parse_file(CEM)
#write_obj("bismarck1", header, indices, materials, tag_points, frames)

print(header)

########################
# blender specific code
########################

scale_x = 1
scale_y = 1
xVal = 0
yVal = 1    
zVal = 2
lod_lvl = 0

vertices = list()
faces = list()
edges = []

for i in range(header["vertices"]):
    vertices.append( Vector( (frames[0]["vertices"][i]["point"][xVal], frames[0]["vertices"][i]["point"][yVal], frames[0]["vertices"][i]["point"][zVal]) ))    

m = 0
for j in range(materials[m]["triangle_selections"][lod_lvl][1]): # Material length
    index = j + materials[m]["triangle_selections"][lod_lvl][0] # Material offset    
    x = indices[lod_lvl][1][index][xVal] + materials[m]["vertex_offset"]
    y = indices[lod_lvl][1][index][yVal] + materials[m]["vertex_offset"]
    z = indices[lod_lvl][1][index][zVal] + materials[m]["vertex_offset"]
    faces.append( [x, y, z] )


plane_mesh = bpy.data.meshes.new(name="Scene Root")
plane_mesh.from_pydata(vertices, edges, faces)
plane_mesh.validate(verbose=True)
plane_object = bpy.data.objects.new("ME 262", plane_mesh)
bpy.context.collection.objects.link(plane_object)



faces_color = list()

m = 1
for j in range(materials[m]["triangle_selections"][lod_lvl][1]): # Material length
    index = j + materials[m]["triangle_selections"][lod_lvl][0] # Material offset    
    x = indices[lod_lvl][1][index][xVal] + materials[m]["vertex_offset"]
    y = indices[lod_lvl][1][index][yVal] + materials[m]["vertex_offset"]
    z = indices[lod_lvl][1][index][zVal] + materials[m]["vertex_offset"]
    faces_color.append( [x, y, z] )


pl_color_mesh = bpy.data.meshes.new(name="Scene Root")
pl_color_mesh.from_pydata(vertices, edges, faces_color)
pl_color_mesh.validate(verbose=True)
pl_color_object = bpy.data.objects.new("player color", pl_color_mesh)
bpy.context.collection.objects.link(pl_color_object)



for t in range(header["tag_points"]):
    tmp_vector = Vector( (frames[0]["tag_points"][t][xVal], frames[0]["tag_points"][t][yVal], frames[0]["tag_points"][t][zVal]) )
    print(tmp_vector)
    add_point(tag_points[t].decode(), tmp_vector)



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
