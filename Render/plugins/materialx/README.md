# MaterialX plugin

MaterialX plugin allows to import Physically Based Rendering materials in
MaterialX format into Render projects.

The plugin is able to get the MaterialX files from various sources: websites,
local directories etc.

This plugin is designed as an independant program that can be launched
separately from Render. In this case, the plugin output is a FCMat file,
that can subsequently be imported into FreeCAD.

The usual way to use it, however, is to run it from Render virtual environment
and embed it into FreeCAD Gui, via subcontainer.py.

The plugin is based on broader dependencies than those provided by FreeCAD (for
instance, QWebEngine*). These dependencies are provided by Render virtual
environment.

# License
Help plugin is licensed under the terms of **GNU General Public License version 3**
or any later.
