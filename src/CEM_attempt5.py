#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created 09.05.2020 12:01 CET

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


magic_number_compressed = b'PK01' # this is the magic number for all compressed files
magic_number_cem = b'SSMF' # this is the magic number for all CEM formats (decompressed)

#header = dict()
#indices = list()
#materials = list()
#tag_points = list()
#frames = list()

def parse_file_1(cem_bytes: bytes):
    print("parsing..........\n")

    read_int_buff = lambda: struct.unpack("<I", cemfile.read(4))[0]
    read_float_buff = lambda: struct.unpack("<f", cemfile.read(4))[0]

    read_mult_int_buff = lambda x: struct.unpack("<%dI" % x, cemfile.read(x*4))

    cemfile = BytesIO(cem_bytes)

    file_type = cemfile.read(4)
    print(file_type)

    header_template = [ 
        "cem_version_major",
        "cem_version_minor",
        "unknown_1",
        "unknown_2",
        "vertices_uni",
        "faces",
        "unknown_3",
        "uvs_uni",
        "tag_points",
        "child_models",
        "name_length"
    ]

    values = struct.unpack("<HH9I", cemfile.read(40))
    header = dict(zip(header_template, values))

    header["name"] = cemfile.read(header["name_length"])[:-1] # [:-1] removes the last byte which is a delimiter (0x00) in this case
    header["center"] = struct.unpack("<fff", cemfile.read(12))

    print(header)
    print(cemfile.read(1)) # 0x00 delimiter (?)
    
    indices = read_mult_int_buff(header["vertices_uni"])
    print(indices)
    print("%d entrys - %d * 4 = %d bytes" % (header["vertices_uni"], header["vertices_uni"], header["vertices_uni"]*4))

    maxim = 0
    for i in range(header["faces"]*3): # number of faces * 3
        unknown_line = struct.unpack("<I7fII", cemfile.read(40))
        maxim = max(maxim, unknown_line[0])
        print(i+1, unknown_line)
    print("%d values and %d max value" % (header["faces"]*3, maxim))

    pl_cl_length = read_int_buff()
    name_2 = cemfile.read(pl_cl_length)
    print(name_2)

    #indices_2 = struct.unpack("<354I", cemfile.read(1416))
    #print(indices_2)

    leng = read_int_buff()
    print(leng, read_mult_int_buff(leng))
    leng = read_int_buff()
    print(leng, read_mult_int_buff(leng))

    #print(read_int_buff(), struct.unpack("<96I", cemfile.read(96*4)))
    #print(read_int_buff(), struct.unpack("<256I", cemfile.read(256*4)))

    print("unknown", cemfile.read(1))

    texture_name_len = read_int_buff()
    texture_name = cemfile.read(texture_name_len)
    print(texture_name)

    indices_3 = struct.unpack("<399I", cemfile.read(1596))
    print(indices_3)
    print("399 * 4 bytes")

    exit()

    for i in range(14):
        tmp_len = read_int_buff()        
        print(cemfile.read(tmp_len))

    vertices_1 = struct.unpack("<466f", cemfile.read(1864))
    print(vertices_1)

    what_the_fuck = struct.unpack("<398B", cemfile.read(398))
    print(what_the_fuck)

    what_the_fuck_2 = struct.unpack("<39f", cemfile.read(156))
    print(what_the_fuck_2)

    some_fucking_placeholder = struct.unpack("<3f", cemfile.read(12))
    print(some_fucking_placeholder)

    rot_matrix = [
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()]
    ]
    print(rot_matrix)

    lower_bound = struct.unpack("<3f", cemfile.read(12))
    print(lower_bound)

    upper_bound = struct.unpack("<3f", cemfile.read(12))
    print(upper_bound)


def parse_file_2(cem_bytes: bytes):
    print("parsing..........\n")

    read_int_buff = lambda: struct.unpack("<I", cemfile.read(4))[0]
    read_float_buff = lambda: struct.unpack("<f", cemfile.read(4))[0]

    cemfile = BytesIO(cem_bytes)

    file_type = cemfile.read(4)
    print(file_type)

    header = struct.unpack("<HH9I", cemfile.read(40)) # fixed magic number
    print(header)

    name = cemfile.read(11) # length value are the 4 bytes before this
    print(name)

    center = struct.unpack("<fff", cemfile.read(12)) # fixed length of 3 * 4 bytes
    print(center)
    cemfile.read(1) # 0x00 delimiter (?)
    indices = struct.unpack("<4I", cemfile.read(16)) # unknown value from header
    print(indices)
    print("4 entrys - 16 bytes")

    maxim = 0
    for i in range(6): # "number of UVs" from header - well not really sadly
        unknown_line = struct.unpack("<I7fII", cemfile.read(40))
        maxim = max(maxim, unknown_line[0])
        print(i+1, unknown_line)
    print("%d values and %d max value" % (6, maxim))

    #pl_cl_length = read_int_buff()
    #name_2 = cemfile.read(pl_cl_length)
    #print(name_2)
    
    indices_2 = struct.unpack("<5I", cemfile.read(20))
    print(indices_2)

    print("unknown", cemfile.read(1))
    
    #texture_name_len = read_int_buff()
    #texture_name = cemfile.read(texture_name_len)
    #print(texture_name)

    indices_3 = struct.unpack("<10I", cemfile.read(40))
    print(indices_3)    

    # tag points
    #for i in range(14):
    #    tmp_len = read_int_buff()        
    #    print(cemfile.read(tmp_len))

    radius = read_float_buff()
    print(radius)

    vertices = struct.unpack("<12f", cemfile.read(48))
    print(vertices)

    #what_the_fuck_2 = struct.unpack("<398B", cemfile.read(398))
    #print(what_the_fuck_2)

    some_fucking_placeholder = struct.unpack("<3f", cemfile.read(12))
    print(some_fucking_placeholder)

    rot_matrix = [
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()],
        [read_float_buff(), read_float_buff(), read_float_buff(), read_float_buff()]
    ]
    print(rot_matrix)

    lower_bound = struct.unpack("<3f", cemfile.read(12))
    print(lower_bound)

    upper_bound = struct.unpack("<3f", cemfile.read(12))
    print(upper_bound)


with open("fx_debrisflat.cem", "rb") as f:
    CEM = f.read()

#with open("air_balloon_09.cem", "rb") as f:
#    CEM = f.read()

parse_file_1(CEM)
