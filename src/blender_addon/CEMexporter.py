import bpy

from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add

from .messagebox import ShowMessageBox

import sys
import struct

from io import BytesIO
from math import radians
from mathutils import Vector, Matrix


#############################
# original code
#############################

magic_number_compressed = b'PK01' # this is the magic number for all compressed files
magic_number_cem = b'SSMF' # this is the magic number for all CEM formats (decompressed)

scale_x = 1
scale_y = 1
scale_z = 1
xVal = 0
yVal = 1
zVal = 2


def generate_cem( header: dict(), indices: list(), materials: list(), tag_points: list(), frames: list() ):
    xVal = 0
    yVal = 1
    zVal = 2
    lod_lvl = 0 #  only one LOD level will get exported
    frame_num = 0 # only the first Frame will get exported (no animations for now)

    write_uint32 = lambda x: cemfile.write(struct.pack("<I", x))
    write_float = lambda x: cemfile.write(struct.pack("<f", x))

    header["lod_levels"] = 1 ## this is 1, because only one LOD level gets exported

    ### write header

    cemfile = BytesIO(b'')

    cemfile.write(magic_number_cem)
    cemfile.write( struct.pack("<IIIIIIIII", 
        header["cem_version"],
        header["faces"],
        header["vertices"],
        header["tag_points"],
        header["materials"],
        header["frames"],
        header["child_models"],
        header["lod_levels"],
        header["name_length"]
    ) )

    cemfile.write(header["name"] + b'\x00')
    cemfile.write( struct.pack("<fff", header["center"][xVal], header["center"][yVal], header["center"][zVal]) )

    ### write indices

    write_uint32(indices[lod_lvl][0])
    for face in indices[lod_lvl][1]:
        cemfile.write( struct.pack("<III", face[xVal], face[yVal], face[zVal]) )

    ### write materials

    for i in range(header["materials"]):
        write_uint32(materials[i]["material_name_length"])
        cemfile.write(materials[i]["material_name"] + b'\x00')
        write_uint32(materials[i]["texture_index"])
        cemfile.write( struct.pack("<II", materials[i]["triangle_selections"][lod_lvl][0], materials[i]["triangle_selections"][lod_lvl][1]) )
        cemfile.write( struct.pack("<III",
            materials[i]["vertex_offset"],
            materials[i]["vertex_count"],
            materials[i]["texture_name_length"]
        ) )
        cemfile.write(materials[i]["texture_name"] + b'\x00')

    ### write tag points

    for tpoint in tag_points:
        write_uint32(len(tpoint) + 1)
        cemfile.write(tpoint + b'\x00')

    ### write frames

    write_float(frames[frame_num]["radius"])
    for i in range(header["vertices"]):
        cemfile.write( struct.pack("<fff", 
            frames[frame_num]["vertices"][i]["point"][xVal],
            frames[frame_num]["vertices"][i]["point"][yVal],
            frames[frame_num]["vertices"][i]["point"][zVal]
        ) )
        cemfile.write( struct.pack("<fff", 
            frames[frame_num]["vertices"][i]["normal"][xVal],
            frames[frame_num]["vertices"][i]["normal"][yVal],
            frames[frame_num]["vertices"][i]["normal"][zVal]
        ) )
        cemfile.write( struct.pack("<ff",
            frames[frame_num]["vertices"][i]["texture"][xVal],
            1-frames[frame_num]["vertices"][i]["texture"][yVal]
        ) )
    for tpoint in frames[frame_num]["tag_points"]:
        cemfile.write( struct.pack("<fff", tpoint[xVal], tpoint[yVal], tpoint[zVal]) )
    cemfile.write( struct.pack("<ffffffffffffffff",
        frames[frame_num]["transform_matrix"][0][0], frames[frame_num]["transform_matrix"][0][1], frames[frame_num]["transform_matrix"][0][2], frames[frame_num]["transform_matrix"][0][3],
        frames[frame_num]["transform_matrix"][1][0], frames[frame_num]["transform_matrix"][1][1], frames[frame_num]["transform_matrix"][1][2], frames[frame_num]["transform_matrix"][1][3],
        frames[frame_num]["transform_matrix"][2][0], frames[frame_num]["transform_matrix"][2][1], frames[frame_num]["transform_matrix"][2][2], frames[frame_num]["transform_matrix"][2][3],
        frames[frame_num]["transform_matrix"][3][0], frames[frame_num]["transform_matrix"][3][1], frames[frame_num]["transform_matrix"][3][2], frames[frame_num]["transform_matrix"][3][3],
    ) )
    cemfile.write( struct.pack("<fff", 
        frames[frame_num]["lower_bound"][xVal],
        frames[frame_num]["lower_bound"][yVal],
        frames[frame_num]["lower_bound"][zVal],
    ) )
    cemfile.write( struct.pack("<fff", 
        frames[frame_num]["upper_bound"][xVal],
        frames[frame_num]["upper_bound"][yVal],
        frames[frame_num]["upper_bound"][zVal],
    ) )

    return cemfile.getvalue()

