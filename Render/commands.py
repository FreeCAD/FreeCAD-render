# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *   Copyright (c) 2024 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements GUI commands for Render workbench."""


import os
import itertools as it

from PySide.QtCore import QT_TRANSLATE_NOOP, Qt, QUrl
from PySide.QtGui import (
    QMessageBox,
    QInputDialog,
    QApplication,
    QCursor,
    QFileDialog,
)

import FreeCAD as App
import FreeCADGui as Gui

from Render.constants import ICONDIR, VALID_RENDERERS, PARAMS
from Render.utils import translate
from Render.rdrhandler import RendererHandler
from Render.taskpanels import MaterialSettingsTaskPanel
from Render.project import Project, user_select_template
from Render.camera import Camera
from Render.lights import (
    PointLight,
    AreaLight,
    SunskyLight,
    ImageLight,
    DistantLight,
)
from Render.rendermaterial import is_multimat
from Render.subcontainer import start_help

MATERIALX = PARAMS.GetBool("MaterialX")
if MATERIALX:
    from Render.materialx import (
        import_materialx,
        open_mxdownloader,
    )


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
            "MenuText": QT_TRANSLATE_NOOP("RenderProjectCommand", "%s Project")
            % rdr,
            "ToolTip": QT_TRANSLATE_NOOP(
                "RenderProjectCommand", "Create a %s project"
            )
            % rdr,
        }

    def Activated(self):
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        assert self.renderer, "Error: no renderer in command"

        # Get rendering template
        if not (template := user_select_template(self.renderer)):
            return

        # Create project
        Project.create(
            App.ActiveDocument, renderer=self.renderer, template=template
        )


class RenderViewCommand:
    """GUI command to create a rendering view of an object in a project.

    The command operates on the selected object(s) and the selected project,
    or the default project.
    """

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "RenderView.svg"),
            "MenuText": QT_TRANSLATE_NOOP(
                "RenderViewCommand", "Rendering View"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "RenderViewCommand",
                "Create a Rendering View of the "
                "selected object(s) in the selected "
                "project or the default project",
            ),
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
        activedoc_projects = filter(
            RendererHandler.is_project, App.ActiveDocument.Objects
        )
        try:
            target_project = next(it.chain(projs, activedoc_projects))
        except StopIteration:
            msg = (
                translate(
                    "Render",
                    "[Render] Unable to find a valid project in selection "
                    "or document",
                )
                + "\n"
            )
            App.Console.PrintError(msg)
            return

        # Finally, add objects to target project
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        target_project.Proxy.add_views(objs)
        QApplication.restoreOverrideCursor()


class RenderCommand:
    """GUI command to render a selected Render project."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "Render.svg"),
            "MenuText": QT_TRANSLATE_NOOP("RenderCommand", "Render"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "RenderCommand",
                "Perform the rendering of a "
                "selected project or the default "
                "project",
            ),
        }

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
        return {
            "Pixmap": ":/icons/camera-photo.svg",
            "MenuText": QT_TRANSLATE_NOOP("CameraCommand", "Camera"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "CameraCommand",
                "Create a Camera object from the current camera position",
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new camera into the active document.
        """
        Camera.create()


class PointLightCommand:
    """GUI command to create a Point Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "PointLight.svg"),
            "MenuText": QT_TRANSLATE_NOOP("PointLightCommand", "Point Light"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "PointLightCommand", "Create a Point Light object"
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new point light into the active document.
        """
        PointLight.create()


class AreaLightCommand:
    """GUI command to create an Area Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "AreaLight.svg"),
            "MenuText": QT_TRANSLATE_NOOP("AreaLightCommand", "Area Light"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "AreaLightCommand", "Create an Area Light object"
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new area light into the active document.
        """
        AreaLight.create()


class SunskyLightCommand:
    """GUI command to create an Sunsky Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "SunskyLight.svg"),
            "MenuText": QT_TRANSLATE_NOOP(
                "SunskyLightCommand", "Sunsky Light"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "SunskyLightCommand", "Create a Sunsky Light object"
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new sunsky light into the active document.
        """
        SunskyLight.create()


class ImageLightCommand:
    """GUI command to create an Image Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "ImageLight.svg"),
            "MenuText": QT_TRANSLATE_NOOP("ImageLightCommand", "Image Light"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "ImageLightCommand", "Create an Image Light object"
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new image light into the active document.
        """
        ImageLight.create()


class DistantLightCommand:
    """GUI command to create an Image Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "DistantLight.svg"),
            "MenuText": QT_TRANSLATE_NOOP(
                "DistantLightCommand", "Distant Light"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "DistantLightCommand", "Create an Distant Light object"
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new image light into the active document.
        """
        DistantLight.create()


