import bpy
import mathutils

def centroid(vertexes):
    x_list = [vertex[0] for vertex in vertexes]
    y_list = [vertex[1] for vertex in vertexes]
    length = len(vertexes)
    x = sum(x_list) / length
    y = sum(y_list) / length
    return(mathutils.Vector((x, y)))

bpy.ops.object.mode_set(mode = 'OBJECT')

meshdata = bpy.context.active_object.data

for polygon in meshdata.polygons:
    # Get uv polygon center
    polygondata = ()
    for i in polygon.loop_indices:
        polygonvert = meshdata.uv_layers.active.data[i].uv[:] # Vector -> tuple
        polygondata += polygonvert,
    polygoncenter = centroid(polygondata)
    # Move MeshUVLoop if selected to polydon center
    for i in polygon.loop_indices:
        meshuvloop = meshdata.uv_layers.active.data[i]
        if meshuvloop.select:
            moveto = (meshuvloop.uv - polygoncenter) * 0.8 + polygoncenter
            meshuvloop.uv.x = moveto.x
            meshuvloop.uv.y = moveto.y
