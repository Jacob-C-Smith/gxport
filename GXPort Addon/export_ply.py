import bpy
import bmesh
from struct import pack

def export_ply (filepath, mesh=bpy.context.selected_objects[0], comment=None, use_geometry=True, use_uv=False, use_normals=False, use_tangents=False, use_bitangents=False, use_colors=False, use_bone_groups=False, use_bone_weights=False ):
    
    # Vertex groups 
    
    # Flags for vertex groups

    # Vertex arrays
    geometry_array    = []
    tuv_array         = []
    uv_array          = []
    normal_array      = []
    bitangent_array   = []
    color_array       = []
    bone_group_array  = []
    bone_weight_array = []
    
    # The UV 
    active_uv         = mesh.data.uv_layers.active.data
    
    # Make a bmesh to access faces, edges, and verts
    bm                = bmesh.new()

    # Point the bmesh to the right mesh
    bm.from_mesh(mesh.data)

    # Buffer faces, edges, and vertices in the array
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    
    # Vertex data
    vertices      = {}
    vertices_count = len(mesh.data.vertices)
    
    if use_geometry == True:
        vertices['xyz']  = []
    
    if use_uv == True:
        vertices['st'] = []
    
    if use_normals == True:
        vertices['nxyz'] = []
        
    if use_bitangents == True:
        vertices['bxyz'] = []
        
    if use_colors == True:
        vertices['rgba'] = []
        
    if use_bone_groups == True:
        vertices['bgroups'] = []
        
    if use_bone_weights == True:
        vertices['bweights'] = []
    
    
    # Face data
    faces_count   = len(mesh.data.polygons)
    faces         = []
    
    # Populate the vertices dictionary
    for v in bm.verts:
        
        if use_geometry == True:
            geometry_array.append(v.co)
        
       
        if use_normals == True:
            normal_array.append(v.normal)
    
    for f in mesh.data.polygons:
         if use_uv == True:    
            tuv_array = [
                active_uv[l].uv[:]
                for l in range(f.loop_start, f.loop_start + f.loop_total)
            ]
    
    bone_weights_and_groups = get_bone_groups_and_weights(mesh)
    
    if bone_weights_and_groups is not None:
        bone_group_array = bone_weights_and_groups[0]
        bone_weight_array = bone_weights_and_groups[1]
    else:
        bone_group_array = None
        bone_weight_array = None
        
    #for j, v in enumerate(f.vertices):
    #    uv_array.append((tuv_array[j][0], tuv_array[j][1]))
            

    
    if use_geometry == True:
        vertices['xyz'] = geometry_array
        
    if use_uv == True:
        vertices['st'] = uv_array
        
    if use_normals == True:
        vertices['nxyz'] = normal_array
    #, uv_array, normal_array, bitangent_array, color_array, bone_group_array, bone_weight_array ) )
    

    vertices['bgroups']  = bone_group_array
    vertices['bweights'] = bone_weight_array
    
    
    # Populate the faces list
    for f in mesh.data.polygons:
        face = []
        for i in f.vertices:
            face.append(i)
        faces.append(face)
            
    # Write the PLY file
    with open(filepath, "wb") as file:
        
        # Shorthand for file write
        wr = file.write
        
        # Construct the header
        
        # Signature
        wr(b"ply\n") 
        
        # Format
        wr(b"format binary_little_endian 1.0\n")
        
        if comment is not None:
            
            # Split the comments on newlines
            comments = comment.split('\n')
            
            # Iterate through the split comments, wrting one per line
            for c in comments:
                comment = str("comment " + str(c) + '\n')        
                wr(comment.encode('utf-8'))
        
        
        # Write vertex groups
        wr(b"element vertex %d\n" % vertices_count)
        
        # Geometry
        if use_geometry == True and vertices['xyz'] is not None:
            wr(b"property float x\n")
            wr(b"property float y\n")
            wr(b"property float z\n")
        
        # UV
        if use_uv == True and vertices['st'] is not None:
            wr(b"property float s\n")
            wr(b"property float t\n")
        
        # Normals
        if use_normals == True and vertices['nxyz'] is not None:
            wr(b"property float nx\n")
            wr(b"property float ny\n")
            wr(b"property float nz\n")

        # Tangent
        if use_tangents == True and vertices['txyz'] is not None:
            wr(b"property float tx\n")
            wr(b"property float ty\n")
            wr(b"property float tz\n")
            
        # Bitangents
        if use_bitangents == True and vertices['bxyz'] is not None:
            wr(b"property float bx\n")
            wr(b"property float by\n")
            wr(b"property float bz\n")

        # Colors
        if use_colors == True  and vertices['rgba'] is not None:
            wr(b"property uchar r\n")
            wr(b"property uchar g\n")
            wr(b"property uchar b\n")
            wr(b"property uchar a\n")
            
        # Bone groups
        if use_bone_groups == True and vertices['bgroups'] is not None:
            wr(b"property uint b0\n")
            wr(b"property uint b1\n")
            wr(b"property uint b2\n")
            wr(b"property uint b3\n")
        
        # Bone weights
        if use_bone_weights == True and vertices['bweights'] is not None:
            wr(b"property float w0\n")
            wr(b"property float w1\n")
            wr(b"property float w2\n")
            wr(b"property float w3\n")
        
        # Face list
        wr(b"element face %d\n" % len(mesh.data.polygons))
        
        # Face indices
        wr(b"property list uchar int vertex_indices\n")
        
        # You can continue to add aditional elements here.
        # Not sure what or why yet, but its a possibility
        
        # Done writing the header
        wr(b"end_header\n")
        
        for f in bm.faces:
            uv = [
                active_uv[l].uv[:]
                for l in range(len(f.loops))
            ]
            
            for j, v in enumerate(f.verts):
                
                # Write the geometry data for the vertex on the iterator
                if use_geometry == True:
                    g  = vertices['xyz'][f.verts[j].index]
                    wr(pack("<3f", *g))
            
                # Write texture coordinates for the vertex on the iterator
                if use_uv == True:
                    
                    wr(pack("<2f", uv[j][0], uv[j][1]))
            
                # Write normal vector for the vertex on the iterator
                if use_normals == True:
                    n = vertices['nxyz'][f.verts[j].index]
                    wr(pack("<3f", *n))
                '''
                # Write bitangent vector for the vertex on the iterator                
                if bitangent is not None:
                    wr(pack("<3f", *bitangent))
            
                # Write color data  for the vertex on the iterator
                if colors is not None:
                    wr(pack("<4B", *colors))
                '''
                # Write bone groups for the vertex on the iterator
                if use_bone_groups == True:
                    bg = vertices['bgroups'][i]
                    wr(pack("<4i", *bg))
            
                # Write bone weights for the vertex on the iterator
                if use_bone_weights == True:
                    bw = vertices['bweights'][i]
                    wr(pack("<4f", *bw))
                    
        
        # 

        # Start writing faces
        for face in faces:
            verts_in_face = len(face)
            facew = "<" + str(verts_in_face) + "I"
            wr(pack("<b", verts_in_face))
            wr(pack(facew, *face))


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

export_ply(filepath="C:/Users/j/Desktop/test.ply", comment="Written by Jake Smith")