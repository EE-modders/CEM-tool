
import sys
from itertools import chain

import bpy
from mathutils import Vector, Matrix

from .messagebox import ShowMessageBox

from .CEM2 import (
    CEMv2,
    Header,
    Vector3d, Vector2d,
    Vertex,
    Face,
    Material,
    Matrix4x4,
    Frame
)


class ExportError(Exception):
    pass


def checkTransforms(object: bpy.types.Object):
    for scale in object.scale:
        if abs(scale - 1) > 0.001: # smallest diff for Blender
            return False

    return True


def calcBounds(bboxPoints: list):
    allX = [ x[0] for x in bboxPoints ]
    allY = [ x[1] for x in bboxPoints ]
    allZ = [ x[2] for x in bboxPoints ]

    maxV = Vector( (max(allX),max(allY),max(allZ)) )
    minV = Vector( (min(allX),min(allY),min(allZ)) )

    centerP = (maxV - minV) * 0.5 + minV

    return maxV, minV, centerP

def getTagPoints(collection: bpy.types.Collection):
    tagPointNames: list[str] = list()
    tagPointsVertex: list[Vector] = list()

    if collection.children[0].name.startswith("tag points"):
        for tp in collection.children[0].objects:
            tagPointNames.append(tp.name.split(".")[0])
            tagPointsVertex.append(tp.location)
    else:
        ShowMessageBox(
            title="export warning",
            message="tag point collection not found - tag points not exported"
        )

    return tagPointNames, tagPointsVertex

def getVertexData(childCollection: bpy.types.Collection):
    bboxPoints = list()
    vertices: list[Vertex] = list()
    materials: list[Material] = list()
    faces: list[Face] = list()
    transformationMatrix: Matrix

    # since Blender likes to shuffle the order around,
    # I need to search for the right object in order to keep the right order
    for i, _ in enumerate(childCollection.objects):
        for obj in childCollection.objects:
            if not obj.name.startswith(f"{i+1}:"):
                continue

            matID, matName, matTexIndex = obj.name.split(":")
            matTexIndex = int(matTexIndex.split(".")[0])

            if "BOUNDING BOX" in matName:
                continue
            else:
                print("parsing", obj.name, matName, matTexIndex)


            if obj.mode == "EDIT":
                ShowMessageBox(
                    title="export error",
                    message="please disable edit mode!",
                    icon='ERROR'
                )
                raise TypeError("please disable edit mode!")

            try:
                # deselect all objects - creates error, when edit mode is enabled
                bpy.ops.object.select_all(action='DESELECT')
            except RuntimeError:
                # export will fail when in edit mode
                ShowMessageBox(
                    title="export error",
                    message="ERROR: do you have edit mode enabled??",
                    icon='ERROR'
                )
                raise TypeError("ERROR: do you have edit mode enabled??")

            if not checkTransforms(obj):
                ShowMessageBox(
                    title="export warning",
                    message="please check your rotation, scaling and location settings, it might look wrong in the game!",
                    icon='INFO'
                )

            bboxPoints += obj.bound_box
            transformationMatrix = obj.matrix_world
            vertexOffset = len(vertices)

            materials.append( Material(
                name=matName,
                textureIndex=matTexIndex,
                textureName="",
                triangleSelections=[(len(faces), len(obj.data.polygons))],
                vertexOffset=vertexOffset,
                vertexCount=len(obj.data.vertices)
            ) )


            for vertex in obj.data.vertices:
                vertices.append( Vertex(
                    point=Vector3d(*vertex.co.to_tuple()),
                    normal=Vector3d(*vertex.normal.to_tuple()),
                    texture=Vector2d()
                ) )

            for polygon in obj.data.polygons:
                face = list()
                for li in polygon.loop_indices:
                    vIndex = obj.data.loops[li].vertex_index
                    uv = obj.data.uv_layers[0].data[li].uv

                    vertices[vIndex + vertexOffset].texture = Vector2d(uv[0], 1 - uv[1])
                    face.append(vIndex)

                if len(face) > 3:
                    ShowMessageBox(
                        title="export warning",
                        message="CEM only supports triangles, please triangulate!"
                    )
                    raise TypeError("CEM only supports triangles, please triangulate!")

                faces.append( Face(face[0], face[1], face[2]) )

    return bboxPoints, vertices, materials, faces, transformationMatrix


def cemExport(filename: str):
    print("saving", filename)

    try:
        cemParts = _cemExport()

        with open(filename, "wb") as f:
            for cem in cemParts:
                cem.serialize(f)
    except ExportError as e:
        ShowMessageBox(title="export error", icon="ERROR", message=str(e))
        print("Export Error:", e)


def _cemExport() -> list[CEMv2]:
    print("generating CEM")

    currScene = bpy.context.scene
    mainCollection = bpy.context.scene.collection.children[0]

    if not mainCollection.name.startswith("M:"):
        raise ExportError("missing main collection")

    cemParts: list[CEMv2] = list()

    for nc, childCollection in enumerate(mainCollection.children):
        if not childCollection.name.startswith(f"{nc+1}:"):
            raise ExportError("no valid CEM structure found")

        print("###", childCollection.name)

        header = Header()
        header.name = childCollection.name.split(":")[-1]
        header.lodLevels = 1


        bboxPoints = list()
        vertices: list[Vertex] = list()
        materials: list[Material] = list()
        faces: list[Face] = list()
        transformationMatrix = Matrix()
        tagPointNames: list[str] = list()


        frames: list[Frame] = list()
        numFrames = currScene.frame_end - currScene.frame_start + 1

        for i, frame in enumerate(range(numFrames)):
            currScene.frame_current = frame

            tagPointNames, tagPointVertex = getTagPoints(childCollection)
            bboxPoints, vertices, materials, faces, transformationMatrix = getVertexData(childCollection)
            maxV, minV, centerP = calcBounds(bboxPoints)

            if i == 0:
                header.vertices = len(vertices)
                header.materials = len(materials)
                header.faces = len(faces)
                header.tagPoints = len(tagPointNames)
                header.center = Vector3d(centerP.x, centerP.y, centerP.z)

            transformationMatrixInv = transformationMatrix.inverted()
            tagPointVertex = [transformationMatrixInv @ v for v in tagPointVertex]
            transMat = Matrix4x4(*chain.from_iterable([row.to_tuple() for row in transformationMatrix.row]))

            frames.append(Frame(
                radius=(maxV - minV).length_squared,
                vertices=vertices,
                tagPoints=[Vector3d(*x.to_tuple()) for x in tagPointVertex],
                transformationMatrix=transMat,
                lowerBound=Vector3d(*minV.to_tuple()),
                upperBound=Vector3d(*maxV.to_tuple())
            ))


        header.frames = len(frames)

        cemParts.append(CEMv2(
            header=header,
            faces=[faces],
            materials=materials,
            frames=frames,
            tagPoints=tagPointNames
        ))
        # not too great, but ok
        cemParts[0].header.childModels = nc

    return cemParts
