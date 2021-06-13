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


class ColorPicker(QPushButton):
    """A color picker widget.

    This widget provides a button, with a colored square icon, which triggers
    a color dialog when it is pressed.
    """

    def __init__(self, color=QColor(127, 127, 127)):
        """Initialize ColorPicker.

        Args:
            color -- The default color of the picker
        """
        super().__init__()
        self.color = QColor(color)
        self._set_icon(self.color)
        QObject.connect(self, SIGNAL("clicked()"), self.on_button_clicked)

    def on_button_clicked(self):
        """Respond to button clicked event (callback)."""
        color = QColorDialog.getColor(initial=self.color)
        if color.isValid():
            self.color = color
            self._set_icon(color)

    def _set_icon(self, color):
        """Set the colored square icon."""
        colorpix = QPixmap(16, 16)
        colorpix.fill(color)
        self.setIcon(QIcon(colorpix))

    def set_color(self, color):
        """Set widget color value."""
        self.color = QColor(color)
        self._set_icon(self.color)

    def get_color_text(self):
        """Get widget color value, in text format."""
        color = self.color
        return "({},{},{})".format(color.redF(), color.greenF(), color.blueF())


class MaterialSettingsTaskPanel():
    """Task panel to edit Material render settings."""

    NONE_MATERIAL_TYPE = QT_TRANSLATE_NOOP("MaterialSettingsTaskPanel",
                                           "<None>")

    def __init__(self, obj=None):
        """Initialize task panel."""
        self.form = Gui.PySideUic.loadUi(TASKPAGE)
        self.tabs = self.form.RenderTabs
        self.tabs.setCurrentIndex(0)
        self.layout = self.tabs.findChild(QFormLayout, "FieldsLayout")
        self.material_type_combo = \
            self.form.findChild(QComboBox, "MaterialType")

        # Initialize material name combo
        self.material_combo = self.form.MaterialNameLayout.itemAt(0).widget()
        self.existing_materials = {obj.Label: obj
                                   for obj in App.ActiveDocument.Objects
                                   if materials.is_valid_material(obj)}
        self.material_combo.addItems(list(self.existing_materials.keys()))
        self.material_combo.currentTextChanged.connect(
            self.on_material_name_changed)

        # Initialize material type combo
        # Note: itemAt(0) is label, itemAt(1) is combo
        self.material_type_combo = \
            self.form.findChild(QComboBox, "MaterialType")
        material_type_set = [MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE] \
            + list(materials.STD_MATERIALS)
        self.material_type_combo.addItems(material_type_set)
        self.material_type_combo.currentTextChanged.connect(
            self.on_material_type_changed)
        self._set_layout_visible("FieldsLayout", False)
        self.fields = []

        # Initialize Father layout
        self._set_layout_visible("FatherLayout", False)
        self.father_field = self.form.FatherLayout.itemAt(1).widget()

        # Initialize Passthru Renderers selector
        rdrwidget = self.form.findChild(QListWidget, "Renderers")
        for rdr in VALID_RENDERERS:
            item = QListWidgetItem()
            item.setText(rdr)
            item.setIcon(QIcon(os.path.join(ICONDIR, "%s.svg" % rdr)))
            rdrwidget.addItem(item)
        rdrwidget.setViewMode(QListView.IconMode)
        rdrwidget.setIconSize(QSize(48, 48))
        rdrwidget.setMaximumWidth(96)
        rdrwidget.setSpacing(6)
        rdrwidget.setMovement(QListView.Static)
        rdrwidget.currentTextChanged.connect(
            self.on_passthrough_renderer_changed)
        self.passthru_rdr = rdrwidget
        self.passthru = self.form.findChild(QPlainTextEdit, "PassthroughEdit")
        self.passthru.textChanged.connect(self.on_passthrough_text_changed)
        self.passthru_cache = {}
        self._set_layout_visible("PassthruLayout", False)

        # Get selected material and initialize material type combo with it
        selection = {obj.Label for obj in Gui.Selection.getSelection()}
        selected_materials = selection & self.existing_materials.keys()
        try:
            selected_material = selected_materials.pop()
        except KeyError:
            pass
        else:
            self.material_combo.setCurrentText(selected_material)

    def on_material_name_changed(self, material_name):
        """Respond to material name changed event."""
        # Clear passthrough cache
        self.passthru_cache = {}

        # Find material
        try:
            material = self.existing_materials[material_name]
        except KeyError:
            # Unknown material: disable everything
            self._set_layout_visible("FieldsLayout", False)
            self._set_layout_visible("FatherLayout", False)
            self._set_layout_visible("PassthruLayout", False)
            return

        # Retrieve material type
        self._set_layout_visible("FieldsLayout", True)
        material_type_combo = self.form.findChild(QComboBox, "MaterialType")
        try:
            material_type = material.Material["Render.Type"]
        except KeyError:
            material_type_combo.setCurrentIndex(0)
        else:
            if not material_type:
                material_type = MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE
            material_type_combo.setCurrentText(material_type)

        # Retrieve passthrough
        self._set_layout_visible("PassthruLayout", True)
        try:
            renderer = self.passthru_rdr.currentItem().text()
        except AttributeError:
            renderer = None
        self._populate_passthru(renderer, material)

        # Retrieve material father
        self._set_layout_visible("FatherLayout", True)
        try:
            father = material.Material["Father"]
        except KeyError:
            father = ""
        finally:
            self.father_field.setText(father)

    def on_material_type_changed(self, material_type):
        """Respond to material type changed event."""
        # Get parameters list
        try:
            params = materials.STD_MATERIALS_PARAMETERS[material_type]
        except KeyError:
            self._delete_fields()
        else:
            self._delete_fields()
            mat_name = self.material_combo.currentText()
            for param in params:
                value = self.existing_materials[mat_name].Material.get(
                    "Render.{}.{}".format(material_type, param.name))
                self._add_field(param, value)

    def on_passthrough_renderer_changed(self, renderer):
        """Respond to passthrough renderer changed event."""
        mat_name = self.material_combo.currentText()
        material = self.existing_materials[mat_name]
        self._populate_passthru(renderer, material)

    def on_passthrough_text_changed(self):
        """Respond to passthrough renderer changed event."""
        rdr = self.passthru_rdr.currentItem()
        if not rdr:
            return
        text = self.passthru.toPlainText()
        self.passthru_cache[rdr.text()] = text

    PASSTHROUGH_KEYS = {r: materials.passthrough_keys(r)
                        for r in VALID_RENDERERS}

    def _populate_passthru(self, renderer, material):
        """Populate passthrough edit field."""
        # If no renderer or no material provided, disable field and quit
        if not renderer or not material:
            self.passthru.setPlainText("")
            self.passthru.setEnabled(False)
            return

        self.passthru.setEnabled(True)

        # If renderer passthrough is already in cache (and possibly modified),
        # use the cache; otherwise, retrieve it from 'material'.
        try:
            text = self.passthru_cache[renderer]
        except KeyError:
            keys = self.PASSTHROUGH_KEYS[renderer]
            common_keys = keys & material.Material.keys()
            lines = [material.Material[k] for k in sorted(common_keys)]
            text = '\n'.join(lines)

        self.passthru.setPlainText(text)

    def _set_layout_visible(self, layout_name, flag):
        """Make a layout visible/invisible, according to flag."""
        layout = self.form.findChild(QLayout, layout_name)
        for index in range(layout.count()):
            item = layout.itemAt(index)
            item.widget().setVisible(flag)

    def _add_field(self, param, value):
        """Add a field to the task panel."""
        name = param.name
        if param.type == "float":
            widget = QLineEdit()
            widget.setAlignment(Qt.AlignRight)
            widget.setValidator(QDoubleValidator())
            try:
                value = QLocale().toString(float(value))
            except (ValueError, TypeError):
                value = None
            widget.setText(value)
            self.fields.append(
                (name, lambda: QLocale().toDouble(widget.text())[0]))
        elif param.type == "RGB":
            if value:
                qcolor = QColor.fromRgbF(*str2rgb(value))
                widget = ColorPicker(qcolor)
            else:
                widget = ColorPicker()
            self.fields.append((name, widget.get_color_text))
        else:
            widget = QLineEdit()
            self.fields.append((name, widget.text))
        widget.setToolTip(param.desc)
        layout = self.form.findChild(QLayout, "FieldsLayout")
        layout.addRow("%s:" % param.name, widget)

    def _delete_fields(self):
        """Delete all fields, except the first one (MaterialType selector)."""
        layout = self.form.findChild(QLayout, "FieldsLayout")
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget.objectName() not in ("MaterialType",
                                           "MaterialTypeLabel"):
                widget.setParent(None)
        self.fields = []

    def _write_fields(self):
        """Write task panel fields to FreeCAD material."""
        # Find material
        mat_name = self.material_combo.currentText()
        try:
            material = self.existing_materials[mat_name]
        except KeyError:
            return
        tmp_mat = material.Material.copy()

        # Set render type and associated fields
        if self.material_type_combo.currentIndex():
            render_type = self.material_type_combo.currentText()
            if render_type == MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE:
                render_type = ""
            tmp_mat["Render.Type"] = str(render_type)

            # Set fields
            for field in self.fields:
                field_name, get_value = field
                param_name = "Render.{}.{}".format(render_type, field_name)
                tmp_mat[param_name] = str(get_value())

        # Set passthru
        pthr_keys = self.PASSTHROUGH_KEYS
        for rdr, text in self.passthru_cache.items():
            lines = dict(zip(sorted(pthr_keys[rdr]), text.splitlines()))
            tmp_mat.update(lines)

        # Set father
        father = self.father_field.text()
        if father:
            tmp_mat["Father"] = str(father)

        # Write to material
        material.Material = tmp_mat

    def accept(self):
        """Respond to user acceptation (OK button).

        Write all task panel fields to material
        """
        self._write_fields()
        Gui.ActiveDocument.resetEdit()
        Gui.Control.closeDialog()
        App.ActiveDocument.recompute()
        return True


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
