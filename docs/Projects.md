# Project options

Project options allow to control rendering process and result.

## Rendering process options

Parameter | Type | Description
----------|------|------------
`Renderer` | String | The name of the raytracing engine to use
`Template` | File | The template to be used by the rendering
`Delayed Build` | Boolean | If true, the views will be updated at render time only
`Page Result` | Included File | The exported file to be sent to the external renderer
`Output Image` | File | The image file saved by the rendering
`Open After Render` | Boolean | If true, the rendered image is opened in FreeCAD when the rendering is done

## Rendering result options

Parameter | Type | Description
----------|------|------------
`Render Width` | Integer | The width of the rendered image (in pixels)
`Render Height` | Integer | The height of the rendered image (in pixels)
`Ground Plane` | Boolean | If true, a default ground plane is added to the scene

## Mesher options

These parameters controls mesher behaviour. Render uses FreeCAD standard
mesher, you may find some more information in [FreeCAD
documentation](https://wiki.freecadweb.org/Mesh_FromPartShape#Standard_mesher)

Parameter | Type | Description
----------|------|------------
`Linear Deflection` | Float | The maximum linear deviation of a mesh section from the surface of the object (the lower the finer).
`Angular Deflection` | Float | The maximum angular deviation from one mesh section to the next, in radians. This setting is used when meshing curved surfaces (the lower the finer).

**Warning:** Be careful when setting those parameters. Unappropriate values can lead to extremely long processing duration.
