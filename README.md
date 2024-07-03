# FreeCAD Render Workbench

[![FreeCAD Addon manager status](https://img.shields.io/badge/FreeCAD%20addon%20manager-available-brightgreen)](https://github.com/FreeCAD/FreeCAD-addons)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)

A [FreeCAD](https://www.freecadweb.org) workbench to produce high-quality
rendered images from your FreeCAD document, using open-source external
rendering engines.

<img src=./docs/freecad-june-09.jpg alt="ShowCase" title="Examples of rendering
made with Render Workbench" width="800">

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
    - various scene lighting features (point lights, area lights, sunsky etc.)
      and preconfigured lightings as templates
    - camera enhanced control
    - material support
    - texture support
    - renderers' advanced features handling: denoising, batch mode
  etc.

## Supported rendering engines

At the moment, the following rendering engines are supported:

* [Pov-Ray](https://www.povray.org/)
* [LuxCoreRender](https://luxcorerender.org/)
* [Appleseed](https://appleseedhq.net)
* [Blender Cycles](https://www.cycles-renderer.org/) ( [standalone](https://github.com/blender/cycles) )
* [Intel Ospray Studio](http://www.ospray.org/ospray_studio)
* [Pbrt v4](https://www.pbrt.org) (experimental)
* LuxRender (deprecated in favor of LuxCoreRender)

## Installation
### Workbench
The Render Workbench is part of the [FreeCAD Addons
repository](https://github.com/FreeCAD/FreeCAD-addons), and thus can be
installed from menu `Tools > Addon Manager` in FreeCAD. This is the recommended
installation method.<br /> However, alternatively, it can also be installed
manually by downloading this repository using the "clone or download" button
above. Refer to [FreeCAD
documentation](https://www.freecadweb.org/wiki/How_to_install_additional_workbenches)
to learn more.

### External rendering engines
In addition to workbench installation, you will also need to [install and set
up](./docs/EngineInstall.md) one or more external rendering engines, among the
supported ones.

## Usage

In quick-start mode, after installation has correctly been done, rendering a
FreeCAD model is just a 4-steps process:
1. **Create a rendering project:** Press the button in the toolbar
   corresponding to your renderer <img src=./Render/resources/icons/Appleseed.svg height=32>
   <img src=./Render/resources/icons/Cycles.svg height=32> <img src=./Render/resources/icons/Luxcore.svg
   height=32> <img src=./Render/resources/icons/Povray.svg height=32> and select a template
   suitable for your renderer \
   (you may start with a 'studio' flavour, like
   appleseed_studio_light.appleseed, cycles_studio_light.xml, luxcore_studio_light.cfg or
   povray_studio_light.pov)


2. **Add views of your objects to your rendering project:** Select both the
   objects and the project, and press the 'Add view' button <img
   src=./Render/resources/icons/RenderView.svg height=32>


3. **Set your point of view:**
[Navigate in FreeCAD 3D View](https://wiki.freecadweb.org/Manual:Navigating_in_the_3D_view)
   to the desired position and switch to _Perspective_ mode.


4. **Render:** Select your project and press the 'Render' button <img
   src=./Render/resources/icons/Render.svg height=32> in toolbar (also available in project's
   context menu).


<br /> **...and you should get a first rendering of your model.** <br />


You may also find a short tutorial on how to get started here:
https://www.youtube.com/watch?v=8wsOnwjKG9M


## More features

Optionally, you may tweak some particulars of your scene:
* Modify some [options of your rendering project](./docs/Projects.md)
* Adjust [the way a particular object is rendered (view options)](./docs/Views.md)
* Add [lights](./docs/Lights.md) to your scene
* Add extra [cameras](./docs/Cameras.md)
* Add [materials](./docs/Materials.md) to your objects
* Add [textures](./docs/Materials.md#textures) to your materials

These adjustments should take place between steps 2 and 3.

## FAQ
### How to solve library conflicts within a FreeCAD AppImage

When using an AppImage, you might be confronted with an error like this on
execution of the "Render" command:

`.../usr/lib/libstdc++.so.6: version 'CXXABI_1.3.15' not found`

This is due to different library versions of your host system and the AppImage.
As a workaround, provide your host libraries to the rendering command using the
"Prefix" field in the Render WB configuration:

`env LD_LIBRARY_PATH="/usr/lib64"`

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

## License

The Render Workbench is licensed under the terms of GNU Lesser General Public
License (GNU LGPL) version 2 or any later version, except plugins `help` and
`materialx` (located in [Render/plugins](./Render/plugins) directory), that are
licensed under the terms of GNU General Public License (GNU GPL) version 3 or
any later version. See [COPYING](./COPYING) file for more information.
