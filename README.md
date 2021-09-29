# FreeCAD Render Workbench

[![FreeCAD Addokn manager status](https://img.shields.io/badge/FreeCAD%20addon%20manager-available-brightgreen)](https://github.com/FreeCAD/FreeCAD-addons) [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/FreeCAD/FreeCAD-render.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/FreeCAD/FreeCAD-render/context:python)

A [FreeCAD](https://www.freecadweb.org) workbench to produce high-quality
rendered images from your FreeCAD document, using open-source external
rendering engines.

<img src=./docs/freecad-june-09.jpg alt="ShowCase" title="Examples of rendering
made with Render Workbench">

## Introduction

The Render Workbench is a replacement for the built-in [Raytracing
Workbench](https://www.freecadweb.org/wiki/Raytracing_Module) of FreeCAD. It is
based on the same philosophy, but aims to improve certain aspects of
Raytracing:

* The Render Workbench is written fully in Python, which should make it much
  easier to understand and extend by non-C++ programmers.
* Exporters to rendering engines are implemented as plugins, which should
  facilitate the addition of new engines. The Render Workbench already supports several more
  renderers than Raytracing Workbench, like Appleseed, LuxCoreRender and Cycles.
* The Render Workbench provides enhanced features, compared to Raytracing:
  scene lighting, camera enhanced control, material support etc.

## Supported rendering engines

At the moment, the following rendering engines are supported:

* [Pov-Ray](https://povray.org/)  
* [LuxCoreRender](https://luxcorerender.org/)
* [Appleseed](https://appleseedhq.net) 
* [Blender Cycles](https://www.cycles-renderer.org/)
* [Intel Ospray Studio](https://github.com/ospray/ospray_studio) (experimental)
* [Pbrt v4](https://github.com/mmp/pbrt-v4) (experimental)
* LuxRender (deprecated in favor of LuxCoreRender)

## Installation

The Render Workbench is part of the [FreeCAD Addons
repository](https://github.com/FreeCAD/FreeCAD-addons), and thus can be
installed from menu `Tools > Addon Manager` in FreeCAD. This is the recommended
installation method.<br /> However, alternatively, it can also be installed
manually by downloading this repository using the "clone or download" button
above. Refer to [FreeCAD
documentation](https://www.freecadweb.org/wiki/How_to_install_additional_workbenches)
to learn more.

In addition to workbench installation, you will also need to [install and set
up](./docs/EngineInstall.md) one or more external render engines, among the
supported ones.

## Usage

In quick-start mode, after installation has correctly be done, rendering a
FreeCAD model is just a 4-steps process:
1. **Create a rendering project:** Press the button in the toolbar
   corresponding to your renderer <img src=./Render/resources/icons/Appleseed.svg height=32>
   <img src=./Render/resources/icons/Cycles.svg height=32> <img src=./Render/resources/icons/Luxcore.svg
   height=32> <img src=./Render/resources/icons/Povray.svg height=32> and select a template
   suitable for your renderer \ (you may start with a 'standard' flavour, like
   appleseed_standard.appleseed, cycles_standard.xml, luxcore_standard.cfg or
   povray_standard.pov) 
2. **Add views of your objects to your rendering project:** Select both the
   objects and the project, and press the 'Add view' button <img
   src=./Render/resources/icons/RenderView.svg height=32>
3. **Set your point of view:** [Navigate in FreeCAD 3D View](https://wiki.freecadweb.org/Manual:Navigating_in_the_3D_view)
   to the desired position and switch to _Perspective_ mode.
4. **Render:** Select your project and press the 'Render' button <img
   src=./Render/resources/icons/Render.svg height=32> in toolbar (also available in project's
   context menu).

<br /> **...and you should get a first rendering of your model.** <br /> 


Optionally, you may tweak some particulars of your scene:
* Modify some [options of your rendering project](./docs/Projects.md)
* Add [lights](./docs/Lights.md) to your scene
* Add extra [cameras](./docs/Cameras.md)
* Add [materials](./docs/Materials.md) to your objects

These adjustments should take place between steps 2 and 3.

## Alternative - Importing in Blender

The Render Workbench's philosophy is to export a FreeCAD model to a file in the
format of a rendering engine and run the rendering engine on that file.

Instead of that, you can also *import* your FreeCAD model into Blender and run a
rendering engine from inside Blender.  Blender is able to import FreeCAD files
with materials correctly placed and ready for Cycles too, by using the FreeCAD
importer Blender addon (available for
[2.80](https://gist.github.com/yorikvanhavre/680156f59e2b42df8f5f5391cae2660b)
and
[2.79](https://gist.github.com/yorikvanhavre/e873d51c8f0e307e333fe595c429ba87)).

Importing your FreeCAD file in Blender before rendering provides you with many
options, such as placing textures, using other renderers than those supported
by the Render Workbench, or more generally using all the powerful features of
Blender.

As a counterpart, all additions made in Blender after importing may be lost if
you need to reimport your FreeCAD file later (for instance, in the event that
your FreeCAD model has been modified...). That is why we would recommend to use
the Render Workbench if the provided features are sufficient for your needs.

## Contributing

Any contributions are welcome! Please read our
[Contributing](./docs/Contributing.md) guidelines beforehand.

## Feedback

For feedback, bugs, feature requests, and further discussion please use a
dedicated FreeCAD forum thread, or open an issue in this Github repo.

## Code of Conduct

This project is covered by FreeCAD [Code of
Conduct](https://github.com/FreeCAD/FreeCAD/blob/master/CODE_OF_CONDUCT.md).
Please comply to this code in all your contributions (issue openings, pull
requests...).

## Author

Yorik Van Havre AKA [@yorikvanhavre](https://github.com/yorikvanhavre)
([blog](https://yorik.uncreated.net/))
