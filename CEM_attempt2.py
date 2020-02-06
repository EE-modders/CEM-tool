#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 18:25:03 2019

@author: zocker_160
@comment: this is attempt: 2
"""

import numpy as np

cemtool_version = 0.1

magic_number_compressed = b'PK01' # this is the magic number for all compressed files
magic_number_cem = b'SSMF' # this is the magic number for all CEM formats (decompressed)

header = {
    "major_version":np.uint16(0), 
    "minor_version":np.uint16(0), 
    "faces":np.uint32(0), 
    "vertices":np.uint32(0), 
    "tag_points":np.uint32(0), 
    "materials":np.uint32(0), 
    "frames":np.uint32(0), 
    "child_models":np.uint32(0), 
    "lod_levels":np.uint32(0), 
    "unknown":np.uint32(0), 
    "model_name":"",
    "center":[np.float32(0), np.float32(0), np.float32(0)]
}
center = [0] * 3
indices = []
materials = {}
material_player = {}
tag_point_names = []
frames = []

### some math crap

def rot_matrix_x(matrix, degree):
    alpha = np.radians(degree)

    cos, sin = np.cos(alpha), np.sin(alpha)
    rotm = np.matrix([ [1,0,0],[0,cos,-sin],[0,sin,cos] ])

    return np.matmul(rotm, matrix)


"""
test1 = np.array([0x53, 0x53, 0x4D, 0x46], dtype=np.uint8)
test2 = np.uint32(np.frombuffer(b'SSMF', dtype=np.uint32))
magic_number_cem = bytes([0x53, 0x53, 0x4D, 0x46])
header = bytes.fromhex('53 53 4D 46').decode()
print(header)
"""

def parse_file(filename = 'flat model_decompressed.cem'):
    print("parsing " + filename + "....\n")

    with open(filename, 'rb') as cemfile:
        file_type = cemfile.read(4)

        if magic_number_cem == file_type:
            print("This is a CEM file")
        else:
            if magic_number_compressed == file_type:
                print("you need to decompress the file first!")
                exit()
            else:
                print("this is not a CEM file")
                exit()

        # lambdas in order to improve readability
        read_float_buff = lambda x: np.float32(np.frombuffer(cemfile.read(x), dtype=np.float32))
        read_int_buff = lambda x: int.from_bytes(cemfile.read(x), byteorder="little", signed=False)


        ## THIS IS FUCKING HORRIBLE PROGRAMMING, I KNOW THAT and I will fix it ;)

        print()
        print("file type: %s" % file_type.decode())

        header["major_version"] = np.uint16(np.frombuffer(cemfile.read(2), dtype=np.uint16))
        print("major version: %d" % header["major_version"].item())

        header["minor_version"] = np.uint16(np.frombuffer(cemfile.read(2), dtype=np.uint16))
        print("minor version: %d" % header["minor_version"].item())


        header["faces"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("faces: %d" % header["faces"].item())

        header["vertices"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("vertices: %d" % header["vertices"].item())

        header["tag_points"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("tag points: %d" % header["tag_points"].item())

        header["materials"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("materials: %d" % header["materials"].item())

        header["frames"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("frames: %d" % header["frames"].item())

        header["child_models"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("child_models: %d" % header["child_models"].item())

        header["lod_levels"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("LOD levels: %d" % header["lod_levels"].item())

        header["unknown"] = np.uint32(np.frombuffer(cemfile.read(4), dtype=np.uint32))
        print("unknown: %d" % header["unknown"].item())

        while True:
            tmp = cemfile.read(1)
            if (tmp == b'\x00'):
                break
            header["model_name"] += tmp.decode()
        
        print("name length: %dbytes" % (len(header["model_name"])+1))

        # header["model_name"] = cemfile.read(10)
        print("generic name: %s" % header["model_name"])

        # cemfile.read(1) # delimiter (?)
        
        center[0] = read_float_buff(4)
        center[1] = read_float_buff(4)
        center[2] = read_float_buff(4)

        for i, center_point in enumerate(center):
            print("center point %d: %f" % (i, center_point) )
        print()

        #indices = [[0]] * header["lod_levels"].item()
        #indices = [ [0] * 6 for i in range(10) ]        
        print(indices)

        """
        for x in range(2):
            for y in range(23):
                print(int.from_bytes(cemfile.read(4), byteorder="little", signed=False), end='')
            print()        
        """
        index_length = header["lod_levels"].item() * 4

        for x in range(header["lod_levels"].item()):
            print("LOD level %s" % (x+1))
            triangle_count = read_int_buff(4)
            indices.append(triangle_count)
            indices.append([])
            print("triangle count: %d" % triangle_count, end='|')

            for _ in range(triangle_count*3):
                tmp = read_int_buff(4)
                indices[-1].append(tmp)
                print(tmp, end=' ')
                index_length += 4
            
            print()
        #print(indices)
        print("used bytes: %d for all indices" % index_length)
        print()
        print("length up until here: %d" % (index_length + len(header["model_name"])+1 + 52) )

        # TODO: read until the next byte is 00
        materials["name"] = cemfile.read(1) # maybe this is a 9 byte long string (or just one byte as \x01 ??? ), but not really sure, what this value actually is
        # delimiter ??
        materials["texture_index"] = read_int_buff(4) # this is 0 most of the time, true meaning of this value is unknown
        
        materials["triangle_selection"] = []
        for _ in range(header["lod_levels"].item()):
            materials["triangle_selection"].append( [ 
                read_int_buff(4), 
                read_int_buff(4) 
            ] )

        materials["vertex_offset_1"] = read_int_buff(4) # ???
        materials["vertex_offset_2"] = read_int_buff(4) # ???
        materials["vertex_count"] = read_int_buff(4)
        materials["unknown_1"] = read_int_buff(4)

        materials["texture_name"] = ""

        # TODO: replace "True/False" with a real condition
        if False:
            cemfile.read(4) # texture name (?)
            cemfile.read(1) # delimiter (?)
        else:
            while True:
                tmp = cemfile.read(1)
                if (tmp == b'\x00'):
                    break
                materials["texture_name"] += tmp.decode()
        materials["unknown_2"] = read_int_buff(4)

        # TODO: insert tag_point_names here, if available

        print("material 1: %s" % materials)

        # TODO: das hier durch etwas Generisches ersetzen, hier viel doppelter Code!

        if (header["materials"].item() > 1):
            material_player["name"] = ""
            while True:
                tmp = cemfile.read(1)
                if (tmp == b'\x00'):
                    break
                material_player["name"] += tmp.decode()

            material_player["texture_index"] = read_int_buff(4) # this is 0 most of the time, true meaning of this value is unknown
            
            material_player["triangle_selection"] = []
            for _ in range(header["lod_levels"].item()):
                material_player["triangle_selection"].append( [ 
                    read_int_buff(4), 
                    read_int_buff(4) 
                ] )

            material_player["vertex_offset_1"] = read_int_buff(4) # ???
            material_player["vertex_offset_2"] = read_int_buff(4) # ???
            material_player["vertex_count"] = read_int_buff(4)
            #material_player["unknown_3"] = read_int_buff(4)

            material_player["texture_name"] = ""

            # TODO: replace "True/False" with a real condition
            if False:
                cemfile.read(4) # texture name (?)
                cemfile.read(1) # delimiter (?)
            else:
                while True:
                    tmp = cemfile.read(1)
                    if (tmp == b'\x00'):
                        break
                    material_player["texture_name"] += tmp.decode()

            print("material 2: %s" % material_player)
        print()

        
        #while True:
        #    print( round( read_float_buff(4).item(), 4) )


        for i in range(header["frames"].item()):            
            print("frame {} of {} frame(s):".format(i+1, header["frames"].item()) )
                        
            frames.append( { "vertex_array": { "point": [], "normal": [], "texture": [] } } )
            frames[i]["radius_squared"] = read_float_buff(4).item()

            for _ in range(header["vertices"].item()):
                frames[i]["vertex_array"]["point"].append( [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()] )
                frames[i]["vertex_array"]["normal"].append( [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()] )
                frames[i]["vertex_array"]["texture"].append( [read_float_buff(4).item(), read_float_buff(4).item()] )
            
            frames[i]["tag_points"] = []
            for _ in range(header["tag_points"].item()):
                frames[i]["tag_points"].append( read_float_buff(4).item() ) # TODO: positions of each tag point are point3!!! -> 3x4 bytes!
            
            frames[i]["transform_matrix"] = [
                    [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()],
                    [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()],
                    [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()],
                    [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()]
                ]
            frames[i]["lower_bound_3"] = [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()]
            frames[i]["upper_bound_3"] = [read_float_buff(4).item(), read_float_buff(4).item(), read_float_buff(4).item()]            
        

        print(frames, "\n", indices)

        print(cemfile.read(-1))

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

# write as obj file for easier debugging

def write_file(name: str, header: dict, frames: list):
    filename = name + ".obj"

    with open(filename, 'wt') as objfile:
        objfile.write("# created with PyCemtool v%s by zocker_160 \n" % cemtool_version)

        for i in range(header["vertices"].item()):
            # save matrix so they can get rotated by -90 around x axis
            vertex_tmp = np.matrix( [ [frames[0]["vertex_array"]["point"][i][0]], [frames[0]["vertex_array"]["point"][i][1]], [frames[0]["vertex_array"]["point"][i][2]] ] )
            vertex_rot = rot_matrix_x(vertex_tmp, -90)

            objfile.write("v %f %f %f \n" %(vertex_rot[0].item(), vertex_rot[1].item(), vertex_rot[2].item()) )
            objfile.write("vn %f %f %f \n" %(frames[0]["vertex_array"]["normal"][i][0], frames[0]["vertex_array"]["normal"][i][1], frames[0]["vertex_array"]["normal"][i][2]) )
            objfile.write("vt %f %f \n" %(frames[0]["vertex_array"]["texture"][i][0], 1 - frames[0]["vertex_array"]["texture"][i][1] ))
        objfile.write("### \n")

        t = indices[1][0] + 1
        m = indices[1][1] + 1
        p = indices[1][2] + 1
        objfile.write("f %i/%i/%i %i/%i/%i %i/%i/%i \n" %(t, t, t, m, m, m, p, p, p) )
        t = indices[1][3] + 1
        m = indices[1][4] + 1
        p = indices[1][5] + 1
        objfile.write("f %i/%i/%i %i/%i/%i %i/%i/%i \n" %(t, t, t, m, m, m, p, p, p) )




#parse_file("test_2.cem")
#parse_file("triangle2.cem")
#parse_file("triangle3.cem")

#parse_file("flat model_decompressed.cem")

#parse_file("models/air_me262_10.cem")
#parse_file("models/air_me110_10_decompressed.cem")
#parse_file("models/nav_bismarck_10_decompressed.cem")
#parse_file("models/nav_battleship_12.cem")
#parse_file("models/bld_siege_10.cem")
parse_file("models/air_a10_10.cem")
#parse_file("models/men_mortar_10.cem")

# write_file("flat_1", header, frames)