class MaterialCreatorCommand:
    """GUI command to create a material."""

    def __init__(self, newname=False):
        """Init command."""
        self._newname = bool(newname)

    def GetResources(self):
        """Get command's resources (callback)."""
        res = {
            "Pixmap": "Arch_Material_Group",
            "MenuText": (
                QT_TRANSLATE_NOOP(
                    "MaterialCreatorCommand", "Internal Material Library"
                )
                if self._newname
                else QT_TRANSLATE_NOOP(
                    "MaterialCreatorCommand", "Create Material"
                )
            ),
            "ToolTip": (
                QT_TRANSLATE_NOOP(
                    "MaterialCreatorCommand",
                    "Create a new Material in current document from internal library",
                )
            ),
        }
        return res

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback)."""
        App.ActiveDocument.openTransaction(
            translate("Render", "Create material")
        )
        Gui.Control.closeDialog()
        Gui.addModule("Render")
        cmds = [
            "obj = Render.make_material()",
            "Gui.Selection.clearSelection()",
            "Gui.Selection.addSelection(obj.Document.Name, obj.Name)",
            "obj.ViewObject.Document.setEdit(obj.ViewObject, 0)",
        ]
        for cmd in cmds:
            Gui.doCommand(cmd)
        App.ActiveDocument.commitTransaction()

    def IsActive(self):
        v = hasattr(
            FreeCADGui.getMainWindow().getActiveWindow(), "getSceneGraph"
        )
        return v


class MaterialMaterialXImportCommand:
    """GUI command to import a MaterialX material."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "materialx-stacked-black.svg"),
            "MenuText": QT_TRANSLATE_NOOP(
                "MaterialMaterialXImportCommand",
                "Import MaterialX file",
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "MaterialMaterialXImportCommand",
                "Import a material from MaterialX file",
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It opens a dialog to set the rendering parameters of the selected
        material.
        """
        filefilter = "MaterialX (*.mtlx *.zip);;All files (*.*)"
        caption = translate("Render", "Select MaterialX")
        openfilename = QFileDialog.getOpenFileName(
            Gui.getMainWindow(), caption, "", filefilter
        )
        if not (materialx_file := openfilename[0]):
            return
        App.ActiveDocument.openTransaction("MaterialXImport")
        import_materialx(materialx_file, Gui.ActiveDocument.Document)
        App.ActiveDocument.commitTransaction()


class MaterialMaterialXLibrary:
    """GUI command to open MaterialX online library."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "amdgpuopen.png"),
            "MenuText": QT_TRANSLATE_NOOP(
                "MaterialMaterialXImportCommand",
                "GPUOpen Material Library",
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "MaterialMaterialXImportCommand",
                "Open AMD GPUOpen Material Library",
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It opens a dialog to set the rendering parameters of the selected
        material.
        """
        doc = App.ActiveDocument
        url = QUrl("https://matlib.gpuopen.com/")
        open_mxdownloader(url, doc)


class MaterialAmbientCGLibrary:
    """GUI command to open AmbientCG online library."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "ambientcg.png"),
            "MenuText": QT_TRANSLATE_NOOP(
                "MaterialMaterialXImportCommand",
                "AmbientCG Material Library",
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "MaterialMaterialXImportCommand",
                "Open AmbientCG Material Library",
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It opens a dialog to set the rendering parameters of the selected
        material.
        """
        doc = App.ActiveDocument
        url = QUrl("https://ambientcg.com/")
        open_mxdownloader(url, doc, disp2bump=True)


class MaterialRenderSettingsCommand:
    """GUI command to set render settings of a material object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "MaterialSettings.svg"),
            "MenuText": QT_TRANSLATE_NOOP(
                "MaterialRenderSettingsCommand",
                "Edit Material Render Settings",
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "MaterialRenderSettingsCommand",
                "Edit rendering parameters of the selected Material",
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It opens a dialog to set the rendering parameters of the selected
        material.
        """
        App.ActiveDocument.openTransaction("MaterialSettings")
        task = MaterialSettingsTaskPanel()
        Gui.Control.showDialog(task)
        App.ActiveDocument.commitTransaction()


class MaterialApplierCommand:
    """GUI command to apply a material to an object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "ApplyMaterial.svg"),
            "MenuText": QT_TRANSLATE_NOOP(
                "MaterialApplierCommand", "Apply Material"
            ),
            "ToolTip": QT_TRANSLATE_NOOP(
                "MaterialApplierCommand", "Apply a Material to selection"
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It sets the Material property of the selected object(s).
        If the Material property does not exist in the object(s), it is
        created.
        """
        # Get selected objects
        if not (selection := Gui.Selection.getSelection()):
            title = translate("Render", "Empty Selection")
            msg = translate(
                "Render",
                "Please select object(s) before applying material.",
            )
            QMessageBox.warning(None, title, msg)
            return

        # Let user pick the Material
        mats = [
            o
            for o in App.ActiveDocument.Objects
            if o.isDerivedFrom("App::MaterialObjectPython") or is_multimat(o)
        ]
        if not mats:
            title = translate("Render", "No Material")
            msg = translate(
                "Render",
                "No Material in document. Please create a "
                "Material before applying.",
            )
            QMessageBox.warning(None, title, msg)
            return
        matlabels = [m.Label for m in mats]
        current_mats_labels = [
            o.Material.Label
            for o in selection
            if hasattr(o, "Material")
            and hasattr(o.Material, "Label")
            and o.Material.Label
        ]
        current_mats = [
            count
            for count, val in enumerate(matlabels)
            if val in current_mats_labels
        ]
        current_mat = current_mats[0] if len(current_mats) == 1 else 0

        userinput, status = QInputDialog.getItem(
            None,
            translate("Render", "Material Applier"),
            translate("Render", "Choose Material to apply to selection:"),
            matlabels,
            current_mat,
            False,
        )
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
                        "App::Property", "The Material for this object"
                    ),
                )
            try:
                obj.Material = material
            except TypeError:
                msg = (
                    translate(
                        "Render",
                        "[Render][Material] "
                        "Cannot apply Material to object '%s': "
                        "object's Material property is of wrong "
                        "type",
                    )
                    + "\n"
                )
                App.Console.PrintError(msg % obj.Label)
            except ValueError as err:
                msg = (
                    translate(
                        "Render",
                        "[Render][Material] "
                        f"Cannot apply Material to object '{obj.Label}': "
                        "object's Material property does not accept "
                        f"provided material '{material.Label}'",
                    )
                    + "\n"
                )
                msg2 = (
                    translate(
                        "Render",
                        "[Render][Material] Object raises ValueError "
                        f"{err.args}",
                    )
                    + "\n"
                )
                # Maybe related to:
                # https://forum.freecad.org/viewtopic.php?t=87202&start=50#p756345
                #
                # Material and Part were not in the same document (in
                # particular, it could happen with assemblies, with parts in
                # separate docs)
                App.Console.PrintError(msg)
                App.Console.PrintError(msg2)
        App.ActiveDocument.commitTransaction()


class HelpCommand:
    """GUI command to open help."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "Help.svg"),
            "MenuText": QT_TRANSLATE_NOOP("HelpCommand", "Help"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "HelpCommand",
                "Open Render help",
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It opens a help browser in Gui.
        """
        start_help()


class SettingsCommand:
    """GUI command to Render WB settings."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(ICONDIR, "settings.svg"),
            "MenuText": QT_TRANSLATE_NOOP("SettingsCommand", "Render"),
            "ToolTip": QT_TRANSLATE_NOOP(
                "SettingsCommand",
                "Open Render workbench settings",
            ),
        }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It opens the settings (preferences) page.
        """
        Gui.showPreferences("Render")


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
        return tuple(f"Render_{name}" for name, _ in self.cmdlist)

    def GetResources(self):
        """Get command group's resources (callback)."""
        return {"MenuText": self.menu, "ToolTip": self.tooltip}


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
        decorated_name = f"Render_{name}"
        Gui.addCommand(decorated_name, action)
        return decorated_name

    if not App.GuiUp:
        return []

    separator = ("Separator", None)

    projects_cmd = [(r, RenderProjectCommand(r)) for r in VALID_RENDERERS]
    projects_group = CommandGroup(
        projects_cmd, "Projects", "Create a Rendering Project"
    )

    lights_cmd = [
        ("PointLight", PointLightCommand()),
        ("AreaLight", AreaLightCommand()),
        ("SunskyLight", SunskyLightCommand()),
        ("ImageLight", ImageLightCommand()),
        ("DistantLight", DistantLightCommand()),
    ]
    lights_group = CommandGroup(lights_cmd, "Lights", "Create a Light")

    mats_cmd = [
        ("MaterialApplier", MaterialApplierCommand()),
        ("MaterialRenderSettings", MaterialRenderSettingsCommand()),
    ]
    materials_group = CommandGroup(mats_cmd, "Materials", "Manage Materials")

    libs_cmd = [
        ("MaterialMaterialXLibrary", MaterialMaterialXLibrary()),
        ("MaterialAmbientCGLibrary", MaterialAmbientCGLibrary()),
        ("MaterialCreator", MaterialCreatorCommand()),
        ("MaterialMaterialXImporter", MaterialMaterialXImportCommand()),
    ]
    libraries_group = CommandGroup(
        libs_cmd, "Libraries", "Download from material libraries"
    )

    if MATERIALX:
        render_commands = [
            ("Projects", projects_group),
            separator,
            ("Camera", CameraCommand()),
            ("Lights", lights_group),
            ("View", RenderViewCommand()),
            separator,
            ("Libraries", libraries_group),
            ("Materials", materials_group),
            separator,
            ("Render", RenderCommand()),
            separator,
            ("Settings", SettingsCommand()),
            ("Help", HelpCommand()),
        ]
    else:
        mats_cmd.insert(0, ("MaterialCreator", MaterialCreatorCommand()))
        render_commands = [
            ("Projects", projects_group),
            separator,
            ("Camera", CameraCommand()),
            ("Lights", lights_group),
            ("View", RenderViewCommand()),
            separator,
            ("Materials", materials_group),
            separator,
            ("Render", RenderCommand()),
            separator,
            ("Settings", SettingsCommand()),
            ("Help", HelpCommand()),
        ]

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
