# Renderers plug-ins directory
This is the renderers plug-ins directory.

## How FreeCAD-render works with external renderers
To obtain a rendering, FreeCAD-render writes a file (the *input file*) in a renderer format and runs an external renderer on this file. As a result, the external renderer outputs an image file.

The input file is built by instantiating a *template* with *descriptions* of FreeCAD objects in renderer format:
* The template basically contains blank sections to fill with objects descriptions, following the general structure expected by the renderer, and also contained predefined settings designed for given use cases: standard scene, sunlight scene...
* The objects descriptions in renderer format are built by ad hoc plug-ins.


## How to add support for a new external renderer
### Files required
To add support for a new renderer, you will need to add at least 3 files:
- A renderer plug-in file,
- An icon file,
- One or more templates file(s),

| Files            | Number    | Location       | File format          |
| ---------------- | --------: | -------------- | ---------------------|
| Renderer plug-in | 1         | This directory | Python               |
| Icon             | 1         | ../icons       | Image (png, svg...)  |
| Templates        | 1 or more | ../templates   | Your renderer format | 

On an optional but strongly recommended basis, you may also want to add some entries in module's Preferences page.
In particular, it is strongly recommended to include the following parameters:
- the path to the external renderer executable (optionnally splitted into CLI and GUI executables, if the renderer supports so),
- the basic command line parameters.


### Renderer plug-in
#### Naming
 
You will need to make sure your plugin file is named with the same name (case sensitive)
that you will use everywhere to describe your renderer. Examples: `Appleseed.py` or
`Povray.py`

#### Contents
The module must contain the following functions:

* `write_object(view, mesh, color, alpha)`

Expected behaviour: return a string containing a mesh object description in renderer format

* `write_camera(pos, rot, up, target, name)`

Expected behaviour: return a string containing a camera description in renderer format

* `write_pointlight(view, location, color, power)`

Expected behaviour: return a string containing an point light description in renderer format

* `write_arealight(name, pos, size_u, size_v, color, power)`

Expected behaviour: return a string containing an area light description in renderer format

* `render(project, prefix, external, output, width, height)`

Expected behaviour: render the given project, by calling the external renderer.
This function is in charge of writing the renderer input file, and calling the external renderer executable. It should return the path to the generated image file.

#### Guidelines
- Before starting, have a look at other existing renderers plug-ins. You can use one of them as a template for a new plugin
- Use Python's Format Specification Mini Language in `write_*` functions
- Carefully read your renderer documentation. For future reviewing, do not hesitate to add links to the documentation in your code, as comments.
- Pay attention to the coordinates systems. External renderers may use different coordinates than FreeCAD (inverted coordinates etc.)

### Template file

#### Naming
The name of the file should contain a reference to your renderer, and then a reference to the use case the template addresses.
The file extension should be the extension expected by the renderer in its input file.
Example: `appleseed_standard.appleseed`

### Icon file

#### Naming
The name of the icon file should be the same as the plug-in file. Example: `Appleseed.svg`.

Recommended format is Scalable Vector Graphics (SVG).
