# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************


"""This is Render workbench main module.

It provides the necessary objects to deal with rendering:
- GUI Commands
- Rendering Projects and Views

On initialization, this module will retrieve all renderer modules and create
the necessary UI controls.
"""


# ===========================================================================
#                                   Imports
# ===========================================================================


import sys
import os
import re
import math
import itertools as it
from tempfile import mkstemp
from types import SimpleNamespace
from operator import attrgetter

from PySide.QtGui import (QAction, QIcon, QFileDialog, QLineEdit,
                          QDoubleValidator, QPushButton, QColorDialog, QPixmap,
                          QColor, QFormLayout, QComboBox, QLayout, QListWidget,
                          QListWidgetItem, QListView, QPlainTextEdit,
                          QMessageBox, QInputDialog)
from PySide.QtCore import (QT_TRANSLATE_NOOP, QObject, SIGNAL, Qt, QLocale,
                           QSize)
import FreeCAD as App
import FreeCADGui as Gui
from ArchMaterial import _CommandArchMaterial
try:
    import ImageGui
except ImportError:
    pass

from Render.constants import *
from Render.project import *
from Render.utils import translate, str2rgb
from Render.rdrhandler import RendererHandler, RendererNotFoundError
from Render.taskpanels import MaterialSettingsTaskPanel
import Render.materials as materials
import Render.camera as camera
import Render.lights as lights


# ===========================================================================
#                     Core rendering objects (Project and View)
# ===========================================================================


# ===========================================================================
#                               GUI Commands
# ===========================================================================


class RenderProjectCommand:
    """GUI command to create a rendering project."""

    def __init__(self, renderer):
        """Initialize command.

        Args:
            renderer (str) -- a rendering module name
        """
        # renderer must be a valid rendering module name (string)
        self.renderer = str(renderer)

    def GetResources(self):
        """Get command's resources (callback)."""
        rdr = self.renderer
        return {
            "Pixmap": os.path.join(ICONDIR, rdr + ".svg"),
            "MenuText": QT_TRANSLATE_NOOP("RenderProjectCommand",
                                          "%s Project") % rdr,
            "ToolTip": QT_TRANSLATE_NOOP("RenderProjectCommand",
                                         "Create a %s project") % rdr
            }

    def Activated(self):
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        assert self.renderer, "Error: no renderer in command"

        # Get rendering template
        template = user_select_template(self.renderer)
        if not template:
            return

        # Create project
        Project.create(App.ActiveDocument, self.renderer, template)

        App.ActiveDocument.recompute()


class RenderViewCommand:
    """GUI command to create a rendering view of an object in a project.

    The command operates on the selected object(s) and the selected project,
    or the default project.
    """

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "RenderView.svg"),
            "MenuText": QT_TRANSLATE_NOOP("RenderViewCommand",
                                          "Rendering View"),
            "ToolTip": QT_TRANSLATE_NOOP("RenderViewCommand",
                                         "Create a Rendering View of the "
                                         "selected object(s) in the selected "
                                         "project or the default project")
            }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        # First, split selection into objects and projects
        selection = Gui.Selection.getSelection()
        objs, projs = [], []
        for item in selection:
            (projs if RendererHandler.is_project(item) else objs).append(item)

        # Then, get target project.
        # We first look among projects in the selection
        # and, if none, we fall back on active document's projects
        activedoc_projects = filter(RendererHandler.is_project,
                                    App.ActiveDocument.Objects)
        try:
            target_project = next(it.chain(projs, activedoc_projects))
        except StopIteration:
            msg = translate(
                "Render",
                "[Render] Unable to find a valid project in selection "
                "or document") + '\n'
            App.Console.PrintError(msg)
            return

        # Finally, add objects to target project and recompute
        target_project.Proxy.add_views(objs)

        App.ActiveDocument.recompute()


