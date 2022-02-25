import bpy

def getPosesList(o):
    
    if o.type != 'ARMATURE':
        return None
    
    ret = []
    
    for p in o.pose_library.pose_markers:
        ret.append((p.frame,p.name))
        
    for p in ret:
        print(p)

    return ret

def exportPoseAsJSON(o, name):
    
    
    
    return None

def exportBoneAsJSON(b):
    
    ret = {
        "name" : b.name,
    }
    
    m = b.matrix_local.decompose()
    
    ret["location"]   = [ m[0][0], m[0][1], m[0][2] ] 
    ret["quaternion"] = [ m[1][0], m[1][1], m[1][2], m[1][3] ]
    ret["scale"]      = [ m[2][0], m[2][1], m[2][2] ] 
    
    print(str(ret))
    
    return 

def getPoseMatrices(o):
    
    return None

getPosesList(bpy.context.selected_objects[0])
exportBoneAsJSON(bpy.context.selected_objects[0].data.bones['spine'])