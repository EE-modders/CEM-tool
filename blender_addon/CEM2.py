"""
Python wrapper class for Empire Earth CEM v2.
Created for the Blender CEM Plugin.

@date 20.10.2024 00:27
@author zocker_160
"""

from dataclasses import dataclass, field

from .utils import *

CEM_MAGIC_COMPRESSED = b"PK01"
CEM_MAGIC = b"SSMF"


@dataclass
class Vector3d:
    x: float = 0
    y: float = 0
    z: float = 0

    @staticmethod
    def parse(f: BufferedReader):
        return Vector3d(*struct.unpack("<fff", f.read(12)))

    def toTuple(self) -> tuple:
        return (self.x, self.y, self.z)

    def serialize(self, f: BufferedWriter):
        f.write(struct.pack("<fff", *self.toTuple()))

@dataclass
class Vector2d:
    u: float = 0
    v: float = 0

    @staticmethod
    def parse(f: BufferedReader):
        return Vector2d(*struct.unpack("<ff", f.read(8)))

    def toTuple(self) -> tuple:
        return (self.u, self.v)

    def serialize(self, f: BufferedWriter):
        f.write(struct.pack("<ff", *self.toTuple()))

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
        return Matrix4x4(*t)

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

    def serialize(self, f: BufferedWriter):
        for row in self.toTuple():
            f.write(struct.pack("<4f", *row))

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

    def serialize(self, f: BufferedWriter):
        self.point.serialize(f)
        self.normal.serialize(f)
        self.texture.serialize(f)

@dataclass
class Face:
    a: int
    b: int
    c: int

    @staticmethod
    def parse(f: BufferedReader):
        t = struct.unpack("<III", f.read(4 * 3))
        return Face(*t)

    def toTuple(self) -> tuple:
        return (self.a, self.b, self.c)

    def serialize(self, f: BufferedWriter):
        f.write(struct.pack("<III", *self.toTuple()))

@dataclass
class Header:
    version: float = 2

    faces: int = 0
    vertices: int = 0
    tagPoints: int = 0
    materials: int = 0
    frames: int = 0

    childModels: int = 0
    lodLevels: int = 0

    name: str = "Scene Root"
    center: Vector3d = field(default_factory=Vector3d)

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

    def serialize(self, f: BufferedWriter):
        vMaj = int(self.version)
        vMin = int((self.version - vMaj) * 10)

        writeShort(f, vMaj)
        writeShort(f, vMin)
        writeInt(f, self.faces)
        writeInt(f, self.vertices)
        writeInt(f, self.tagPoints)
        writeInt(f, self.materials)
        writeInt(f, self.frames)
        writeInt(f, self.childModels)
        writeInt(f, self.lodLevels)
        writeString(f, self.name)
        self.center.serialize(f)

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

    def serialize(self, f: BufferedWriter):
        writeString(f, self.name)
        writeInt(f, self.textureIndex)
        for selection in self.triangleSelections:
            f.write(struct.pack("<II", *selection))
        writeInt(f, self.vertexOffset)
        writeInt(f, self.vertexCount)
        writeString(f, self.textureName)

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

    def serialize(self, f: BufferedWriter):
        writeFloat(f, self.radius)
        for vertex in self.vertices:
            vertex.serialize(f)
        for tagPoint in self.tagPoints:
            tagPoint.serialize(f)
        self.transformationMatrix.serialize(f)
        self.lowerBound.serialize(f)
        self.upperBound.serialize(f)

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
                fc.append(Face.parse(f))

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

    def serialize(self, f: BufferedWriter):
        f.write(CEM_MAGIC)
        self.header.serialize(f)

        for i in range(self.header.lodLevels):
            writeInt(f, len(self.faces[i]))
            for face in self.faces[i]:
                face.serialize(f)

        for i in range(self.header.materials):
            self.materials[i].serialize(f)

        for i in range(self.header.tagPoints):
            writeString(f, self.tagPoints[i])

        for i in range(self.header.frames):
            self.frames[i].serialize(f)


## testing only

TESTFILE = "/home/bene/Programmierkram/GitHub/EE-modders/CEM-tool/samples/air_me262_10.cem"

if __name__ == "__main__":
    
    with open(TESTFILE, "rb") as f:
        CEMv2.parse(f)
