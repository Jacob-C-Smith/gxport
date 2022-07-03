# gxport
 gxport (G10 export) is an Add-on for Blender. gxport writes Blender scenes to a user specified directory. gxport will create a file structure, containing your textures, meshes, G10 materials, G10 Entities, colliders, and your G10 scene.

 
```
.
├── Scene.json
├── colliders
├── entities
│   ├── Ancient Pot.json
│   ├── Floor.json
│   ├── Front Wall.json
│   └── Side Wall.json
├── materials
│   ├── Ancient Pot.json
│   ├── Floor.json
│   ├── Front Wall.json
│   └── Side Wall.json
├── parts
│   ├── Ancient Pot.json
│   ├── Ancient Pot.ply
│   ├── Floor.json
│   ├── Floor.ply
│   ├── Front Wall.json
│   ├── Front Wall.ply
│   ├── Side Wall.json
│   └── Side Wall.ply
├── skybox
│   ├── World.hdr
│   └── World.json
└── textures
    ├── Ancient Pot Material
    │   ├── albedo.png
    │   ├── metal.png
    │   ├── normal.png
    │   └── rough.png
    ├── Grime Alley Bricks 2
    │   ├── albedo.png
    │   ├── metal.png
    │   ├── normal.png
    │   └── rough.png
    └── Mahogany Floor
        ├── albedo.png
        ├── metal.png
        ├── normal.png
        └── rough.png
 ```