########################
# blender specific code
########################

def inverse_transform_vector(vector: Vector, matrix: Matrix):
    hom_vec = Vector( (vector[0], vector[1], vector[2], 1) )
    hom_vec = matrix.inverted() @ hom_vec
    kath_vec = Vector( (hom_vec[0] / hom_vec[3], hom_vec[1] / hom_vec[3], hom_vec[2] / hom_vec[3]) )
    return kath_vec

def generate_header_info(mesh_col: bpy.types.Collection):
    nVerts = 0
    nFaces = 0
    nMaterials = 0
    bbox_center = Vector()
    bbox_points = list()

    for obj in mesh_col.objects:
        try:
            nVerts += len(obj.data.vertices)
            nFaces += len(obj.data.polygons)
            nMaterials += 1
            bbox_points += obj.bound_box
        except AttributeError: # Bounding Box doesn't have vertices attribute
            if "BOUNDING BOX" in obj.name:            
                None ## ignore
                #bbox_center = obj.location
                #bbox_scale = obj.scale

    return nVerts, nFaces, nMaterials, bbox_points # bbox_center, bbox_scale

def get_vertex_data(blobject: bpy.types.Object):
    '''returns all vertices, normals, uvs, vertex_indices and the number of vertices of the blender object'''
    vertices = [ v.co for v in blobject.data.vertices ]
    normals = [ v.normal for v in blobject.data.vertices ]

    num_vertices = len(vertices)
    uvs = [0] * num_vertices
    indices = list()

    for polygon in blobject.data.polygons:
        tmp = list()
        for loop_index in polygon.loop_indices:
            v_index = blobject.data.loops[loop_index].vertex_index
            tmp.append(v_index)

            uvs[v_index] = blobject.data.uv_layers[0].data[loop_index].uv
        indices.append(tmp)

    return vertices, normals, uvs, indices, num_vertices

def get_bounds(bounding_box: list):
    maxV = Vector( max(bounding_box, key=sum) )
    minV = Vector( min(bounding_box, key=sum) )

    centerP = (maxV - minV) * 0.5 + minV

    return maxV, minV, centerP

def check_transforms(blobject: bpy.types.Object):
    for s in blobject.scale:
        print(s)
        if s != 1.0: return False
    
    # rotation is allowed!! - so commenting that out
    #for r in blobject.rotation_euler:
    #    print(r)
    #    if r != 0.0: return False
    return True

