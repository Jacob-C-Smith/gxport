import bpy
import math
import mathutils

def recenterObject(o):
    exit = False
    while exit == False:
            
        # TODO: Replace with float min and float max constants
        mx=-99999999
        my=-99999999
        mz=-99999999

        Mx=999999999
        My=999999999
        Mz=999999999 
    
        # Find minimum and maximum dimensions
        for v in o.data.vertices:
        
            if v.co[0] > mx:
                mx = v.co[0]
            if v.co[1] > my:
                my = v.co[1]
            if v.co[2] > mz:
                mz = v.co[2]
        
            if v.co[0] < Mx:
                Mx = v.co[0]
            if v.co[1] < My:
                My = v.co[1]
            if v.co[2] < Mz:
                Mz = v.co[2]        
    
        print (str(mx) + " " + str(Mx))
        print (str(my) + " " + str(My))
        print (str(mz) + " " + str(Mz))

        # Calculate a new median point
        medianx = (mx + Mx) / 2
        mediany = (my + My) / 2
        medianz = (mz + Mz) / 2

        # Print median x, y, z
        print( medianx )
        print( mediany )
        print( medianz )
        
        if medianx < 0.0001 and medianx > -0.0001 and mediany < 0.0001 and mediany > -0.0001 and medianz < 0.0001 and medianz > -0.0001:
            exit = True 
        
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='EDIT')
            
        bpy.ops.transform.translate(value=(-medianx, -mediany, -medianz))
    
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.transform.translate(value=(medianx, mediany, medianz))
            

        
    print(o.name + " DONE")     
        
    # Return minimum and maximum dimensions
    return [ [ mx, my, mz ], [ Mx, My, Mz ] ]

l =[]
for o in bpy.context.selected_objects:
    o.select_set(False)
    l.append(o)

l.append(None)

for o in l:
    if o is not None:
        o.select_set(True)
        recenterObject(o)
        o.select_set(False)
    
    