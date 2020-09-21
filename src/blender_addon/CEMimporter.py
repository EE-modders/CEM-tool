import bpy

from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add

import os
import sys
import struct

from io import BytesIO
from math import radians
from mathutils import Vector, Matrix
from itertools import chain

#############################
# original code
#############################

magic_number_compressed = b'PK01' # this is the magic number for all compressed files
magic_number_cem = b'SSMF' # this is the magic number for all CEM formats (decompressed)
empty_size = 0.08

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
        return num_cem
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

def parse_cem(cem_bytes: bytes):
    ## import-specific vars
    header = dict()
    indices = list()
    materials = list()
    tag_points = list()
    frames = list()
    ##

    print("parsing..........\n")

    cemfile = BytesIO(cem_bytes)

    file_type = cemfile.read(4)

    if magic_number_cem == file_type:
        print("This is a CEM file\n")
    else:
        if magic_number_compressed == file_type:
            raise TypeError("you need to decompress the file first!")
            return {'CANCELLED'}
        else:
            raise TypeError("this is not a CEM file \n")
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
        print(indices[x][1])
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

def transform_vector(vector: Vector, matrix: Matrix):
    hom_vec = Vector( (vector[0], vector[1], vector[2], 1) )
    hom_vec = matrix @ hom_vec
    kath_vec = Vector( (hom_vec[0] / hom_vec[3], hom_vec[1] / hom_vec[3], hom_vec[2] / hom_vec[3]) )
    return kath_vec

# here is a problem, because in blender empty objects do *NOT* have an origin! (and I need to one not overwrite the world matrix)
# SOLVED: multiplying the inversed world matrix does provice the relative position to origin! (see CEMexporter)
def add_point(point_name: str, location: Vector, trans_matrix: Matrix, collection: bpy.types.Collection, empty: list()):
    empty.append(bpy.data.objects.new(point_name, None))
    empty[-1].empty_display_size = empty_size
    empty[-1].empty_display_type = 'PLAIN_AXES'
    #empty[-1].matrix_world = trans_matrix
    empty[-1].location += transform_vector(vector=location, matrix=trans_matrix)

    #bpy.context.collection.objects.link(empty[-1])
    collection.objects.link(empty[-1])

def add_point_cone(point_name: str, location: Vector, trans_matrix: Matrix, collection: bpy.types.Collection, empty: list()):
    bpy.ops.mesh.primitive_cone_add(calc_uvs=False, vertices=5)
    empty.append(bpy.context.view_layer.objects.active)
    empty[-1].select_set(False)
    empty[-1].name = point_name
    empty[-1].matrix_world = trans_matrix
    empty[-1].location += location

    empty[-1].scale = [0.01] * 3

    collection.objects.link(empty[-1])


def add_empty_cube(cube_name: str, collection: bpy.types.Collection, empty: list()):
    empty.append(bpy.data.objects.new(cube_name, None))
    empty[-1].empty_display_type = 'CUBE'

    collection.objects.link(empty[-1])
    return empty[-1]

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

def add_collection(name: str) -> bpy.types.Collection:
    new_col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(new_col)
    return new_col

def add_collection_child(name: str, parent_collection: bpy.types.Collection) -> bpy.types.Collection:
    new_col = bpy.data.collections.new(name)
    parent_collection.children.link(new_col)
    return new_col

def redraw():
    for area in bpy.context.screen.areas:
        if area.type in ['IMAGE_EDITOR', 'VIEW_3D']:
            area.tag_redraw()