class RenderCommand:
    """GUI command to render a selected Render project."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(ICONDIR, "Render.svg"),
                "MenuText": QT_TRANSLATE_NOOP("RenderCommand", "Render"),
                "ToolTip": QT_TRANSLATE_NOOP("RenderCommand",
                                             "Perform the rendering of a "
                                             "selected project or the default "
                                             "project")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        # Find project
        project = None
        sel = Gui.Selection.getSelection()
        for obj in sel:
            if "Renderer" in obj.PropertiesList:
                project = obj
                break
        if not project:
            for obj in App.ActiveDocument.Objects:
                if "Renderer" in obj.PropertiesList:
                    return

        # Render (and display if required)
        project.Proxy.render()


class CameraCommand:
    """GUI command to create a Camera object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": ":/icons/camera-photo.svg",
                "MenuText": QT_TRANSLATE_NOOP("CameraCommand",
                                              "Camera"),
                "ToolTip": QT_TRANSLATE_NOOP("CameraCommand",
                                             "Create a Camera object from "
                                             "the current camera position")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new camera into the active document.
        """
        camera.Camera.create()


class PointLightCommand:
    """GUI command to create a Point Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(ICONDIR, "PointLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("PointLightCommand",
                                              "Point Light"),
                "ToolTip": QT_TRANSLATE_NOOP("PointLightCommand",
                                             "Create a Point Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new point light into the active document.
        """
        lights.PointLight.create()


class AreaLightCommand:
    """GUI command to create an Area Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(ICONDIR, "AreaLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("AreaLightCommand",
                                              "Area Light"),
                "ToolTip": QT_TRANSLATE_NOOP("AreaLightCommand",
                                             "Create an Area Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new area light into the active document.
        """
        lights.AreaLight.create()


class SunskyLightCommand:
    """GUI command to create an Sunsky Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(ICONDIR, "SunskyLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("SunskyLightCommand",
                                              "Sunsky Light"),
                "ToolTip": QT_TRANSLATE_NOOP("SunskyLightCommand",
                                             "Create a Sunsky Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new sunsky light into the active document.
        """
        lights.SunskyLight.create()


class ImageLightCommand:
    """GUI command to create an Image Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(ICONDIR, "ImageLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("ImageLightCommand",
                                              "Image Light"),
                "ToolTip": QT_TRANSLATE_NOOP("ImageLightCommand",
                                             "Create an Image Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new image light into the active document.
        """
        lights.ImageLight.create()


class MaterialCreatorCommand(_CommandArchMaterial):
    """GUI command to create a material.

    This class is based on Arch 'ArchMaterial' command.
    """

    def GetResources(self):
        """Get command's resources (callback)."""
        res = super().GetResources()
        res["MenuText"] = QT_TRANSLATE_NOOP("MaterialCreatorCommand",
                                            "Create Material")
        res["ToolTip"] = QT_TRANSLATE_NOOP("MaterialCreatorCommand",
                                           "Create a new Material in current"
                                           "document")
        return res


class MaterialRenderSettingsCommand:
    """GUI command to set render settings of a material object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(ICONDIR, "MaterialSettings.svg"),
                "MenuText": QT_TRANSLATE_NOOP("MaterialRenderSettingsCommand",
                                              "Edit Material Render Settings"),
                "ToolTip": QT_TRANSLATE_NOOP("MaterialRenderSettingsCommand",
                                             "Edit rendering parameters of "
                                             "the selected Material")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It opens a dialog to set the rendering parameters of the selected
        material.
        """
        # App.setActiveTransaction("MaterialSettings")
        App.ActiveDocument.openTransaction("MaterialSettings")
        task = MaterialSettingsTaskPanel()
        Gui.Control.showDialog(task)
        # App.closeActiveTransaction()
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()


class MaterialApplierCommand:
    """GUI command to apply a material to an object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(ICONDIR, "ApplyMaterial.svg"),
                "MenuText": QT_TRANSLATE_NOOP("MaterialApplierCommand",
                                              "Apply Material"),
                "ToolTip": QT_TRANSLATE_NOOP("MaterialApplierCommand",
                                             "Apply a Material to selection")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It sets the Material property of the selected object(s).
        If the Material property does not exist in the object(s), it is
        created.
        """
        # Get selected objects
        selection = Gui.Selection.getSelection()
        if not selection:
            title = translate("Render", "Empty Selection")
            msg = translate("Render",
                            "Please select object(s) before applying "
                            "material.")
            QMessageBox.warning(None, title, msg)
            return

        # Let user pick the Material
        mats = [o for o in App.ActiveDocument.Objects
                if o.isDerivedFrom("App::MaterialObjectPython")]
        if not mats:
            title = translate("Render", "No Material")
            msg = translate("Render",
                            "No Material in document. Please create a "
                            "Material before applying.")
            QMessageBox.warning(None, title, msg)
            return
        matlabels = [m.Label for m in mats]
        current_mats_labels = [o.Material.Label for o in selection
                               if hasattr(o, "Material")
                               and hasattr(o.Material, "Label")
                               and o.Material.Label]
        current_mats = [count for count, val in enumerate(matlabels)
                        if val in current_mats_labels]
        current_mat = current_mats[0] if len(current_mats) == 1 else 0

        userinput, status = QInputDialog.getItem(
                None,
                translate("Render", "Material Applier"),
                translate("Render", "Choose Material to apply to selection:"),
                matlabels,
                current_mat,
                False)
        if not status:
            return

        material = next(m for m in mats if m.Label == userinput)

        # Update selected objects
        App.ActiveDocument.openTransaction("MaterialApplier")
        for obj in selection:
            # Add Material property to the object if it hasn't got one
            if "Material" not in obj.PropertiesList:
                obj.addProperty(
                    "App::PropertyLink",
                    "Material",
                    "",
                    QT_TRANSLATE_NOOP(
                        "App::Property",
                        "The Material for this object"))
            try:
                obj.Material = material
            except TypeError:
                msg = translate("Render",
                                "Cannot apply Material to object '%s': "
                                "object's Material property is of wrong "
                                "type") + '\n'
                App.Console.PrintError(msg % obj.Label)
        App.ActiveDocument.commitTransaction()



# ===========================================================================
#                            Commands initialization
# ===========================================================================


class CommandGroup:
    """Group of commands for GUI (toolbar, menu...)."""

    def __init__(self, cmdlist, menu, tooltip=None):
        """Initialize group of commands."""
        self.cmdlist = cmdlist
        self.menu = menu
        self.tooltip = tooltip if tooltip is not None else menu

    def GetCommands(self):
        """Get command group's commands (callback)."""
        return tuple("Render_%s" % name for name, _ in self.cmdlist)

    def GetResources(self):
        """Get command group's resources (callback)."""
        return {'MenuText': self.menu, 'ToolTip': self.tooltip}


def _init_gui_commands():
    """Initialize GUI commands for Render Workbench.

    Initialization will happen only if Gui is up.
    Please note this function has side-effects, as it calls Gui.addCommand

    Returns:
        List of commands initialized ([] if Gui is down)
    """
    def add_command(name, action):
        """Add a command to GUI (helper).

        The command name is decorated before being added.

        Params:
            name -- Name of the command to add
            action -- Action of the command to add
        """
        decorated_name = "Render_%s" % name
        Gui.addCommand(decorated_name, action)
        return decorated_name

    if not App.GuiUp:
        return []

    separator = ("Separator", None)

    projects_cmd = [(r, RenderProjectCommand(r)) for r in VALID_RENDERERS]
    projects_group = CommandGroup(projects_cmd,
                                  "Projects",
                                  "Create a Rendering Project")

    lights_cmd = [("PointLight", PointLightCommand()),
                  ("AreaLight", AreaLightCommand()),
                  ("SunskyLight", SunskyLightCommand()),
                  ("ImageLight", ImageLightCommand())]
    lights_group = CommandGroup(lights_cmd, "Lights", "Create a Light")

    mats_cmd = [("MaterialCreator", MaterialCreatorCommand()),
                ("MaterialRenderSettings", MaterialRenderSettingsCommand()),
                ("MaterialApplier", MaterialApplierCommand())]
    materials_group = CommandGroup(mats_cmd, "Materials", "Manage Materials")

    render_commands = [("Projects", projects_group),
                       separator,
                       ("Camera", CameraCommand()),
                       ("Lights", lights_group),
                       ("View", RenderViewCommand()),
                       ("Materials", materials_group),
                       separator,
                       ("Render", RenderCommand())]

    result = []

    for cmdname, cmdobj in render_commands:
        if cmdobj:
            try:
                grpcmd = cmdobj.cmdlist  # Command group
            except AttributeError:
                pass
            else:
                for cmd in grpcmd:
                    add_command(*cmd)
            fullname = add_command(cmdname, cmdobj)  # Normal command
            result.append(fullname)
        else:
            result.append(cmdname)  # Separator

    return result


# If Gui is up, create the FreeCAD commands
RENDER_COMMANDS = _init_gui_commands()
