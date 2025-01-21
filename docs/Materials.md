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
2. Assign this FreeCAD Material to the object

Let's detail those two steps:

### Step #1: Create a Material in your document


Open a Material library:
- OpenGPU (external): <img src=../Render/resources/icons/amdgpuopen.png alt="amdgpuopen" title="OpenGPU Library"
height=24>
- AmbientCG (external) <img src=../Render/resources/icons/ambientcg.png alt="ambientcg" title="AmbientCG Library"
height=24>
- Internal: <img src=../Render/resources/icons/Arch_Material_Group.svg alt="internal" title="Internal Library"
height=24>

Select your material and download it. Materials imported from external libraries should be ready-to-use.

**Caveat**: for external libraries, you'll need MaterialX to be installed on your system.



### Step #1bis: Tweak your material (optional)
Optionally, you can edit the rendering settings of your material:

Select your new Material and open the rendering settings editor by the command
available in Render Workbench toolbar:
<img src=../Render/resources/icons/MaterialSettings.svg alt="editor" title="Editor Command"
height=32>

Choose the material type and tweak the rendering settings of your Material.


### Step #2: Assign your FreeCAD Material to your object
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

## Textures

### A few words about textures
First, let's remind of what a texture is, in Physically Based Rendering
context: in PBR, **a texture is a set of images that serve as inputs to a
material.**

The use of textures therefore presupposes the use of a material. _There is no
texture without material._
Each image is intended to feed one of the material's parameters: color,
roughness, normals, bumpiness, etc. The image is also called a map: color map,
roughness map, normal map, bump map...


### How it works in Render
In Render, you can use textures in your materials via a four steps process:

#### Step 1: Prepare
The first thing to do is to obtain the texture. Textures for rendering can be
downloaded from various sites, including [AmbientCG](https://www.ambientcg.com),
[MaterialX](https://matlib.gpuopen.com) etc.

Since it's usually shipped as a compressed file, you first have to unzip it
into a temporary directory. At this stage, you usually get a set of image files
plus a few other files containing metadata you may ignore (.usdc, .mtlx etc.).


<img src=./fileset_texture.png alt="Texture File Set">

As we have seen, texture is necessarily applied via a material. If you've
already got a material to be textured, you can jump to next step. If not, it is
recommended to use a Disney material, which is the most versatile solution.

#### Step 2: Upload
Then you have to store the texture into the material in FreeCAD.
To do so, right-click on your material and select 'Add Texture'.
A new texture object appears under the material:

<img src=./material_texture.png alt="MaterialTexture">

It contains:
- an Image field
- and mapping informations: rotation, scale, translation (in 2D)

You then have to upload your image files to this Render texture object:
- click on the Image field, and select your first image file in the file
  picker. The image file is being uploaded into the texture.
- If there are remaining image files, right-click on the texture and select
  'Add image entry' in the context menu. Click on the new Image field and
  select your file. Repeat till there is no more remaining image file.

You should obtain something like that:

<img src=./manyimages_texture.png alt="ManyimagesTexture">

Hints:
1. Some image files found in downloadable textures are useless for our
purposes. For instance:
    - Ambient Occlusion: this input is not handled by our renderers.
    - Normal DX: see note #2 below.
    - Preview (usually a .png file...): although it is an image file, this file
      is not intended to be an input for the material, but a way of assessing
      the texture result.

  You may ignore those files when uploading.

2. Some image names may be reinterpreted to connect to their target parameters:
    - Albedo should be connected to Color / Base Color
    - Displacement may rather be connected to Bump than to Displacement.

3. Due to FreeCAD's peculiarities, once you've uploaded a file to an Image
   field, it's no longer possible to modify this link. If you still want to
   make a modification, you need to delete the field, invoking 'Remove Image Entry' in
   texture context menu, and recreate it (please don't blame Render for this,
   this is FreeCAD related...).



#### Step 3: Connect
Once you have a workable texture, you can use it in rendering parameters:
1. Right-click on your material, select 'Edit Render Settings' to open your
material's settings
2. For each parameter affected by an image file, set the parameter to 'Use
   texture' and select the image file you want in the combo box. You should get
   something like that:

<img src=./textures.png alt="TextureSettings">

#### Step 4: Tweak
Optionally, you may set:
- the mapping parameters.
- the UV mapping: see next chapter.

#### Additional Notes
- Normal DX / Normal GL: Normal maps exist in two formats : DX (DirectX)
  and GL (OpenGL). Both formats strictly contain the same information, but in
  two distinct encodings.
  _In Render, normal maps are expected to follow OpenGL encoding (not DirectX)._
  Hence NormalDX files are useless for us.
- The image files will be stored inside the .FCStd file. Large use of
  textures may affect file size!

### UV mapping
To correctly position the texture on the object, Render WB generates a UV
mapping. Three modes are available:
- Cubic
- Spherical
- Cylindrical
Those modes are accessible in the View of the object, in the parameter
`UV Projection` under the section `Material & Textures`.

<img src=./UVProjection.png alt="UV Projection">

By default, the cubic is mode is selected, which is suitable for most situations.

## Advanced information

See [Material - Advanced](./materials_advanced.md)
