# Plugins

## What are Plugins in Render WB?
In Render workbench, Plugins are small applets written in Python that can be run as separate subprocesses, while being embedded in FreeCAD Gui and
being able to interact with FreeCAD.
Render workbench provides plugins a virtual environment (https://docs.python.org/3/library/venv.html) where various additional packages can be installed.
Examples of installed packages include - but are not restricted to - PySide6 addons (QWebEngine), MaterialX...

In short, plug-ins are a convenient way of adding extra functionalities to Render WB that
require dependencies present neither in the FreeCAD package nor in modules installed at system level.

## How do Plugins work?
Plugins are run by 'subcontainer.py'. They are launched as subprocesses. They are provided a framework (hosted in the virtual environment)
with the underlying features. 

Plugins can interact with Render and FreeCAD in two ways:
* a bidirectional socket, based on localhost or named pipes, according to OS 
* piped stdin and stdout

 
