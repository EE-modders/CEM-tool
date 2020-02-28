#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created 06.02.2020 12:52 CET

@author: zocker_160
"""

import os
import sys
from io import BytesIO

cem_magic = b'SSMF'
result = list()


def write_file(results: list()):
    header = [ 
		"Model Name", 
		"number of CEM files",
		"number child models",
		"CEM version major", 
		"CEM version minor",
		"number tag points",
		"number materials",
		"number frames",
		"number LOD levels"
		]
    with open("!output.csv", "w") as csvfile:
        csvfile.write(",".join(header)+"\n")

        for res in results:
            csvfile.write("%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (res[0], res[1], res[2], res[3], res[4], res[5], res[6], res[7], res[8]))

def get_num_CEM_parts(binary, start_pos=0, num_cem=1):
    cem_blob = BytesIO(binary)
    cem_blob.seek(start_pos)
    #cem_blob.read(8)
    name_length = int.from_bytes(cem_blob.read(4), byteorder='little', signed=False)
    material_name = cem_blob.read(name_length)[:-1]
    print(material_name)
    cem = cem_blob.read(-1)
    next_file = cem.find(cem_magic)

    if next_file == -1:
        return num_cem, material_name
    else:
        return get_num_CEM_parts(cem, start_pos=next_file+8, num_cem=num_cem+1)

def get_num_CEM_parts2(binary):
	CEM_parts = binary.split(cem_magic)[1:]
	return len(CEM_parts)

#os.chdir("models/")
for f in os.listdir("."):
    if f.endswith(".cem"):
        print(f)
        with open(f, "rb") as cemfile:
            if cemfile.read(4) != cem_magic:
                print("not a CEM file!")                
            else:
                version_maj = int.from_bytes(cemfile.read(2), byteorder='little', signed=False)
                version_min = int.from_bytes(cemfile.read(2), byteorder='little', signed=False)
                cemfile.read(8)
                num_tag_points = int.from_bytes(cemfile.read(4), byteorder='little', signed=False)                
                num_materials = int.from_bytes(cemfile.read(4), byteorder='little', signed=False)
                num_frames = int.from_bytes(cemfile.read(4), byteorder='little', signed=False)
                num_child_models = int.from_bytes(cemfile.read(4), byteorder='little', signed=False)
                num_lod_levels = int.from_bytes(cemfile.read(4), byteorder='little', signed=False)
                cemfile.seek(0)
                num_cem = get_num_CEM_parts2(cemfile.read(-1))
                result.append( [ f, num_cem, num_child_models, version_maj, version_min, num_tag_points, num_materials, num_frames, num_lod_levels ] )

                write_file(result)
