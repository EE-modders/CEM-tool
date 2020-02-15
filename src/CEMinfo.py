#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created 12.02.2020 13:06 CET

@author: zocker_160
@comment: this is a tool, which shows all info of a CEM file
"""

import sys
import struct

from io import BytesIO

"""
for more information on "struct" read this:
    https://docs.python.org/2/library/struct.html
so you might understand the code easier
"""


cemtool_version = 0.3

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
        print(next_cem)
        if next_cem == -1:
            CEM_parts.append(blob)
            return CEM_parts
        else:
            CEM_parts.append(blob[:next_cem+1])
        blob = blob[next_cem+1:]

def show_exit():
	input("press Enter to close..........")
	sys.exit()

def parse_file(cem_bytes: bytes):
    print("parsing..........\n")

    cemfile = BytesIO(cem_bytes)

    file_type = cemfile.read(4)

    if magic_number_cem == file_type:
        print("This is a (valid) CEM file\n")
    else:
        if magic_number_compressed == file_type:
            print("you need to decompress the file first!")
            show_exit()
        else:
            print("this is not a CEM file \n")
            show_exit()

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

        print(frames[i]["transform_matrix"])

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
    #print(frames[0]["tag_points"])
    #print(tag_points)
    #print(materials[0]["triangle_selections"])

    """
    print(int.from_bytes(file_type, byteorder="little", signed=False))
    print(magic_number.view(dtype=np.float32))
    print(test2.view())
    for x in indices:
        print("intwert: %d" % (x.item()) )


    #for i, header in header.items():
    #    objfile.write("%s: %s \n" %(i, header) )
    """
    print()

    return header, indices, materials, tag_points, frames

try:
	if sys.argv[1] == '--test':
		print("#### CEMinfo v0.3 made by zocker_160")
		print("####")
		print("WORKS!")
		sys.exit()
	
	with open(sys.argv[1], "rb") as f:
		CEM = f.read()
except IndexError:
	print("#### CEMinfo v0.3 made by zocker_160")
	print("####")
	print("ERROR: pls specify a file!")
	show_exit()

CEM_parts = get_CEM_parts(CEM)

header, indices, materials, tag_points, frames = parse_file(CEM_parts[0])

show_exit()
