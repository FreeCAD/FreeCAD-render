# Plugins

## What are Plugins in Render WB?
Render Plugins are a convenient way of adding extra functionalities to Render
WB that would require dependencies present neither in the FreeCAD package nor
in system-level modules.

Practically speaking, plugins are **small programs** written in Python that can
be run as **separate subprocesses in a dedicated Python virtual environment**
(fork/exec), while being **embedded in FreeCAD Gui** providing some
(minimalistic) ability to interact with Render. Render workbench provides
plugins a dedicated virtual environment
(https://docs.python.org/3/library/venv.html) where various additional packages
can be installed from PyPi, in addition to those accessible at system-level.
Examples of installed packages include Qt addons (QWebEngine), MaterialX... but
are not restricted to and can be extended.

The major benefit of that virtual environment is that, being hosted in the user
directory, it allows new dependencies to be installed and updated _without
elevation of rights_, and thus in a way that is totally transparent to the
user.

At the moment, plugins are designed as a single-window Qt-based application,
with a central widget. The customizable part of the plugin is the central
widget. In the future, this could be extended to headless applications,
GTK-based apps etc. (but there is no plan for that in the short term).

## How do Plugins work?
Plugins are run by `subcontainer.py`. They are launched as subprocesses and are
provided a framework containing a set of features to interact with Render &
FreeCAD. The framework is hosted in the virtual environment, so that it can
simply be imported in the plugin, like any Python module.

The framework takes care of:
* keeping the virtual environment available and up-to-date
* embedding plugin's main window into FreeCAD Gui
* establishing the means for Plugin / Render communication.

Plugins can interact with Render / FreeCAD in two ways:
* stdout, which is piped to FreeCAD console (log level).
* a bidirectional socket, based on localhost or named pipes, according to OS.
  Both ways are provided by framework.

The socket enables the transmission of multiple types of information:
- application messages
- user messages (log, warn, error...)
- serialized objects
in both directions: Workbench -> Plugin and Plugin -> Workbench.

## How to write a Plugin?
Plugin side:
Create a directory in `Render/plugins` folder and, in this directory, provide a
`__main__.py`
In this file:
* import `renderplugin`
* create a widget class corresponding to your target application - here comes all the customization
* instantiate `renderplugin.RenderPluginApplication`, passing it your widget class and your parameters
* call the `exec` method of the above instance

Workbench side:
* In `subcontainer.py`, add a `start_xxx` method based on an existing one.
* In `virtualenv.py`, add any additional required modules in "Step 5".

## License
Please note that plugins, as separate programs, can be licensed under different
terms that Render Workbench.
