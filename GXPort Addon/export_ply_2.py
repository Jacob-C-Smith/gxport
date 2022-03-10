import bpy
from struct import pack
import bmesh

# This function gives me anxiety 
def get_bone_groups_and_weights(o):
    
    bone_vertex_indices_and_weights = { }
    bone_group_array  = []
    bone_weight_array = []
    
    if len(o.vertex_groups) == 0:
        return None
    
    # Find vertex indices and bone weights for each bone    
    for g in o.vertex_groups:
        
        # Make a dictionary key for each bone
        bone_vertex_indices_and_weights[g.name] = []
        
        # And a convenience variable
        working_bone = bone_vertex_indices_and_weights[g.name]
        
        for v in o.data.vertices:
            for vg in v.groups:
                if vg.group == g.index:
                    working_bone.append((v.index, vg.weight))
    
    '''
        bone_vertex_indices_and_weights now looks like
        {
            "bone name" : [ (1, 0.6), (2, 0.4), (3, 0.2), ... ],
            "spine"     : [ (9, 0.2), ... ],
            ...
            "head"      : [ ... , (3302, 0.23), (3303, 0.34), (3304, 0.6) ]
        }
    '''
    # This exporter only writes the 4 most heavily weighted bones to each vertex
    
    # Iterate over every vert
    for v in o.data.vertices:
        
        # Keep track of the 4 most heavy weights and their vertex groups
        heaviest_groups  = [ -1, -1, -1, -1 ] 
        heaviest_weights = [ 0, 0, 0, 0 ]
        
        # Iterate through bones
        for c in bone_vertex_indices_and_weights.keys():
            d = bone_vertex_indices_and_weights[c]
            
            for i in d:
                if v.index == i[0]:
                    if i[1] > heaviest_weights[0]:
                        heaviest_groups[0]  = o.vertex_groups[c].index
                        heaviest_weights[0] = i[1]
                    elif i[1] > heaviest_weights[1]:
                        heaviest_groups[1]  = o.vertex_groups[c].index
                        heaviest_weights[1] = i[1]
                    elif i[1] > heaviest_weights[2]:
                        heaviest_groups[2]  = o.vertex_groups[c].index
                        heaviest_weights[2] = i[1]
                    elif i[1] > heaviest_weights[3]:
                        heaviest_groups[3]  = o.vertex_groups[c].index
                        heaviest_weights[3] = i[1]
                    else:
                        None
        bone_group_array.append(heaviest_groups)
        bone_weight_array.append(heaviest_weights)

    
    return (bone_group_array, bone_weight_array)


