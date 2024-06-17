# Plugins

## What are Plugins in Render WB?
Render Plugins are a convenient way of adding extra functionalities to Render WB that would
require dependencies present neither in the FreeCAD package nor in system-level modules.

Practically speaking, plugins are **small applets** written in Python that can be run as **separate subprocesses in a dedicated Python environment**,
while being **embedded in FreeCAD Gui** and being able to interact with FreeCAD. Render workbench provides plugins a virtual environment (https://docs.python.org/3/library/venv.html) where various additional packages can be installed from PyPi, in addition to those accessible at system-level.
Examples of installed packages include - but are not restricted to - PySide6 addons (QWebEngine), MaterialX...

The major benefit of that virtual environment is that, being hosted in the user directory, it allows installing new dependencies (or deleting old ones)
_without elevation of rights_.

At the moment, plugins are designed as a single-window Qt-based application, with a central widget. The customizable part of the plugin is the central widget.

## How do Plugins work?
Plugins are run by `subcontainer.py`. They are launched as subprocesses and are provided a framework
containing a set of features to interact with Render & FreeCAD. 
The framework is hosted in the virtual environment, so that it can simply be imported in the plugin.

Plugins can interact with Render / FreeCAD in two ways:
* stdout, which is piped to FreeCAD console (log level).
* a bidirectional socket, based on localhost or named pipes, according to OS 
Both ways are provided by framework.

The socket is a particularly flexible tool, enabling the transmission of multiple types of information:
- application messages
- user messages (log, warn, error...)
- serialized objects
in both directions: Workbench -> Plugin and Plugin -> Workbench. 
 
## How to write a Plugin?
Applet side:
Create a Python file in `Render/plugins` folder.
In this file:
* import `plugin_framework`
* create a widget class corresponding to your target application - here comes all the customization
* instantiate `plugin_framework.RenderPluginApplication`, passing it the widget class
* call the `exec` method of the above instance

Workbench side:
* In `subcontainer.py`, add a `start_xxx` method based on an existing one.
* In `virtualenv.py`, add any additional required modules in "Step 5".
Remark: I'm aware that this way of doing things is a bit manual, but I'm not sure it would be worth packaging a complete API.
