# Install and set up external rendering engines


## General indications

In order to have Render workbench fully functional, you must give it access to one
or more external rendering engines. To achieve that, you must follow a 2-step process:
1. Install the rendering engine(s) on your system.
2. Set up this/these external rendering engine(s) in Render workbench.

### Install external rendering engines on your system

To use Render Workbench, you must first install one of the supported rendering
engines on your system.

At the moment, the following engines are supported:

* [Pov-Ray](https://www.povray.org/)
* [LuxCoreRender](https://luxcorerender.org/)
* [Appleseed](https://appleseedhq.net)
* [Blender Cycles](https://www.cycles-renderer.org/)
* [Intel Ospray Studio](http://www.ospray.org/ospray_studio)
* [Pbrt v4](https://www.pbrt.org) (experimental)

The precise installation procedure for each of those engines should be first
searched on their respective websites.
However, you will find below some indications for a few platforms.

After installing, it is recommended to make sure your rendering engine is fully
functional: test scenes are usually provided with the renderer for that
purpose, please refer to its documentation.


### Set up external rendering engines in the workbench

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


## Per-platform indications

### Ubuntu

#### Povray
<ins>Install</ins><br>
Povray is in the repo, so just do it the simple way:
`sudo apt install povray`

<ins>Set up</ins><br>
In workbench settings, enter `/usr/bin/povray` in 'PovRay executable path'.

#### LuxCoreRender - UI only
*Caveat: this install is easier (and lighter), but you won't be able to run
Luxcorerender in batch mode*
 
<ins>Install</ins><br>
Download Luxcore binaries package from website, with this link:
[Standalone release v2.6](https://github.com/LuxCoreRender/LuxCore/releases/download/luxcorerender_v2.6/luxcorerender-v2.6-linux64.tar.bz2)

Choose a target directory for the application. Let's call it `<appdir>`.

Unzip the downloaded package file into `<appdir>`

<ins>Set up</ins><br>
In workbench settings:
- Leave 'LuxCore command (cli) path' blank.
- Enter `<appdir>/LuxCore/luxcoreui` in 'LuxCore UI path'


#### LuxCoreRender - Full (UI & batch)

<ins>Install</ins><br>
Download Luxcore binaries package from website, with this link:
[LuxCore API SDK release v2.6](https://github.com/LuxCoreRender/LuxCore/releases/download/luxcorerender_v2.6/luxcorerender-v2.6-linux64-sdk.tar.bz2)


Choose a target directory for the application. We'll call it `<appdir>`.

Unzip the downloaded package file into `<appdir>`

Copy all the files in `<appdir>/LuxCore-sdk/lib/` to `<appdir>/LuxCore-sdk/bin/`.
*Very important:* If you miss this step, you'll get some fatal "cannot open shared object file: No such file or directory" messages...

<ins>Set up</ins><br>
In workbench settings:
- Enter `<appdir>/LuxCore-sdk/bin/luxcoreconsole` in 'LuxCore command (cli) path'
- Enter `<appdir>/LuxCore-sdk/bin/luxcoreui` in 'LuxCore UI path'


#### Appleseed

<ins>Install</ins><br>
Download Appleseed binaries package from website, with this link:
[Appleseed for Linux](https://github.com/appleseedhq/appleseed/releases/download/2.1.0-beta/appleseed-2.1.0-beta-0-g015adb503-linux64-gcc74.zip)

Choose a target directory for the application. We'll call it `<appdir>`.

Unzip the downloaded package file into `<appdir>`

Install Python 2.7 library
`sudo apt install libpython2.7`
*(Very important)* 

<ins>Set up</ins><br>
In workbench settings:
- Enter `<appdir>/appleseed/bin/appleseed.cli` in 'Appleseed command (cli) path'
- Enter `<appdir>/appleseed/bin/appleseed.studio` in 'Appleseed Studio path'


#### Ospray Studio

<ins>Install</ins><br>
Download Ospray Studio binaries package from website, with this link:
[Ospray Studio for Linux](https://github.com/ospray/ospray_studio/releases/download/v0.12.1/ospray_studio-0.12.1.x86_64.linux.tar.gz)

Choose a target directory for the application. We'll call it `<appdir>`.

Unzip the downloaded file into `<appdir>`

<ins>Set up</ins><br>
In workbench settings:
- Enter `<appdir>/ospray_studio-0.12.1.x86_64.linux/bin/ospStudio` in 'OspStudio executable path'

#### Cycles standalone
Cycles standalone has to be compiled from sources. See https://github.com/blender/cycles

Warning: Installing Cycles standalone from sources can be tricky and time-consuming, see below. You'll be warned...


#### Pbrt
Pbrt has to be compiled from sources. See https://github.com/mmp/pbrt-v4


### Archlinux

In Archlinux, all renderers have been packaged, either in official repositories or in AUR.

There is just a point of attention: for a given renderer, it can exist several packages in AUR (version, -git etc.)
and not all will fit correctly.
The following array gathers the recommended packages and the corresponding workbench settings:

| Renderer      | Repo          | Package               | Workbench Settings||
| ---           | ---           | ---                   | ---| --- |
| Povray  	| Official  	| `povray`  		| PovRay executable path:                                   | `/usr/bin/povray`				| 
| LuxCore  	| AUR  		| `luxcorerender` 	| LuxCore command (cli) path: <br> LuxCore UI path: | `/usr/bin/luxcoreconsole` <br> `/usr/bin/luxcoreui` |
| Appleseed  	| AUR  		| `appleseed-git`  	| Appleseed command (cli) path: <br /> Appleseed Studio path: | `/usr/bin/appleseed.cli` <br /> `/usr/bin/appleseed.studio`|
| Ospray  	| AUR  		| `ospray-studio`  	| OspStudio executable path: | `/usr/bin/ospStudio` |
| Cycles  	| AUR  		| `cycles-standalone`	| Cycles executable path: | `/usr/bin/cycles`|
| Pbrt  	| AUR  		| `pbrt-v4-git`   	| Pbrt executable path: | `/usr/bin/pbrt`|


### Windows

#### Povray

<ins>Install</ins><br>
Download Povray 3.7 installer: https://www.povray.org/ftp/pub/povray/Official/povwin-3.7-agpl3-setup.exe

Run Povray installer.


<ins>Set up</ins><br>
Look for `pvengine64.exe` on your system. In Render settings, fill 'PovRay executable path' with `<path/to/pvengine64.exe>`

#### LuxCoreRender

<ins>Install</ins><br>
Download Luxcore binaries package from website, with this link:
[LuxCore API SDK release v2.6](https://github.com/LuxCoreRender/LuxCore/releases/download/luxcorerender_v2.6/luxcorerender-v2.6-win64-sdk.zip)

Choose a target directory for the application. We'll call it `<appdir>`.

Unzip the downloaded package file into `<appdir>`

As stated in Download page (https://luxcorerender.org/download/):<br>
<q>All Windows executables require the Visual C++ Redistributable Packages for
VS 2017 and Intel C++ redistributable.</q><br>
Please check your system meets those requirements, or update it accordingly.

<ins>Set up</ins><br>
In workbench settings:
- Enter `<appdir>/luxcorerender-v2.6-win64-sdk/bin/luxcoreconsole.exe` in 'LuxCore command (cli) path'
- Enter `<appdir>/luxcorerender-v2.6-win64-sdk/bin/luxcoreui.exe` in 'LuxCore UI path'


#### Appleseed

<ins>Install</ins><br>
Download Appleseed binaries package from website, with this link:
[Appleseed for Windows](https://github.com/appleseedhq/appleseed/releases/download/2.1.0-beta/appleseed-2.1.0-beta-0-g015adb503-win64-vc141.zip)

Choose a target directory for the application. We'll call it `<appdir>`.

Unzip the downloaded package file into `<appdir>`

<ins>Set up</ins><br>
In workbench settings:
- Enter `<appdir>/appleseed/bin/appleseed.cli.exe` in 'Appleseed command (cli) path'
- Enter `<appdir>/appleseed/bin/appleseed.studio.exe` in 'Appleseed Studio path'

#### Ospray Studio
<ins>Install</ins><br>
Download Ospray Studio installer: https://github.com/ospray/ospray_studio/releases/download/v0.12.1/ospray_studio-0.12.1.x86_64.windows.msi

Run Ospray Installer

<ins>Set up</ins><br>
Look for `ospStudio.exe` on your system. In Render settings, fill 'OspStudio executable path' with `<path/to/ospStudio.exe>`

#### Cycles standalone
In general case, Cycles standalone has to be compiled from sources, from here: https://github.com/blender/cycles <br>
However, compiling Cycles standalone from sources can be tricky and time-consuming, see below. <br>
Fortunately, users @MisterMakerNL and @metalex201 provide precompiled versions: 
https://github.com/MisterMakerNL/Cycles-stand-alone-windows-build. [1.13.4]
https://github.com/metalex201/Cycles-standalone-windows-build. [4.0.0]


#### Pbrt
Pbrt has to be compiled from sources. See https://github.com/mmp/pbrt-v4


## Miscellaneous

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

### Bugs & Errors

All the indications above rely on external information that can vary.

Please do not hesitate to open an issue to report errors, dead links, out-of-date information, questions and so on.

