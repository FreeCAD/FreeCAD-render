# FreeCAD Render workbench

A [FreeCAD](https://www.freecadweb.org) workbench to produce high-quality
rendered images from your FreeCAD document, using open-source external
rendering engines.

<img src=./docs/freecad-june-09.jpg alt="ShowCase" title="Examples of rendering
made with Render workbench">


## Introduction

The Render workbench is a replacement for the built-in [Raytracing
workbench](https://www.freecadweb.org/wiki/Raytracing_Module) of FreeCAD. There
are several differences between the two:

* The Render workbench is written fully in Python, which makes it much easier
  to understand and extend by non-C++ programmers.
* Adding new render engines (renderers) is made easier as render engines are
  implemented as plugins. Compared to Raytracing, Render already supports
  several additional renderers, like Appleseed, LuxCoreRender and Cycles.
* The Render workbench provides extended capabilities, compared to Raytracing,
  like scene lighting, camera enhanced features and material support.

Some key-functionalities of built-in Raytracing are also present:
* Like the builtin Raytracing workbench, the Render workbench offers the
  possibility to update the View objects whenever its source object changes,
  which costs extra processing time everytime the source object changes. But it
  also offers a mode where the views are updated all at once, only when the
  render is performed. This makes the render slower, but adds virtually no
  slowdown during the work with FreeCAD, no matter the size of a Render
  project.
* The Render workbench uses the same
  [templates](https://www.freecadweb.org/wiki/Raytracing_Module#Templates)
  logic as the Raytracing workbench, and templates are fully compatible.
  Appleseed templates are created the same way (check the [default
  template](templates/empty.appleseed) for example)

## Supported render engines

At the moment, the following engines are supported:

* [Pov-Ray](https://povray.org/)  
* [LuxCoreRender](https://luxcorerender.org/)
* [Appleseed](https://appleseedhq.net) 
* [Blender Cycles](https://www.cycles-renderer.org/)
* LuxRender (deprecated in favor of LuxCoreRender)

## Installation

The Render workbench is part of the [FreeCAD Addons
repository](https://github.com/FreeCAD/FreeCAD-addons), and can be installed
from menu `Tools > Addon Manager` in FreeCAD. This is the recommended
installation method.  However, it can also be installed manually by downloading
this repository using the "clone or download" button above. Refer to the
[FreeCAD
documentation](https://www.freecadweb.org/wiki/How_to_install_additional_workbenches)
to learn more.

In addition to workbench installation, you will also need to [install and set
up](./docs/EngineInstall.md) one or more external render engines, among the
supported ones.

## Usage

For a quick-start, rendering a FreeCAD model is just a 3-step process:
1. **Create a rendering project:** Press the button in the toolbar
   corresponding to your renderer (<img src=./icons/Appleseed.svg height=32>
   <img src=./icons/Cycles.svg height=32> <img src=./icons/Luxcore.svg
   height=32> <img src=./icons/Povray.svg height=32>) 
2. **Add views of your objects to the project:** Select both the objects and
   the project, and press the 'Add view' button (<img
   src=./icons/RenderView.svg height=32>)
3. **Render:** Press Render button (<img src=./icons/Render.svg height=32>),
   also available in project's contextual menu.

That's all!

Optionally, you can tweak some particulars of your scene:
* Modify some [options of your rendering project](./docs/Projects.md)
* Add [lights](./docs/Lights.md) to your scene
* Add extra [cameras](./docs/Cameras.md)
* Add [materials](./docs/Materials.md) to your objects These adjustments take
  place between steps 2 and 3.

## Alternatives

### Using Blender

Instead of exporting to a renderer, you can also import your FreeCAD model to
Blender.  Blender is able to import FreeCAD files with materials correctly
imported and ready for Cycles too, by installing the FreeCAD importer addon
(available for
[2.80](https://gist.github.com/yorikvanhavre/680156f59e2b42df8f5f5391cae2660b)
and
[2.79](https://gist.github.com/yorikvanhavre/e873d51c8f0e307e333fe595c429ba87)).
Importing your FreeCAD file in Blender before rendering gives you more options
such as placing textures.


## Contributing

Any contributions are welcome! Feel free to post PR to this project.

### Code of Conduct

This project is covered by FreeCAD 
[Code of Conduct](https://github.com/FreeCAD/FreeCAD/blob/master/CODE_OF_CONDUCT.md).

### To Do (not exhaustive)

* Add some more lighting functionalities:
  - Spot lights
  - Directional lights
* Add UV-textures to material support
* Currently the external (open the file to be rendered in the Renderer's
  GUI)/internal (render directly inside FreeCAD) render mode is not
  implemented, the external mode will always be used.
* Add support for more renderers
  - Yafaray
  - OpenCasCade's [CadRays](https://www.opencascade.com/content/cadrays) 
  - Kerkythea (adapt the existing macro)
  - Blender's Eevee

### Notes on Code Quality

In order to make this module easy to read, maintain and extend by everyone, we
strive to sustain a good level of code quality.  In particular, we try to
ensure that the code complies with PEP8 / PEP257. Therefore,
* If you post contributions (thank you very much!), please enforce PEP8 /
  PEP257 on your production, and run pylint and flake8 before sending PR. A
  specific pylintrc file, with general PEP8 rules and some specific tweaks
  related to FreeCAD framework, is provided for that purpose in the project
  directory.
* If you see anything that could be improved in terms of code quality (PEP
  compliance, pythonicity, coding best practices...), or simply readability
  (comments, documentation...), do not hesitate to post propositions!


## Feedback

For feedback, bugs, feature requests, and further discussion please use the
dedicated FreeCAD [forum thread]()

## Author Yorik Van Havre AKA
[@yorikvanhavre](https://github.com/yorikvanhavre)
([blog](https://yorik.uncreated.net/))