def main_function_export_file(filename: str):
    lod_level = 0 # only one LOD level will get exported    

    main_col = bpy.context.scene.collection.children[0]
    CEM = b''


    # for mesh_col in main_col.children: ## i is used as iterator, so the code below makes sense :D
    #i = 0 # this is only temporary, because for now child models are not getting exported (otherwise the code below would be bullshit I know)

    try:
        mesh_col0 = main_col.children[0]
    except IndexError:
        ShowMessageBox(title="export error", message="no valid CEM structure found!", icon='ERROR')
        return False

    for i, mesh_col in enumerate(main_col.children):
        try:
            nVerts, nFaces, nMaterials, bbox_points = generate_header_info(mesh_col)
        except TypeError as e:
            ShowMessageBox(title="export error", message=str(e), icon='ERROR')
            return False
        
        highest_point, lowest_point, bbox_center = get_bounds(bbox_points)

        if i == 0:
            chm = len(main_col.children)-1
        else:
            chm = 0

        vertices = list()
        normals = list()
        texture_uvs = list()
        indices = [[ [], [] ]]
        indices_only = list()
        materials = list()
        mat_triangle_sel = 0
        frames = list()
        
        #if i == 0:
        num_tag_points = len(mesh_col.children[0].objects)
        #else:
        #    num_tag_points = 0

        ### header
        header = { 
        "cem_version":2,
        "faces":nFaces,
        "vertices":nVerts,
        "tag_points":num_tag_points,
        "materials":nMaterials,
        "frames":1, # no animations, so only one frame
        "child_models":chm,
        "lod_levels":1,
        "name_length":len(mesh_col.name.split(':')[1])+1,
        "name":mesh_col.name.split(':')[1].encode(),
        "center":bbox_center.to_tuple(),
        }

        ### materials
        material_template = [
        "material_name_length",     # uint32
        "material_name",            # string
        "texture_index",            # uint32
        "triangle_selections",      # list of tuples (offset, length) as uint32 for each LOD level
        "vertex_offset",            # uint32
        "vertex_count",             # uint32
        "texture_name_length",      # uint32
        "texture_name"              # string
        ]

        for curr_object in mesh_col.objects:
            matID, matName, matTextureindex = curr_object.name.split(':')
            matTextureindex = matTextureindex.split('.')[0]
            if matName == "BOUNDING BOX":
                continue

            materials.append(dict.fromkeys(material_template, 0))
            if curr_object.mode == 'EDIT':
                ShowMessageBox(title="export error", message="please disable edit mode!", icon='ERROR') # export will fail when in edit mode
                return False
            #bpy.ops.object.editmode_toggle() # this doesn't work for some reason, so user has to do it
            try:
                bpy.ops.object.select_all(action='DESELECT') # deselect all objects - creates error, when edit mode is enabled
            except RuntimeError:
                ShowMessageBox(title="export error", message="ERROR: do you have edit mode enabled??", icon='ERROR') # export will fail when in edit mode
                return False

            if not check_transforms(curr_object): # check if transforms are correctly applied - show warning if not, but export anyway
                ShowMessageBox(title="export warning", message="Pls check your rotation, scaling and location settings, it might look wrong in the game!", icon='INFO')        
            vt, nt, uvt, indt, num_vertices = get_vertex_data(curr_object) # get_vertex_data returns vertices, normals, uvs, indices, num_vertices

            materials[-1]["material_name_length"] = len(matName)+1
            materials[-1]["material_name"] = matName.encode()
            materials[-1]["texture_index"] = int(matTextureindex)

            materials[-1]["triangle_selections"] = [ (mat_triangle_sel, len(indt)) ]
            mat_triangle_sel += len(indt)

            materials[-1]["vertex_offset"] = len(vertices)
            materials[-1]["vertex_count"] = num_vertices

            matTextureName = curr_object.data.name.split('.')[0] # cutoff potential ".00x" from the name, which blender adds
            materials[-1]["texture_name_length"] = len(matTextureName)+1
            materials[-1]["texture_name"] = matTextureName.encode()

            vertices += vt
            normals += nt
            texture_uvs += uvt
            indices_only += indt
            transformation_matrix = curr_object.matrix_world

        ### indices
        indices[lod_level][0] = len(indices_only)
        indices[lod_level][1] = indices_only

        ### tag points
        tag_points = [ tp.name.split('.')[0].encode() for tp in mesh_col.children[0].objects ]


        ### frames
        frames_template = [ "radius", "vertices", "tag_points", "transform_matrix", "lower_bound", "upper_bound" ]

        for j in range(header["frames"]):
            frames.append(dict.fromkeys(frames_template, 0))
            print("header center:", header["center"])
            frames[j]["radius"] = max( [ (v-bbox_center).length for v in vertices ] )**2
            tmp = list()
            for v in range(nVerts):
                tmp.append(dict())
                tmp[v]["point"] = vertices[v].to_tuple()
                tmp[v]["normal"] = normals[v].to_tuple()
                if texture_uvs[v] == 0: texture_uvs[v] = Vector((0, 0)) # if vertex has to UV point value assigned, it will be 0 (replacing it with (0, 0) vector, because CEM forces a UV value)
                tmp[v]["texture"] = texture_uvs[v].to_tuple()
            frames[j]["vertices"] = tmp

            tmp_arr_tp = [ inverse_transform_vector(vector=tp.location, matrix=transformation_matrix) for tp in mesh_col.children[0].objects ]

            frames[j]["tag_points"] = tmp_arr_tp
            frames[j]["transform_matrix"] = [ list(vector) for vector in transformation_matrix.row ]
            frames[j]["lower_bound"] = lowest_point
            frames[j]["upper_bound"] = highest_point

        CEM += generate_cem(header, indices, materials, tag_points, frames)


    ### write all this shit to the file
    if not filename.endswith(".cem"):
        filename += ".cem"
    
    with open(filename, "wb") as f:
        f.write(CEM)

    return True