### MAIN function
def main_function_import_file(filename: str, bTagPoints: bool, bTransform: bool, lod_lvl: int, frame_num: int):
    empty = list()
    edges = []
    mesh_col = list()
    

    os_delimiter = os.sep

    with open(filename, "rb") as f:
        CEM = f.read(-1)
    ###################
    # main function where all the magic happens ;)
    ###################
    print(filename)
    CEM_PARTS = get_CEM_parts(CEM)

    print("LOD LEVEL:", lod_lvl)

    main_col_name = filename.split(os_delimiter)[-1]
    main_col = add_collection("M:%s.LOD %i" % (main_col_name, lod_lvl))


    for o, cemobject in enumerate(CEM_PARTS):
        header, indices, materials, tag_points, frames = parse_cem(cemobject)

        print(type(frames))

        # if frame_num is 0 -> import all frames
        if frame_num == 0:
            frame_num = header["frames"]

        # set timeline to number of available frames
        # only set for the first object, it should be the same for all
        if o == 0:
            curr_scene = bpy.context.scene
            curr_scene.frame_current = 0
            curr_scene.frame_start = 0
            curr_scene.frame_end =  curr_scene.frame_start + frame_num - 1


        # array of transformation matrixes to represent the animation
        transformation_matrix = list()
        for f in range(header["frames"]):
            transformation_matrix.append( Matrix(frames[f]["transform_matrix"]) )

        mesh_col.append(add_collection_child(name="%i:%s" % (o+1, header["name"].decode()), parent_collection=main_col))

        for n in range(frame_num):
            ### ADD bounding BOX from the current object
            center_bounding_box = Vector( header["center"] )
            #transformation_matrix = Matrix( frames[n]["transform_matrix"] )
            lower_bound_point = Vector( frames[n]["lower_bound"] )
            upper_bound_point = Vector( frames[n]["upper_bound"] )

            if bTransform:
                center_bounding_box = transform_vector(center_bounding_box, transformation_matrix[n])
                lower_bound_point = transform_vector(lower_bound_point, transformation_matrix[n])
                upper_bound_point = transform_vector(upper_bound_point, transformation_matrix[n])

            if n == 0:
                empty_cube = add_empty_cube("0:BOUNDING BOX:0", mesh_col[o], empty)

            #add_point("lower bound", lower_bound_point, mesh_col[o], empty)
            #add_point("upper bound", upper_bound_point, mesh_col[o], empty)

            empty_cube.location = center_bounding_box
            empty_cube.keyframe_insert('location', frame=n)

            diffVec = (lower_bound_point - upper_bound_point) * 0.5
            empty_cube.scale[xVal] = abs(diffVec[xVal])
            empty_cube.scale[yVal] = abs(diffVec[yVal])
            empty_cube.scale[zVal] = abs(diffVec[zVal])
            empty_cube.keyframe_insert('scale', frame=n)


        ####################################################### vertices get transformed by the matrix saved inside the file:
        """
        example for ship Bismarck:
        ##### Scene Root:
        [[1.0, 0.0, 0.0, 0.0], 
        [0.0, 1.0, 0.0, 0.0], 
        [0.0, 0.0, 1.0, 0.0], 
        [0.0, 0.0, 0.0, 1.0]]

        ##### turret_00
        [[1.0, -1.5099580252808664e-07, 0.0, 0.0], 
        [1.5099580252808664e-07, 1.0, 0.0, 0.4869990050792694], 
        [0.0, 0.0, 1.0, 0.08950112760066986], 
        [0.0, 0.0, 0.0, 1.0]]

        ##### turret_01
        [[1.0, -1.5099580252808664e-07, 0.0, 5.45201972457221e-09], 
        [1.5099580252808664e-07, 1.0, 0.0, 0.3635149300098419], 
        [0.0, 0.0, 1.0, 0.10767261683940887], 
        [0.0, 0.0, 0.0, 1.0]]

        ##### turret_02
        [[-1.0, 3.019916050561733e-07, 0.0, 8.17802980890292e-09], 
        [-3.019916050561733e-07, -1.0, 0.0, -0.5054473876953125], 
        [0.0, 0.0, 1.0, 0.1103220209479332], 
        [0.0, 0.0, 0.0, 1.0]]

        ##### turret_03
        [[-1.0, 3.019916050561733e-07, 0.0, -5.45201972457221e-09], 
        [-3.019916050561733e-07, -1.0, 0.0, -0.6289314031600952], 
        [0.0, 0.0, 1.0, 0.09018093347549438], 
        [0.0, 0.0, 0.0, 1.0]]
        """

        for m in range(header["materials"]):
            faces = list()
            
            plane_object_name = "%i:none:%i" % (m+1, materials[m]["texture_index"])
            if materials[m]["material_name"] is not b'':
                plane_object_name = "%i:%s:%i" % (m+1, materials[m]["material_name"].decode(), materials[m]["texture_index"])
            
            for j in range(materials[m]["triangle_selections"][lod_lvl][1]): # Material length
                index = j + materials[m]["triangle_selections"][lod_lvl][0] # Material offset

                ## debugg stuff
                #print("range %i" % (materials[m]["triangle_selections"][lod_lvl][1]))
                #print("index: %i" % index)
                #print("length: %i" % (len(indices[lod_lvl][1])))
                #print(indices[lod_lvl][1][index][xVal])
                #print(materials[m]["vertex_offset"])

                x = indices[lod_lvl][1][index][xVal]
                y = indices[lod_lvl][1][index][yVal]
                z = indices[lod_lvl][1][index][zVal]
                faces.append( [x, y, z] )
            
            mat_vertex_offset = materials[m]["vertex_offset"]
            mat_vertex_count = materials[m]["vertex_count"]

            main_mesh = bpy.data.meshes.new(name="%s" % materials[m]["texture_name"].decode())
            main_mesh.uv_layers.new(do_init=True)

            for n in range(frame_num):
                vertices = list()
                texture_uvs = list()
                
                for i in range(header["vertices"]):
                    vertex_tmp = Vector( (frames[n]["vertices"][i]["point"][xVal], frames[n]["vertices"][i]["point"][yVal], frames[n]["vertices"][i]["point"][zVal]) )            
                    vertices.append(vertex_tmp)    
                    texture_uvs.append( Vector( (frames[n]["vertices"][i]["texture"][xVal], 1-frames[n]["vertices"][i]["texture"][yVal]) ))
                
                v_tmp = vertices[mat_vertex_offset : mat_vertex_offset + mat_vertex_count]

                if n == 0:
                    main_mesh.from_pydata(v_tmp, list(), faces)
                    main_mesh.validate(verbose=True)

                    ### add UV coords
                    for p, polygon in enumerate(main_mesh.polygons):
                        for i, index in enumerate(polygon.loop_indices):

                            #print("FACE:", faces[p][i])
                            #print("TEXTURE UV:", texture_uvs[faces[p][i]] )
                            #print("INDEX:", index)

                            main_mesh.uv_layers[0].data[index].uv = texture_uvs[mat_vertex_offset : mat_vertex_offset + mat_vertex_count][faces[p][i]]

                    plane_object = bpy.data.objects.new(plane_object_name, main_mesh)
                else:
                    plane_object.data.vertices.foreach_set('co', tuple(chain.from_iterable(v_tmp)))
                    #for i, v in enumerate(plane_object.data.vertices):
                    #    v.co = v_tmp[i]

                if bTransform:
                    plane_object.matrix_world = transformation_matrix[n]

                # create keyframe for animation (all vertices, all UVs and the postition of the object itself)
                for vertex in plane_object.data.vertices:
                    vertex.keyframe_insert('co', frame=n)
                for uv in plane_object.data.uv_layers[0].data:
                    uv.keyframe_insert('uv', frame=n)                
                for pos in ['location', 'rotation_euler', 'scale']:
                    plane_object.keyframe_insert(pos, frame=n)


                # Add vieport material to player color, so that it appears blue
                if n == 0:
                    #bpy.context.collection.objects.link(plane_object)
                    mesh_col[o].objects.link(plane_object)

                    if materials[m]["material_name"] == b'player color':
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

                        if plane_object.data.materials:
                            plane_object.data.materials[0] = player_color_mat
                        else:
                            plane_object.data.materials.append(player_color_mat)
                    else:
                        ########## add material to main_object
                        if plane_object.data.materials:
                            #plane_object.data.materials[0] = bpy.data.materials[0]
                            None
                        else:
                            if bpy.data.materials:
                                plane_object.data.materials.append(bpy.data.materials[0])
                            else:
                                plane_object.data.materials.append(bpy.data.materials.new("CEM Default"))

        ########### add player color mesh
        #faces_color = list()
        #m = 1
        #plane_object_name = "material %i" % (m+1)
        #if materials[m]["material_name"] is not b'':
        #    plane_object_name = "%s" % (materials[m]["material_name"])
        #
        #for j in range(materials[m]["triangle_selections"][lod_lvl][1]): # Material length
        #    index = j + materials[m]["triangle_selections"][lod_lvl][0] # Material offset    
        #    x = indices[lod_lvl][1][index][xVal] + materials[m]["vertex_offset"]
        #    y = indices[lod_lvl][1][index][yVal] + materials[m]["vertex_offset"]
        #    z = indices[lod_lvl][1][index][zVal] + materials[m]["vertex_offset"]
        #    faces_color.append( [x, y, z] )
        #pl_color_mesh = bpy.data.meshes.new(name="mesh_%s" % plane_object_name)
        #pl_color_mesh.from_pydata(vertices, list(), faces_color)
        ### add UV coords
        #pl_color_mesh.uv_layers.new(do_init=True)
        #for p, polygon in enumerate(pl_color_mesh.polygons):
        #    for i, index in enumerate(polygon.loop_indices):
        #        #print("FACE:", faces_color[p][i])
        #        #print("TEXTURE UV:", texture_uvs[faces_color[p][i]] )
        #        pl_color_mesh.uv_layers[0].data[index].uv = texture_uvs[faces_color[p][i]]
        #pl_color_mesh.validate(verbose=True)
        #pl_color_object = bpy.data.objects.new("player color", pl_color_mesh)
        ##bpy.context.collection.objects.link(pl_color_object)
        #mesh_col.objects.link(pl_color_object)


        ########## add tag points
        if bTagPoints:            
            point_col = bpy.data.collections.new("tag points")
            mesh_col[o].children.link(point_col)
            
            for t in range(header["tag_points"]):
                for n in range(frame_num):
                    tmp_vector = Vector( (frames[n]["tag_points"][t][xVal], frames[n]["tag_points"][t][yVal], frames[n]["tag_points"][t][zVal]) )
                    if bTransform:
                        tmp_trans_matrix = transformation_matrix[n]
                    else:
                        tmp_trans_matrix = Matrix() # use identity matrix

                    if n == 0:
                        add_point(point_name=tag_points[t].decode(), location=tmp_vector, trans_matrix=tmp_trans_matrix, collection=point_col, empty=empty)                        
                        #add_point_cone(tag_points[t].decode(), location=tmp_vector, trans_matrix=transformation_matrix, collection=point_col, empty=empty)
                    else:
                        empty[-1].location = transform_vector(vector=tmp_vector, matrix=tmp_trans_matrix)

                    empty[-1].keyframe_insert('location', frame=n)


        print(header)
        print(len(CEM_PARTS))        

        del header
        del indices
        del materials
        del tag_points
        del frames

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
