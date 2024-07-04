# MaterialX plugin

MaterialX plugin allows to import Physically Based Rendering materials in
MaterialX format into Render projects.

The plugin is able to get MaterialX files from various sources: websites, local
directories etc. and transform them into FCMat files, ready to be imported.
It can also trigger the import via minimalistic interprocess communication.

The plugin is based on broader dependencies than those provided by FreeCAD (for
instance, QWebEngine*). These dependencies are provided by a Python virtual
environment.

# License
MaterialX plugin is licensed under the terms of **GNU General Public License version 3**
or any later, at your option.

A special effort has been made and will be continued to ensure that this plugin
and the workbench are not considered as a single combined program.
( https://www.gnu.org/licenses/gpl-faq.en.html#GPLPlugins)

In particular:
- The plugin is launched by the workbench via fork and exec. No linking occurs
  between plugin and workbench -  neither dynamic nor static. No shared memory
  is used.
- No back and forth complex data structures shipping occurs, as no object is
  sent from workbench to plugin. Exchanges between plugin and workbench are
  limited to the providing of a file in FCMat format by the plugin, to be
  imported by the workbench via FreeCAD's standard API.