# PLY exporter v2
def export_ply_2 ( mesh, file_path, comment=None, use_geometry=True, use_uv_coords=True, use_normals=True, use_tangents=False, use_bitangents=False, use_colors=False, use_bone_groups=False, use_bone_weights=False):
    
    # Convinience 
    active_uv_layer         = mesh.data.uv_layers.active.data
    active_col_layer        = None
    bone_groups_and_weights = None
    bone_groups             = None
    bone_weights            = None
    
    if use_colors:
        active_col_layer = mesh.vertex_colors.active.data
        
    # Make a new bmesh from the parameter
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    
    # Buffer lookup tables
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    
    # Dict for vertices and faces
    vertices = { }
    
    vertex_counter = 0
    
    faces   = { }
    
    if use_bone_groups or use_bone_weights:
        bone_groups_and_weights = get_bone_groups_and_weights(mesh)
        bone_groups  = bone_groups_and_weights[0]
        bone_weights = bone_groups_and_weights[1]
        
        
    # Iterate over all faces (faces are triangulated)
    for i, f in enumerate(bm.faces):
        
        # Face vertex attributes
        t             = [ None, None, None ]
        b             = [ None, None, None ]
        
        # Face indicies
        face_indicies = [ 0, 0, 0 ]
        
        # Compute the tangent and bitangent of the face        
        if use_tangents or use_bitangents:
            
            # < x, y, z > coordinates for each vertex in the face
            pos1                = (f.verts[0].co)
            pos2                = (f.verts[1].co)
            pos3                = (f.verts[2].co)    
        
            # < s, t > coordinates for each vertex
            uv1                 = active_uv_layer[f.loops[0].index].uv
            uv2                 = active_uv_layer[f.loops[1].index].uv
            uv3                 = active_uv_layer[f.loops[2].index].uv
        
            # Compute the edges 
            edge1               = pos2 - pos1
            edge2               = pos3 - pos1
        
            # Compute the difference in UVs
            delta1              = uv2 - uv1
            delta2              = uv3 - uv1
        
            # Compute the inverse determinant
            inverse_determinant = float(1) / float(delta1[0] * delta2[1] - delta2[0] * delta1[1])
        
            # Finally, construct the < tx, ty, tz > and < bx, by, bz > vectors
            t = [
                inverse_determinant * float( delta2[1] * edge1[0] - delta1[1] * edge2[0] ),
                inverse_determinant * float( delta2[1] * edge1[1] - delta1[1] * edge2[1] ),
                inverse_determinant * float( delta2[1] * edge1[2] - delta1[1] * edge2[2] )
            ]
            
            b = [
                inverse_determinant * float( -delta2[0] * edge1[0] + delta1[0] * edge2[0] ),
                inverse_determinant * float( -delta2[0] * edge1[1] + delta1[0] * edge2[1] ),
                inverse_determinant * float( -delta2[0] * edge1[2] + delta1[0] * edge2[2] )
            ]
        
        # Iterate over each vertex in the face
        for j, v in enumerate(f.verts):
            
            # Vertex attributes
            g  = [ None, None, None ]       # < x, y, z >
            uv = [ None, None ]             # < s, t >
            n  = [ None, None, None ]       # < nx, ny, nz >
            c  = [ None, None, None, None ] # < r, g, b, a >
            bg = [ None, None, None, None ] # < g0, g1, g2, g3 > 
            bw = [ None, None, None, None ] # < w0, w1, w2, w3 >
            
            # < x, y, z > of current vert
            if use_geometry:
                g  = f.verts[j].co
            
            # < s, t > of current vert
            if use_uv_coords:
                uv = active_uv_layer[f.loops[j].index].uv
            
            # < nx, ny, nz > of current vert
            if use_normals:
                n  = f.verts[j].normal
            
            # < r, g, b, a >
            if use_colors:
                c  = active_col_layer[f.loops[j].index].color

            # TODO: Bone groups and weights
            if use_bone_groups:
                bg = bone_groups[f.verts[j].index]
                   
            if use_bone_weights:
                bw = bone_weights[f.verts[j].index]              
            
            # Combine < x, y, z >
            #         < s, t >
            #         < nx, ny, nz >
            #         < tx, ty, tz >
            #         < bx, by, bz >
            #         < r, g, b, a >
            #         < g0, g1, g2, g3 >
            #         < w0, w1, w2, w3 >
            
            combined_vertex = (
                                g[0] , g[1] , g[2],         # 0  : < x, y, z >
                                uv[0], uv[1],               # 3  : < s, t >
                                n[0] , n[1] , n[2],         # 5  : < nx, ny, nz >
                                t[0] , t[1] , t[2],         # 8  : < tx, ty, tz >
                                b[0] , b[1] , b[2],         # 11 : < bx, by, bz >
                                c[0] , c[1] , c[2] , c[3],  # 14 : < r, g, b, a >
                                bg[0], bg[1], bg[2], bg[3], # 18 : < g0, g1, g2, g3 >
                                bw[0], bw[1], bw[2], bw[3], # 22 : < w0, w1, w2, w3 >
                              )
            
            index = vertices.get(combined_vertex)
            
            if index is not None:
                face_indicies[j] = index
            else:            
                face_indicies[j] = vertex_counter
                vertices[combined_vertex] = vertex_counter
                
                vertex_counter = vertex_counter + 1

        faces[i] = face_indicies

    with open(file_path, "wb") as file:
        fw = file.write

        fw(b"ply\n")
        fw(b"format binary_little_endian 1.0\n")
        if comment is not None:
            fw(b"comment " + str(comment))

        fw(b"element vertex %d\n" % vertex_counter)
        
        if use_geometry:
            fw(
                b"property float x\n"
                b"property float y\n"
                b"property float z\n"
            )
        if use_uv_coords:
            fw(
                b"property float s\n"
                b"property float t\n"
            )
        if use_normals:
            fw(
                b"property float nx\n"
                b"property float ny\n"
                b"property float nz\n"
            )
        if use_tangents:
            fw(
                b"property float tx\n"
                b"property float ty\n"
                b"property float tz\n"
            )
        if use_bitangents:
            fw(
                b"property float bx\n"
                b"property float by\n"
                b"property float bz\n"
            )
        if use_colors:
            fw(
                b"property uchar red\n"
                b"property uchar green\n"
                b"property uchar blue\n"
                b"property uchar alpha\n"
            )
        if use_bone_groups:
            fw(
                b"property uchar b0\n"
                b"property uchar b1\n"
                b"property uchar b2\n"
                b"property uchar b3\n"
            )
        if use_bone_weights:
            fw(
                b"property uchar w0\n"
                b"property uchar w1\n"
                b"property uchar w2\n"
                b"property uchar w3\n"
            )
            
        fw(b"element face %d\n" % len(faces))
        fw(b"property list uchar uint vertex_indices\n")
        fw(b"end_header\n")
    
        # Iterate over vertices
        for v in vertices:
            
            # Write < x, y, z >
            if use_geometry:
                fw(pack("<3f", v[0] , v[1], v[2] ))
            
            # Write < s, t >
            if use_uv_coords:
                fw(pack("<2f", v[3] , v[4] ))
        
            # Write < nx, ny, nz >
            if use_normals:
                fw(pack("<3f", v[5] , v[6] , v[7] ))
        
            # Write < tx, ty, tz >
            if use_tangents:
                fw(pack("<3f", v[8] , v[9] , v[10]))
            
            # Write < bx, by, bz >
            if use_bitangents:
                fw(pack("<3f", v[11], v[12], v[13]))
    
            # Write < r, g, b, a >
            if use_colors:
                fw(pack("<4B", v[14], v[15], v[16], v[17]))
    
            if use_bone_groups:
                fw(pack("<4i", v[18], v[19], v[20], v[21]))
               
            
            if use_bone_weights:
                fw(pack("<4f", v[22], v[23], v[24], v[25]))
                    
        for i, f in enumerate(faces):
            w = "<3I"
            fw(pack("<b", 3))
            lf = faces[f] 
            fw(pack(w, lf[0], lf[1], lf[2]))
        
    return     

export_ply_2(bpy.context.selected_objects[0],"C:/Users/j/Desktop/ply_test_2.ply")
        