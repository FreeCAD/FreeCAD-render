# Help plugin

Help plugin shows help on FreeCAD features.

This plugin is designed as an independant program that can be launched
separately from Render. The usual way to use it, however, is to run it from
Render virtual environment and embed it into FreeCAD Gui, via subcontainer.py.

The applet is based on broader dependencies than those provided by FreeCAD (for
instance, QWebEngine*). These dependencies are provided by Render virtual
environment.

# License
Help plugin is licensed under the terms of **GNU General Public License version 3**
or any later, at your option.

A special effort has been made and will be continued to ensure that this plugin
and the workbench are not considered as a single combined program.
( https://www.gnu.org/licenses/gpl-faq.en.html#GPLPlugins)

In particular:
- The plugin is launched by the workbench via fork and exec. No linking occurs
  between plugin and workbench -  neither dynamic nor static. No shared memory
  is used.
- No back and forth complex data structures shipping occurs, as no object is
  exchanged between workbench and plugin.
