Materials
=========
Materials are a general way to modify the rendering appearance of an object
when processed by a rendering engine. All renderers (POV-Ray, Cycles etc.)
support such a functionality.

Materials make it possible to give objects various final aspects, like glass,
coated painting etc., in order to improve rendering realism:

<img src=./Appleseed_glass.png alt="GlassMaterial"
title="Sphere rendered with red glass material, with a white matte ground plane
(render engine: Appleseed)" height=400>

Render Workbench provides features to add material rendering information to
objects exported to renderers.

To make things easier, these features heavily rely on the standard Material
data system of FreeCAD. An introduction to FreeCAD Material system can be found
here: 
[FreeCAD Material Introduction](https://wiki.freecadweb.org/Material).

*Please note that it eventually leads to 2 concepts of "materials":
FreeCAD Material, the material feature of FreeCAD ; and
Rendering material, the material feature of the renderers.*

You will find below some indications about how to use Materials in Render
Workbench.

## Adding Material rendering information to an object
The general workflow to add material rendering information to an object is
quite simple:
1. Create a FreeCAD Material in the document
2. Set the rendering parameters of your Material
3. Assign this FreeCAD Material to the object, or to its view in the rendering project

Let's detail those three steps:

### Step #1: Create a Material in your document

Open the Material Creator: 
<img src=../Render/resources/icons/Arch_Material_Group.svg alt="editor" title="Creator Command"
height=32>

Choose a preset (ie a Material Card) and give a name to your new material. Click
OK. This should import the selected preset into a new Material in your
project.

Remark: You can find more information in FreeCAD documentation:
[Add Material in FreeCAD](https://wiki.freecadweb.org/Arch_SetMaterial)



### Step #2: Edit rendering settings of your new Material

Select your new Material and open the rendering settings editor by the command
available in Render Workbench toolbar:
<img src=../Render/resources/icons/MaterialSettings.svg alt="editor" title="Editor Command"
height=32>

Choose the material type and tweak the rendering settings of your Material.

At the moment, the following material types are available:
- Diffuse
- Disney
- Glass
- Mixed (a mix between Diffuse and Glass)
- Carpaint
- Substance_PBR
You may find more information about those materials and their settings in your
renderer documentation, or in general CG documentation.



### Step #3: Assign your FreeCAD Material to your object
Select your object and open Material Applier:
<img src=../Render/resources/icons/ApplyMaterial.svg alt="applier" title="Applier Command"
height=32>

Select the Material to apply, and click OK. You're done.


Please note the following remarks:
- As an alternative to using the Applier, you can directly edit the `Material`
  property of your object, if there is one. However, you should find the Applier
  more practical.
- It is also possible to set the Material of the *View* of the object in the
  rendering project. It will override the Material definition in the object, so
  it can be useful in some cases (when you cannot create or modify the Material
  property of an object, for instance).  However, it is recommended to use the
  Material of the object whenever possible.


**At this stage, you should have some usable rendering information attached to your object.**
**If this is your main goal, you may skip the rest of this page.**

## How Render Workbench uses Material rendering settings

### Inputs
Once an object has been assigned a FreeCAD Material with relevant rendering
information, the rendering material computation process can take place at render
time.
It is based on the following inputs:
- An object being rendered
- A FreeCAD Material (https://wiki.freecadweb.org/Material)
- A renderer
- A default color for the object being rendered. This data is taken from the
object's shape color in FreeCAD, and is provided to the process mainly for
fallback.

### Workflow
The workflow goes through the following steps:
1. The workbench looks into the FreeCAD Material for a passthrough material
definition for the given renderer.
A passthrough is a piece of code, written in the renderer's SDL (Scene
Description Language), which can be passed directly to the renderer.
2. If no passthrough, the workbench looks into the FreeCAD Material for a
standard rendering material definition.
This standard material is parsed and consolidated into an internal object,
which in turn is passed to the renderer plugin to be translated into
renderer's SDL (it being agreed that every renderer plugin is required to
have capabilities to translate standard materials into its renderer's SDL).
3. If no standard material, the workbench looks into FreeCAD Material for a
Father material. If there is one, it loops to step #1 with this Father.
4. If no father, the workbench tries to tinker a substitute fallback matte
material with FreeCAD Material DiffuseColor, or with object's default color,
or, at the last end, with white color.

Please note that the preferred method for material definition should definitely
be standard material, as it is the most generic way to do so.
Indeed, passthrough is a highly renderer-specific way to define a material, and
should be used only when standard material is not sufficient.


## Textures

You can add textures to your material, to be used as inputs to material's parameters.
To do so, right-click on the material and select 'Add Texture'.
The new texture appears under the material:

<img src=./material_texture.png alt="MaterialTexture">


For the new texture to be usable, you must upload at least one image: set the
'Image' parameter.
You can then add as many other images as you want. Textures can indeed be
composed of different images for different purposes (color, bump map, normal
map...). Use 'Add image entry' in texture's right-click menu.


<img src=./manyimages_texture.png alt="ManyimagesTexture">

Optionally, you can set the mapping parameters (rotation, scale, translation).

Once you have a workable texture, you can use it in rendering parameters:
right-click on your material, select 'Edit Render Settings' to open your
material's settings; set the parameter to 'Use texture' and select the texture
you want in the combo box. You should get something like that:

<img src=./textures.png alt="TextureSettings">

Caveats:
- Textures cannot be used standalone: they are necessarily linked to a
  material.
- A material can only access its own textures (not the textures of another
  material).
- Textures images are stored inside the .fcstd file. Intensive use of textures
  may affect file size!


## Writing Material card for rendering <a name="parameters"></a>
In [Step #1](#step-1-create-a-material-in-your-document) above, you have imported a
Material Card into a Material, and then set up the rendering parameters.

If you don't want to specify your rendering parameters each time you create a
new Material in your document, you can also directly set your rendering
parameters in the Material Card.
A description of the FreeCAD material card format, the creation and the import
processes of such a card can be found here in FreeCAD documentation:
[FreeCAD material card file format](https://wiki.freecadweb.org/Material#The_FreeCAD_material_card_file_format).

The relevant parameters to be used for rendering material are to be found
below in chapter [Material card settings for rendering](#parameters)

This section explains how to write rendering parameters in material cards files
(.FCMat).

### General recommendations

- Material card files (.FCMat) follows the "Ini" file format, as described in
FreeCAD documentation:
[FreeCAD material card file format](https://wiki.freecadweb.org/Material#The_FreeCAD_material_card_file_format).
Be sure to have understood the general format before adding specific rendering
parameters.
- Rendering parameters should be gathered under a `[Rendering]` section.
It is not mandatory but it can improve the readability of the material
card.
- Decimal separator will always be a dot (`3.14`), whatever locale settings
may exist in the system.
- No quote must be used to enclose values, even string values. Such quotes would be
considered as part of the value by parser, and lead to subtle issues.
In particular, be careful when specifying `Render.Type` parameter:
  - `Render.Type=Diffuse` --> OK ;
  - `Render.Type="Diffuse"` --> NOK.
- Multi-line value are not allowed by FCMat syntax. Therefore all values
must fit in one line.
- Keys are case-sensitive: `Render.Type` is different from `Render.type`
- Values are case-sensitive as well: `Diffuse` is different from `diffuse`
- Duplicated keys lead to undefined behaviour.

### Standard materials

Standard materials are declared by specifying a type with a `Render.Type`
parameter, and setting some other parameters specific to this type.

#### Common parameters

All materials will accept the following input parameters:

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.<material>.Bump` | texonly |  | Bump texture
`Render.<material>.Normal` | texonly |  | Normal texture

Those parameters create bump/normal effects and are "texture only".

Nearly all materials, except `Substance_PBR`, will also accept the following,
for displacement effect:

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.<material>.Displacement` | texonly |  | Displacement texture


#### **Diffuse** Material

A simple matte material, usually based on ideal Lambertian reflection.

`Render.Type=Diffuse`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Diffuse.Color` | RGB | (0.8, 0.8, 0.8) | Diffuse color


#### **Disney** Material

A versatile material, based on the Disney principled model also known as the
"PBR" shader, capable of producing a wide variety of materials (e.g., plastic,
metal...) by combining multiple different layers and lobes.

`Render.Type=Disney`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Disney.BaseColor` | RGB | (0.8, 0.8, 0.8) | Base color
`Render.Disney.Subsurface` | float | 0.0 | Subsurface coefficient
`Render.Disney.Metallic` | float | 0.0 | Metallic coefficient
`Render.Disney.Specular` | float | 0.0 | Specular coefficient
`Render.Disney.SpecularTint` | float | 0.0 | Specular tint coefficient
`Render.Disney.Roughness` | float | 0.0 | Roughness coefficient
`Render.Disney.Anisotropic` | float | 0.0 | Anisotropic coefficient
`Render.Disney.Sheen` | float | 0.0 | Sheen coefficient
`Render.Disney.SheenTint` | float | 0.0 | Sheen tint coefficient
`Render.Disney.ClearCoat` | float | 0.0 | Clear coat coefficient
`Render.Disney.ClearCoatGloss` | float | 0.0 | Clear coat gloss coefficient

#### **Glass** Material

A glass-like shader mixing refraction and reflection at grazing angles,
suitable for transparent materials (glass, water, transparent plastics...).

`Render.Type=Glass`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Glass.IOR` | float | 1.5 | Index of refraction
`Render.Glass.Color` | RGB | (1, 1, 1) | Transmitted color

#### **Substance_PBR** Material

A shader created to give a good visual match with PBR materials (roughness
based workflow), specially intended to textured materials.

`Render.Type=Substance_PBR`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Substance_PBR.BaseColor` | RGB | (0.8, 0.8, 0.8) | Base color
`Render.Substance_PBR.Roughness` | float | 0.0 | Roughness
`Render.Substance_PBR.Metallic` | float | 0.0 | Metallic

#### **Mixed** Material

A material mixing a Diffuse and a Glass submaterials. This material is
specifically designed to render FreeCAD transparent objects.

`Render.Type=Mixed`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Mixed.Glass.IOR` | float | 1.5 | Index of refraction
`Render.Mixed.Glass.Color` | RGB | (1, 1, 1) | Transmitted color
`Render.Mixed.Diffuse.Color` | RGB | (0.8, 0.8, 0.8) | Diffuse color
`Render.Mixed.Transparency` | float | 0.5 | Mix ratio between Glass and Diffuse (should stay in [0,1], other values may lead to undefined behaviour)


#### Textures

Text  


### **Passthrough** material

A material which allows to pass direct statements to the renderer. Warning:
the result is renderer-specific.

#### General syntax
Passthrough materials are defined using `Render.<renderer>.<line>` entries,
where:
* `<renderer>` is to be replaced by the name of the renderer targeted for the
passthrough
* `<line>` is to be replaced by line numbers, in a four-digits integer format:
`0001`, `0002` etc.

Note that spreading the material definition onto multiple keys/values is a
workaround to overcome the monoline syntactical limitation of FCMat format.

#### Renderer
For the passthrough material to be recognised internally, the renderer name
(`<renderer>`) must match the name of an existing renderer.
In particular, this name is case-sensitive.
Known renderers can be retrieved from Render workbench entering the following
code in FreeCAD console:
```python
import Render
print(Render.RENDERERS)
```

#### Lines order
Lines will be internally considered in sorted order, whatever order they follow
in FCMat file. For instance, the following sequence in FCMat file:
```
Render.Some_renderer.0002 = foo
Render.Some_renderer.0003 = baz
Render.Some_renderer.0001 = bar
```
...will always lead to the following internal representation:
```txt
bar
foo
baz
```

#### Pseudovariables
In addition, passthrough parameters syntax provides a set of pseudovariables
instantiated at render time, which can be useful to adapt the passthrough
to realtime context.

Those pseudovariables are described in the array below, note that the term
*rendered object* stands for the object which the material is applied to
at render time:

| Pseudovariable | Type   | Description                                                |
| -------------- | ------ | ---------------------------------------------------------- |
| `%NAME%`       | string | The name of the rendered object                            |
| `%RED%`        | float  | The default color of the rendered object - red component   |
| `%GREEN%`      | float  | The default color of the rendered object - green component |
| `%BLUE%`       | float  | The default color of the rendered object - blue component  |



### Material Cards Examples

#### Example #1: Diffuse material with red color
```INI
[Rendering]
Render.Type = Diffuse
Render.Diffuse.Color = (0.8,0,0)
```

#### Example #2: Glass material
```INI
[Rendering]
Render.Type = Glass
Render.Glass.IOR = 1.5
Render.Glass.Color = (1,1,1)
```

#### Example #3: Mirror passthrough material for Luxcore
```INI
[Rendering]
Render.Luxcore.0001 = scene.materials.%NAME%.type = mirror
Render.Luxcore.0002 = scene.materials.%NAME%.kr = %RED% %GREEN% %BLUE%
```

#### Example #4: Mirror passthrough material for Appleseed
```INI
[Rendering]
Render.Appleseed.0001 = <!-- Generated by FreeCAD - Color '%NAME%_color' -->
Render.Appleseed.0002 = <color name="%NAME%_color">
Render.Appleseed.0003 =     <parameter name="color_space" value="linear_rgb" />
Render.Appleseed.0004 =     <parameter name="multiplier" value="1.0" />
Render.Appleseed.0005 =     <parameter name="wavelength_range" value="400.0 700.0" />
Render.Appleseed.0006 =     <values> %RED% %GREEN% %BLUE% </values>
Render.Appleseed.0007 = </color>
Render.Appleseed.0008 = <bsdf name="%NAME%_bsdf" model="specular_brdf">
Render.Appleseed.0009 =     <parameter name="reflectance" value="%NAME%_color" />
Render.Appleseed.0010 = </bsdf>
Render.Appleseed.0011 = <material name="%NAME%" model="generic_material">
Render.Appleseed.0012 =     <parameter name="bsdf" value="%NAME%_bsdf" />
Render.Appleseed.0013 =     <parameter name="bump_amplitude" value="1.0" />
Render.Appleseed.0014 =     <parameter name="bump_offset" value="2.0" />
Render.Appleseed.0015 =     <parameter name="displacement_method" value="bump" />
Render.Appleseed.0016 =     <parameter name="normal_map_up" value="z" />
Render.Appleseed.0017 =     <parameter name="shade_alpha_cutouts" value="false" />
Render.Appleseed.0018 = </material>
```
