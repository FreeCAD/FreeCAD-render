# View options

View options allow to adjust the way a particular object is rendered.

As a reminder, the View is what you create to incorporate a FreeCAD object in a
rendering project.

<img src=./View.png>


## Material & Textures options

These options are related to rendering material.

Parameter | Type | Description
----------|------|------------
`Material` | Link | A link to the rendering material to use to render this object. If set, this parameter overrides the object's one. Nota: the preferred way should remain to assign material to the object, not to the view.
`Uv mapping` | [Cubic, Spherical, Cylindric] | The type of projection to use for uv mapping.

Nota: Uv mapping will be used only if the material contains textures. For now, we support 3 types of projections:
- Cubic: this projection maps the mesh onto the faces of a cube, which is then unfolded.
- Cylindric: this projection maps the mesh onto a cyclinder. The "up" is on Z
  axis in the object local coordinates.
- Spherical: the same with a sphere (up on Z axis)


## Smooth options

These options are related to mesh smoothing.

Parameter | Type | Description
----------|------|------------
`Auto Smooth` | Boolean | A flag to enable/disable mesh smoothing during rendering.
`Auto Smooth Angle` | Angle (in degrees) | The angle above which an edge will not be smoothed.


Please note that smoothing is enabled by default, to avoid disgraceful
tessellation at rendering. In most cases, it should not be disabled. However,
smoothing involves calculations that can be lengthy, especially for large
meshes, and in some cases, may bring only a small benefit, if the mesh is dense
enough. In this case, you may disable smoothing here.
