#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created 28.02.2020 13:35 CET

@author: zocker_160
@comment: converts CEM files to OBJ
"""

import os
import sys
import struct

from io import BytesIO

"""
for more information on "struct" read this:
    https://docs.python.org/2/library/struct.html
so you might understand the code easier
"""


cemtool_version = 0.4

magic_number_compressed = b'PK01' # this is the magic number for all compressed files
magic_number_cem = b'SSMF' # this is the magic number for all CEM formats (decompressed)

header = dict()
indices = list()
materials = list()
tag_points = list()
frames = list()

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
        #print(next_cem)
        if next_cem == -1:
            CEM_parts.append(blob)
            return CEM_parts
        else:
            CEM_parts.append(blob[:next_cem+1])
        blob = blob[next_cem+1:]

"""
test1 = np.array([0x53, 0x53, 0x4D, 0x46], dtype=np.uint8)
test2 = np.uint32(np.frombuffer(b'SSMF', dtype=np.uint32))
magic_number_cem = bytes([0x53, 0x53, 0x4D, 0x46])
header = bytes.fromhex('53 53 4D 46').decode()
print(header)
"""

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
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
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

    cemfile.seek(0)
    return cemfile.read(-1)


def parse_file(cem_bytes: bytes):
    print("parsing..........\n")

    cemfile = BytesIO(cem_bytes)

    file_type = cemfile.read(4)

    if magic_number_cem == file_type:
        print("This is a valid CEM file\n")
    else:
        if magic_number_compressed == file_type:
            print("you need to decompress the file first!")
            sys.exit()
        else:
            print("this is not a CEM file \n")
            sys.exit()

    # lambdas in order to improve readability
    read_float_buff = lambda: struct.unpack("<f", cemfile.read(4))[0]
    read_uint32_buff = lambda: struct.unpack("<I", cemfile.read(4))[0]

    read_int_buff = lambda x: int.from_bytes(cemfile.read(x), byteorder="little", signed=False)

    header_template = [ "cem_version", "faces", "vertices", "tag_points", "materials", "frames", "child_models", "lod_levels", "name_length" ]

    values = struct.unpack("<IIIIIIIII", cemfile.read(36)) # 9 * 4 bytes = 36
    header = dict(zip(header_template, values))

    if header["cem_version"] != 2:
        input("ERROR: only CEM v2 files are supported!\n exiting..........")
        sys.exit()

    header["name"] = cemfile.read(header["name_length"])[:-1] # [:-1] removes the last byte which is a delimiter (0x00) in this case
    header["center"] = struct.unpack("<fff", cemfile.read(12))


    for _ in range(header["lod_levels"]):
        num_indices = read_uint32_buff()
        triangles = list()

        for _ in range(num_indices):
            triangles.append( struct.unpack("<III", cemfile.read(12)) )

        indices.append( (num_indices, triangles) )

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

    tmp = 0
    for _ in range(header["tag_points"]):
        l = read_uint32_buff()
        tmp += 4+l
        tag_points.append(cemfile.read(l)[:-1])

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

    return header, indices, materials, tag_points, frames

"""
saved values:
    header = dict()
    indices = list()
    materials = list()
    tag_points = list()
    frames = list()
"""

def write_obj(name: str, header: dict(), indices: list(), materials: list(), tag_points: list(), frames: list(), frame = 0):
    filename = "%s_%i.obj" % (name, frame)
    xVal = 0
    yVal = 1
    zVal = 2
    lod_lvl = 0

    with open(filename, "wt") as objfile:
        objfile.write("########## created with CEMconv v%s by zocker_160 \n" % cemtool_version)
        objfile.write("s off \n") # deactivate smooth shader
        n = header["name"].decode()
        if not n: n = "Scene Root"
        objfile.write("o %s \n" % n)

        for i in range(header["vertices"]):
            objfile.write("v %f %f %f \n" % (frames[frame]["vertices"][i]["point"][xVal], frames[frame]["vertices"][i]["point"][yVal], frames[frame]["vertices"][i]["point"][zVal]))
            #objfile.write("vn %f %f %f \n" % (vertex_rot2[0].item(), vertex_rot2[1].item(), vertex_rot2[2].item()))
            objfile.write("vt %f %f \n" % (frames[frame]["vertices"][i]["texture"][xVal], 1 - frames[frame]["vertices"][i]["texture"][yVal]))

        objfile.write("##########\n")

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

try:
    filepath = sys.argv[1]
except IndexError:
    input("ERROR: pls specify a CEM file\nPress Enter key to exit ..........")
    sys.exit()

filename = filepath.split(os.sep)[-1]

with open(filepath, "rb") as f:
    print(filename)
    CEM = f.read()

header, indices, materials, tag_points, frames = parse_file(CEM)

num_frames = header["frames"]

if num_frames > 1:
    ret = input("This CEM object has %i frames, do you want to export them all? (y/n) " % num_frames)
else:
    ret = "n"

if ret is not "y":
    write_obj(filename.split('.')[0], header, indices, materials, tag_points, frames, frame=0)
else:
    for frame in range(num_frames):
        write_obj(filename.split('.')[0], header, indices, materials, tag_points, frames, frame=frame)

print("DONE!")
input("Press Enter key to exit ..........")
