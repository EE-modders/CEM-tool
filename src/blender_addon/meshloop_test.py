import bpy
 
#bpy.ops.object.mode_set(mode = 'OBJECT')
 
meshdata = bpy.context.active_object.data
 
for i, polygon in enumerate(meshdata.polygons):
    print('polygon: ', i)
    for i1, loopindex in enumerate(polygon.loop_indices):
        print('meshloop: ', i1, ' index: ',loopindex)
        
        meshloop = meshdata.loops[i1]
        meshvertex = meshdata.vertices[meshloop.vertex_index]
        meshuvloop = meshdata.uv_layers.active.data[loopindex]
        
        print('meshuvloop coords: ', meshuvloop.uv, ' selected: ', meshuvloop.select)
    