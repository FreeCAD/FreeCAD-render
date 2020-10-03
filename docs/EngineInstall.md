# Install and set up external rendering engines

In order to have Render workbench fully functional, you have to go through 2
steps:
* Install one or more external rendering engines on your system;
* Set up external rendering engines in Render workbench.

## Install external rendering engines on your system

To use Render Workbench, you must first install one of the supported rendering
engines on your system.

At the moment, the following engines are supported:

* [Pov-Ray](https://povray.org/)  
* [LuxCoreRender](https://luxcorerender.org/)
* [Appleseed](https://appleseedhq.net) 
* [Blender Cycles](https://www.cycles-renderer.org/)

The precise installation procedure for each of those engines is beyond the
scope of this manual, but detailed installation instructions (adapted to your
OS, your distro etc.) can be found on their respective websites. For Linux
users, you may also usually find on-the-shelf packages in your distribution
repository.

As an exception, you will find below some more information about Cycles
renderer, which is a special case.

After installing, please make sure your rendering engine is fully functional:
test scenes are usually provided with the renderer for that purpose, please
refer to its documentation.

### Notes on installing Cycles for Render (standalone version)

To use Cycles renderer with Render workbench, you need a standalone version of
Cycles, named *Cycles Standalone*. This version is distinct from the one
embedded in Blender. You will find some more information about this version
[here](https://wiki.blender.org/wiki/Source/Render/Cycles/Standalone).

*Cycles Standalone* usually requires compilation from sources, as no
precompiled binaries are generally available in standard environments. Sources
and compilation instructions can be found
[here](https://developer.blender.org/diffusion/C/).

If you already compile Blender by yourself, an alternative is to enable
`WITH_CYCLES_STANDALONE` and `WITH_CYCLES_STANDALONE_GUI` cmake variables (I
also had to add `-lGLU` to `CMAKE_EXE_LINKER_FLAGS`) and you will get a
separate 'cycles' executable compiled together with Blender.

## Set up external rendering engines in the workbench

Once you have a rendering engine installed on your system, you need to set it
up in the workbench.

Each renderer has some configurations to be set in `Edit > Preferences >
Render` before being able to use it.

<img src=./preferences.jpg alt="Preferences" title="Renderers settings">

At least, you must fill in the **path to your renderer executable**, in the
corresponding section. This is a **mandatory** step, otherwise the workbench
will not be able to run the engine when required. Some renderers may provide a
command-line and a GUI flavours of their engine, in which case you should fill
in both.

Optionally, you may want to add some command-line parameters (for instance, to
activate GPU rendering, or to specify halt conditions etc.: see your renderer's
documentation). In that case, you can use the dedicated field 'Render
parameters' in your renderer section. 

Optionally as well, you can set a few renderer-wide parameters:
* `Prefix`: A prefix that can be added before the renderer executable
  invocation.  This is useful, for example, to add environment variables or run
  the renderer inside a GPU switcher such as primusrun or optirun on Linux.
  This parameter is fully optional and can be left empty if not needed.
* `Default render width`, `default render height`: the default dimensions of
  the rendering output. Default values are 800x600 and can be left as-is if no
  special dimensions are required.
