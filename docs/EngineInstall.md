# Install and set up external rendering engines

In order to have Render workbench fully functional, you need to install one or more external rendering engines on your system, and to set up this/these external rendering engine(s) in Render workbench.

## Install external rendering engines on your system

To use Render Workbench, you must first install one of the supported rendering
engines on your system.

At the moment, the following engines are supported:

* [Pov-Ray](https://www.povray.org/)
* [LuxCoreRender](https://luxcorerender.org/)
* [Appleseed](https://appleseedhq.net)
* [Blender Cycles](https://www.cycles-renderer.org/)
* [Intel Ospray Studio](http://www.ospray.org/ospray_studio) (experimental)
* [Pbrt v4](https://www.pbrt.org) (experimental)

The precise installation procedure for each of those engines should be first
searched on their respective websites.
However, you will find below some indications for a few platforms.

You will find below some more information about Cycles
renderer, which is a special case.

After installing, please make sure your rendering engine is fully functional:
test scenes are usually provided with the renderer for that purpose, please
refer to its documentation.


## Set up external rendering engines in the workbench

Once you have a rendering engine installed on your system, you have to set it
up in the workbench.

Each renderer has some configurations to be set in `Edit > Preferences >
Render` before being able to use it.

<img src=./preferences.jpg alt="Preferences" title="Renderers settings">

At least, you must fill in the **path to your renderer executable**, in the
corresponding section. This is a **mandatory** step, otherwise the workbench
will not be able to run the engine when required. Some renderers may provide
two flavours of their engine: a command-line and a GUI; in which case you
should fill in both.

Optionally, you may want to add some command-line parameters (for instance, to
activate GPU rendering, or to specify halt conditions etc.: see your renderer's
documentation) to renderer invocation. In that case, you can use the dedicated
field 'Render parameters' in your renderer section. 

Optionally as well, you can set a few renderer-wide parameters:
* `Prefix`: A prefix that can be added before the renderer executable
  invocation.  This is useful, for example, to add environment variables or run
  the renderer inside a GPU switcher such as primusrun or optirun on Linux.
  This parameter is fully optional and can be left empty if not needed.
* `Default render width`, `default render height`: the default dimensions of
  the rendering output. Default values are 800x600 and can be left as-is if no
  special dimensions are required.

[comment]: # (We should add a small script to test installation...)


### Ubuntu

#### Povray (difficulty: 0/5)
Povray is in the repo, so just do it the simple way:
`sudo apt install povray`

In workbench settings, enter `/usr/bin/povray` in 'PovRay executable path'.

#### LuxCoreRender - UI only (difficulty: 1/5)
*Caveat: with this install, you won't be able to run Luxcorerender in batch mode*
 
Download Luxcore binaries package from website, with this link:
[Standalone release v2.6](https://github.com/LuxCoreRender/LuxCore/releases/download/luxcorerender_v2.6/luxcorerender-v2.6-linux64.tar.bz2)

Choose a target directory for the application. Let's call it `<appdir>`.

Uncompress the downloaded file to `<appdir>`

In workbench settings:
- Leave 'LuxCore command (cli) path' blank.
- Enter `<appdir>/LuxCore/luxcoreui` in 'LuxCore UI path'


#### LuxCoreRender - UI & batch mode (difficulty: 2/5)

Download Luxcore binaries package from website, with this link:
[LuxCore API SDK release v2.6](https://github.com/LuxCoreRender/LuxCore/releases/download/luxcorerender_v2.6/luxcorerender-v2.6-linux64-sdk.tar.bz2)


Choose a target directory for the application. We'll call it `<appdir>`.

Uncompress the downloaded file to `<appdir>`

Copy all the files in `<appdir>/LuxCore-sdk/lib/` to `<appdir>/LuxCore-sdk/bin/`.
*Very important:* If you miss this step, you'll get to some fatal "cannot open shared object file: No such file or directory" messages...

In workbench settings:
- Enter `<appdir>/LuxCore-sdk/bin/luxcoreconsole` in `LuxCore command (cli) path`
- Enter `<appdir>/LuxCore-sdk/bin/luxcoreui` in 'LuxCore UI path'


#### Appleseed (difficulty: 1/5)

Download Appleseed binaries package from website, with this link:
[Appleseed for linux](https://github.com/appleseedhq/appleseed/releases/download/2.1.0-beta/appleseed-2.1.0-beta-0-g015adb503-linux64-gcc74.zip)

Choose a target directory for the application. We'll call it `<appdir>`.

Uncompress the downloaded file to `<appdir>`

Install Python 2.7 library
`sudo apt install libpython2.7`
*(Very important)* 

In workbench settings:
- Enter `<appdir>/appleseed/bin/appleseed.cli` in `Appleseed command (cli) path`
- Enter `<appdir>/appleseed/bin/appleseed.studi` in 'Appleseed Studio path'


#### Ospray Studio (difficulty: 1/5)

Download Ospray Studio binaries package from website, with this link:
[Ospray Studio for Linux](https://github.com/ospray/ospray_studio/releases/download/v0.12.1/ospray_studio-0.12.1.x86_64.linux.tar.gz)

Choose a target directory for the application. We'll call it `<appdir>`.

Uncompress the downloaded file to `<appdir>`

In workbench settings:
- Enter `<appdir>/ospray_studio-0.12.1.x86_64.linux/bin/ospStudio" in 'OspStudio executable path'

#### Cycles standalone (difficulty: 5/5)
Cycles standalone has to be compiled from sources. See https://github.com/blender/cycles
Installing Cycles standalone can be tricky and time-consuming, especially with GPU support. You'll be warned...


#### Pbrt (difficulty: 4/5)
Pbrt has to be compiled from sources. See https://github.com/mmp/pbrt-v4


### Notes on installing Cycles for Render (standalone version)

*Caveat: Installing Cycles Standalone can be tricky and time-consuming —
especially on Microsoft Windows platform. If you have no taste for poorly
documented installation procedures or if you have no time to waste, you
should rather consider using Appleseed or LuxCoreRender, which both provide
ready-to-use binaries, along with excellent rendering features.*

To use Cycles renderer with Render workbench, you need a standalone version of
Cycles, named *Cycles Standalone*. This version is distinct from the one
embedded in Blender. You will find some more information about *Cycles
Standalone* in the dedicated Blender [wiki
page](https://wiki.blender.org/wiki/Source/Render/Cycles/Standalone).

*Cycles Standalone* usually requires compilation from sources, as no
precompiled binaries are generally available in standard environments. Sources
and compilation instructions can be found
[here](https://projects.blender.org/blender/cycles/src/branch/main/BUILDING.md).

As an alternative, in the (fairly rare) case you already compile Blender by
yourself, you can enable `WITH_CYCLES_STANDALONE` and
`WITH_CYCLES_STANDALONE_GUI` in cmake variables (I also had to add `-lGLU` to
`CMAKE_EXE_LINKER_FLAGS`) before your build process. You will then get a
separate 'cycles' executable compiled together with Blender.

Arch Linux users may avoid all this hassle by using the [package](https://aur.archlinux.org/packages/cycles-standalone/)
available in AUR.

Mac OS Big Sur users may also find some valuable instructions [here](https://vectronic.io/posts/building-freecad-on-macos-big-sur/#install-cycles-standalone).

