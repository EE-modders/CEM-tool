## data loading

import struct
from io import BufferedReader, BufferedWriter

def readInt(f: BufferedReader) -> int:
    return int.from_bytes(f.read(4), byteorder="little", signed=False)
def readShort(f: BufferedReader) -> int:
    return int.from_bytes(f.read(2), byteorder="little", signed=False)
def readByte(f: BufferedReader) -> int:
    return int.from_bytes(f.read(1), byteorder="little", signed=False)
def readFloat(f: BufferedReader) -> float:
    return struct.unpack("<f", f.read(4))[0]

def readString(f: BufferedReader) -> str:
    length = readInt(f)
    return f.read(length).strip(b"\0").decode("iso8859-15")

def writeInt(f: BufferedWriter, value: int) -> int:
    return f.write(value.to_bytes(4, byteorder="little", signed=False))
def writeShort(f: BufferedWriter, value: int) -> int:
    return f.write(value.to_bytes(2, byteorder="little", signed=False))
def writeByte(f: BufferedWriter, value: int) -> int:
    return f.write(value.to_bytes(1, byteorder="little", signed=False))
def writeFloat(f: BufferedWriter, value: float) -> int:
    return f.write(struct.pack("<f", value))

def writeString(f: BufferedWriter, value: str) -> int:
    value = value.encode("iso8859-15")
    value = checkNullTerminator(value)

    writeInt(f, len(value))
    return f.write(value)


def checkNullTerminator(data: bytes) -> bytes:
    if not data.endswith(b"\0"):
        data += b"\0"
    return data


# Blender helpers

import bpy
from mathutils import Vector, Matrix

def newEmpty(name: str, size: float) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_size = size
    empty.empty_display_type = "PLAIN_AXES"

    return empty

def newEmptyCube(name: str) -> bpy.types.Object:
    cube = bpy.data.objects.new(name, None)
    cube.empty_display_type = "CUBE"
    return cube


def redraw():
    for area in bpy.context.screen.areas:
        if area.type in ['IMAGE_EDITOR', 'VIEW_3D']:
            area.tag_redraw()

def cleanup():
    for item in bpy.data.objects:
        bpy.data.objects.remove(item)

    for col in bpy.data.collections:
        bpy.data.collections.remove(col)
    
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)

    for mat in bpy.data.materials:
        if mat.users == 0:
            bpy.data.materials.remove(mat)
