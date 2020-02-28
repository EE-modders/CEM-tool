import bpy
import math
 
# mesh arrays
verts = []
faces = []
edges = []
 
#3D supershape parameters
m = 14.23
a = -0.06
b = 2.78
n1 = 0.5
n2 = -.48
n3 = 1.5
 
scale = 3
 
Unum = 50
Vnum = 50
 
Uinc = math.pi / (Unum/2)
Vinc = (math.pi/2)/(Vnum/2)
 
#fill verts array
theta = -math.pi
for i in range (0, Unum + 1):
    phi = -math.pi/2
    r1 = 1/(((abs(math.cos(m*theta/4)/a))**n2+(abs(math.sin(m*theta/4)/b))**n3)**n1)
    for j in range(0,Vnum + 1):
        r2 = 1/(((abs(math.cos(m*phi/4)/a))**n2+(abs(math.sin(m*phi/4)/b))**n3)**n1)
        x = scale * (r1 * math.cos(theta) * r2 * math.cos(phi))
        y = scale * (r1 * math.sin(theta) * r2 * math.cos(phi))
        z = scale * (r2 * math.sin(phi))
 
        vert = (x,y,z) 
        verts.append(vert)
        #increment phi
        phi = phi + Vinc
    #increment theta
    theta = theta + Uinc
 
#fill faces array
count = 0
for i in range (0, (Vnum + 1) *(Unum)):
    if count < Vnum:
        A = i
        B = i+1
        C = (i+(Vnum+1))+1
        D = (i+(Vnum+1))
 
        face = (A,B,C,D)
        faces.append(face)
 
        count = count + 1
    else:
        count = 0
 
#create mesh and object
mymesh = bpy.data.meshes.new("supershape")
myobject = bpy.data.objects.new("supershape",mymesh)
 
#set mesh location
myobject.location = bpy.context.scene.cursor.location
bpy.context.scene.objects.link(myobject)
 
#create mesh from python data
mymesh.from_pydata(verts,edges,faces)
mymesh.update(calc_edges=True)
 
#set the object to edit mode
bpy.context.scene.objects.active = myobject
bpy.ops.object.mode_set(mode='EDIT')
 
# remove duplicate vertices
bpy.ops.mesh.remove_doubles() 
 
# recalculate normals
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
 
# subdivide modifier
myobject.modifiers.new("subd", type='SUBSURF')
myobject.modifiers['subd'].levels = 3
 
# show mesh as smooth
mypolys = mymesh.polygons
for p in mypolys:
    p.use_smooth = True
