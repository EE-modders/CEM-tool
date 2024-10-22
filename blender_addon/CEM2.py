"""
Python wrapper class for Empire Earth CEM v2.
Created for the Blender CEM Plugin.

@date 20.10.2024 00:27
@author zocker_160
"""

from dataclasses import dataclass

from .utils import *

CEM_MAGIC_COMPRESSED = b"PK01"
CEM_MAGIC = b"SSMF"


@dataclass
class Vector3d:
    x: float
    y: float
    z: float

    @staticmethod
    def parse(f: BufferedReader):
        return Vector3d(*struct.unpack("<fff", f.read(12)))

    def toTuple(self) -> tuple:
        return (self.x, self.y, self.z)

@dataclass
class Vector2d:
    u: float
    v: float

    @staticmethod
    def parse(f: BufferedReader):
        return Vector2d(*struct.unpack("<ff", f.read(8)))

    def toTuple(self) -> tuple:
        return (self.u, self.v)

@dataclass
class Matrix4x4:
    m11: float
    m12: float
    m13: float
    m14: float

    m21: float
    m22: float
    m23: float
    m24: float

    m31: float
    m32: float
    m33: float
    m34: float

    m41: float
    m42: float
    m43: float
    m44: float

    @staticmethod
    def parse(f: BufferedReader):
        t = struct.unpack("<16f", f.read(16 * 4))
        return Matrix4x4(
            t[0], t[1], t[2], t[3],
            t[4], t[5], t[6], t[7],
            t[8], t[9], t[10], t[11],
            t[12], t[13], t[14], t[15],
        )

    def toTuple(self) -> tuple:
        return (
            (self.m11, self.m12, self.m13, self.m14),
            (self.m21, self.m22, self.m23, self.m24),
            (self.m31, self.m32, self.m33, self.m34),
            (self.m41, self.m42, self.m43, self.m44),
        )

    def __str__(self) -> str:
        return f"""
        [{self.m11}, {self.m12}, {self.m13}, {self.m14}]
        [{self.m21}, {self.m22}, {self.m23}, {self.m24}]
        [{self.m31}, {self.m32}, {self.m33}, {self.m34}]
        [{self.m41}, {self.m42}, {self.m43}, {self.m44}]
        """

@dataclass
class Vertex:
    point: Vector3d
    normal: Vector3d
    texture: Vector2d

    @staticmethod
    def parse(f: BufferedReader):
        return Vertex(
            point=Vector3d.parse(f),
            normal=Vector3d.parse(f),
            texture=Vector2d.parse(f)
        )

@dataclass
class Face:
    a: int
    b: int
    c: int

    def toTuple(self) -> tuple:
        return (self.a, self.b, self.c)

@dataclass
class Header:
    version: float

    faces: int
    vertices: int
    tagPoints: int
    materials: int
    frames: int

    childModels: int
    lodLevels: int

    name: str
    center: Vector3d

    @staticmethod
    def parse(f: BufferedReader):
        vMaj = readShort(f)
        vMin = readShort(f)

        return Header(
            version=vMaj + (vMin / 10),
            faces=readInt(f),
            vertices=readInt(f),
            tagPoints=readInt(f),
            materials=readInt(f),
            frames=readInt(f),
            childModels=readInt(f),
            lodLevels=readInt(f),
            name=readString(f),
            center=Vector3d.parse(f)
        )

@dataclass
class Material:
    name: str
    textureIndex: int

    triangleSelections: list[tuple[int]]

    vertexOffset: int
    vertexCount: int

    textureName: int

    @staticmethod
    def parse(f: BufferedReader, lodLevels: int):
        return Material(
            name=readString(f),
            textureIndex=readInt(f),
            triangleSelections=[struct.unpack("<II", f.read(8)) for _ in range(lodLevels)], # FIXME
            vertexOffset=readInt(f),
            vertexCount=readInt(f),
            textureName=readString(f)
        )

@dataclass
class Frame:
    radius: float
    
    vertices: list[Vertex]
    tagPoints: list[Vector3d]

    transformationMatrix: Matrix4x4

    lowerBound: Vector3d
    upperBound: Vector3d

    @staticmethod
    def parse(f: BufferedReader, header: Header):
        return Frame(
            radius=readFloat(f),
            vertices=[Vertex.parse(f) for _ in range(header.vertices)],
            tagPoints=[Vector3d.parse(f) for _ in range(header.tagPoints)],
            transformationMatrix=Matrix4x4.parse(f),
            lowerBound=Vector3d.parse(f),
            upperBound=Vector3d.parse(f)
        )


@dataclass
class CEMv2:
    
    header: Header
    
    faces: list[list[Face]]
    materials: list[Material]
    frames: list[Frame]

    tagPoints: list[str]

    @staticmethod
    def parse(f: BufferedReader):
        # header
        assert f.read(4) == CEM_MAGIC, "invalid CEM magic, is the file compressed?"
        
        header = Header.parse(f)
        assert header.version == 2, "only CEM v2 is supported"    

        print(header)

        # faces
        faces = list()
        for i in range(header.lodLevels):
            fc = list()
            numFaces = readInt(f)

            for _ in range(numFaces):
                fc.append(Face(*struct.unpack("<III", f.read(12))))

            faces.append(fc)

            #print(f"LOD {i+1} | nF: {numFaces}")

        # materials
        materials = list()
        for _ in range(header.materials):
            mat = Material.parse(f, header.lodLevels)
            materials.append(mat)

            print(mat)

        # tag points
        tagPoints = list()
        for _ in range(header.tagPoints):
            tagPoints.append(readString(f))

        print(tagPoints)

        # frames
        frames = list()
        for _ in range(header.frames):
            frame = Frame.parse(f, header)
            frames.append(frame)

            print(frame.radius)
            print(frame.lowerBound, frame.upperBound)
            print(frame.transformationMatrix)

        print("position", f.tell())

        assert len(materials) == header.materials
        assert len(frames) == header.frames
        assert len(tagPoints) == header.tagPoints

        return CEMv2(
            header=header,
            faces=faces,
            materials=materials,
            frames=frames,
            tagPoints=tagPoints
        )


## testing only

TESTFILE = "/home/bene/Programmierkram/GitHub/EE-modders/CEM-tool/samples/air_me262_10.cem"

if __name__ == "__main__":
    
    with open(TESTFILE, "rb") as f:
        CEMv2.parse(f)
