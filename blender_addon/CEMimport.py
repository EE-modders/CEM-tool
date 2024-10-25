import os

import bpy
from mathutils import Vector, Matrix

from . import utils

from .CEM2 import CEMv2

EMPTY_SIZE = 0.04

def cemImport(filename: str, lodLevel: int):
    print("loading", filename)

    with open(filename, "rb") as f:
        cem = CEMv2.parse(f)

        currScene = bpy.context.scene
        currScene.frame_current = 0
        currScene.frame_start = 0
        currScene.frame_end = max(0, cem.header.frames - 1)

        basename = os.path.basename(filename)

        mainCollection = bpy.data.collections.new(f"M:{basename}.LOD {lodLevel}")
        currScene.collection.children.link(mainCollection)

        childIndex = 1
        childCollection = bpy.data.collections.new(f"{childIndex}:{cem.header.name}")
        mainCollection.children.link(childCollection)

        _cemImport(cem, lodLevel, childCollection)

        for i in range(cem.header.childModels):
            childIndex = i + 2
            cem = CEMv2.parse(f)

            childCollection = bpy.data.collections.new(f"{childIndex}:{cem.header.name}")
            mainCollection.children.link(childCollection)

            _cemImport(cem, lodLevel, childCollection)


def _cemImport(cem: CEMv2, lodLevel: int, childCollection: bpy.types.Collection):

    bbox = utils.newEmptyCube("0:BOUNDING BOX:0")
    childCollection.objects.link(bbox)

    for i, material in enumerate(cem.materials):

        matName = material.name if material.name else "none"
        objName = f"{i+1}:{matName}:{material.textureIndex}"

        selectionOffset, selectionLen = material.triangleSelections[lodLevel]
        faces = [x.toTuple() for x in cem.faces[lodLevel][selectionOffset : selectionOffset + selectionLen]]

        matMesh = bpy.data.meshes.new(material.textureName)
        matMesh.uv_layers.new()

        matObj = bpy.data.objects.new(objName, matMesh)
        childCollection.objects.link(matObj)

        for n, frame in enumerate(cem.frames):

            transMatrix = Matrix(frame.transformationMatrix.toTuple())
            bboxMin = Vector(frame.lowerBound.toTuple())
            bboxMax = Vector(frame.upperBound.toTuple())

            bbox.scale = (bboxMax - bboxMin) / 2
            bbox.location = transMatrix.translation + (bboxMin + bboxMax) / 2
            bbox.rotation_euler = transMatrix.to_euler()

            vStart = material.vertexOffset
            vEnd = vStart + material.vertexCount
            points = [Vector(x.point.toTuple()) for x in frame.vertices[vStart:vEnd]]

            if n == 0:
                matMesh.from_pydata(points, list(), faces)
                matMesh.update()
                #matMesh.validate(verbose=True)

                uvs = [x.texture for x in frame.vertices[vStart:vEnd]]
                # UV vector flip
                uvs = [Vector((x.u, 1 - x.v)) for x in uvs]

                for p, polygon in enumerate(matMesh.polygons):
                    for i, index in enumerate(polygon.loop_indices):
                        matMesh.uv_layers[0].uv[index].vector = uvs[faces[p][i]]

                if material.name == "player color":
                    plColorMat = bpy.data.materials.get(material.name, bpy.data.materials.new(material.name))
                    plColorMat.diffuse_color = (0.1, 0.1, 1, 1)
                    plColorMat.roughness = 1
                    plColorMat.metallic = 0

                    matObj.data.materials.append(plColorMat)

            else:
                for i, vertex in enumerate(matObj.data.vertices):
                    vertex.co = points[i]

            matObj.matrix_world = transMatrix

            if cem.header.frames > 1:
                matObj.keyframe_insert("location", frame=n)
                matObj.keyframe_insert("rotation_euler", frame=n)
                matObj.keyframe_insert("scale", frame=n)

                bbox.keyframe_insert("location", frame=n)
                bbox.keyframe_insert("rotation_euler", frame=n)
                bbox.keyframe_insert("scale", frame=n)

                for vertex in matObj.data.vertices:
                    vertex.keyframe_insert("co", frame=n)

    # tag points
    pointCollection = bpy.data.collections.new("tag points")
    childCollection.children.link(pointCollection)

    for i in range(cem.header.tagPoints):

        tagPoint = utils.newEmpty(cem.tagPoints[i], EMPTY_SIZE)
        pointCollection.objects.link(tagPoint)

        for n, frame in enumerate(cem.frames):
            transMatrix = Matrix(frame.transformationMatrix.toTuple())
            locVec = Vector(frame.tagPoints[i].toTuple())

            tagPoint.location = transMatrix @ locVec

            if cem.header.frames > 1:
                tagPoint.keyframe_insert("location", frame=n)
