# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements Material object for Render workbench.

Please note Render Material object is mainly derived from Arch Material.
"""

import itertools

import FreeCAD as App
import FreeCADGui as Gui

from PySide.QtGui import QAction
from PySide.QtCore import QObject, SIGNAL, QT_TRANSLATE_NOOP

from ArchMaterial import (
    _ArchMaterial,
    _ViewProviderArchMaterial,
    getMaterialContainer,
)

from Render.texture import Texture
from Render.taskpanels import MaterialTaskPanel, MaterialSettingsTaskPanel
from Render.constants import FCDVERSION


def make_material(name="Material", color=None, transparency=None):
    """Make an Material object."""
    if not App.ActiveDocument:
        App.Console.PrintError("No active document. Aborting\n")
        return None
    obj = App.ActiveDocument.addObject("App::MaterialObjectPython", "Material")
    obj.Label = name
    Material(obj)
    if App.GuiUp:
        ViewProviderMaterial(obj.ViewObject)
    getMaterialContainer().addObject(obj)
    if color:
        obj.Color = color[:3]
        if len(color) > 3:
            obj.Transparency = color[3] * 100
    if transparency:
        obj.Transparency = transparency
    return obj

def strtobool(val):
    """Convert a string representation of truth to True or False.

    True values are y, yes, t, true, on and 1; false values are n, no, f,
    false, off and 0, in a case-insensitive manner. Raises ValueError if val is
    anything else.
    This function is a local reimplementation of deprecated
    `distutils.util.strtobool`.
    """
    val = str(val).lower()
    if val in ["y", "yes", "t", "true", "on", "1"]:
        return True
    if val in ["n", "no", "f", "false", "off", "0"]:
        return False
    raise ValueError

class Material(_ArchMaterial):
    """The Render Material object.

    This class is essentially derived from Arch WB's equivalent one.
    """

    # Internal variables, do not modify
    _fpos = {}
    _on_changed_counters = {}

    def __init__(self, vobj):
        super().__init__(vobj)
        self.fpo = vobj
        self._add_group_property(vobj)
        self.__module__ = "Render"

    def onDocumentRestored(self, obj):
        super().onDocumentRestored(obj)
        self.fpo = obj
        self._add_group_property(obj)
        self.__module__ = "Render"

    @property
    def fpo(self):
        """Get underlying FeaturePython object."""
        return self._fpos[id(self)]

    @fpo.setter
    def fpo(self, new_fpo):
        """Set underlying FeaturePython object."""
        self._fpos[id(self)] = new_fpo

    @property
    def on_changed_counter(self):
        """Gets on_changed_counter."""
        try:
            res = self._on_changed_counters[id(self)]
        except KeyError:
            res = 0
            self._on_changed_counters[id(self)] = res
        return res

    @on_changed_counter.setter
    def on_changed_counter(self, new_counter):
        """Sets on_changed_counter."""
        self._on_changed_counters[id(self)] = new_counter

    def onChanged(self, obj, prop):
        # Use a counter to avoid reentrance (possible infinite recursion)
        if not self.on_changed_counter:
            self.on_changed_counter += 1
            super().onChanged(obj, prop)
            self.on_changed_counter -= 1

    def execute(self, obj):
        # Prevent applying material color if UseObjectColor is set
        try:
            if strtobool(obj.Material["UseObjectColor"]):
                return
        except KeyError:
            pass

        super().execute(obj)

    def add_texture(self, img_path):
        """Add a texture to the material.

        Args:
            filepath: path to image file (mandatory)
        """
        img_path = str(img_path)
        Texture.create(filepath=img_path, group=self.fpo)

    def get_textures(self):
        """Retrieve material's textures."""
        return [o for o in self.fpo.Group if o.Proxy.Type == "Texture"]

    def get_texture_images(self):
        """Retrieve material's texture images."""
        return list(
            itertools.chain.from_iterable(
                [tex.Proxy.get_images() for tex in self.get_textures()]
            )
        )

    def _add_group_property(self, fpo):
        """Add a Group property to object, if missing."""
        if "Group" not in fpo.PropertiesList:
            if FCDVERSION >= (0, 19):
                fpo.addExtension("App::GroupExtensionPython")
                # See https://forum.freecadweb.org/viewtopic.php?f=10&t=54370
            else:
                fpo.addExtension("App::GroupExtensionPython", self)
        fpo.setEditorMode("Group", 2)


class ViewProviderMaterial(_ViewProviderArchMaterial):
    """A View Provider for the Material object.

    This class is essentially derived from the Arch WB's equivalent one.
    The main difference is that the edition is done by Render's Material
    Task Panel.
    """

    def __init__(self, vobj):
        super().__init__(vobj)
        self.__module__ = "Render"
        self.taskd = None

    def attach(self, vobj):
        super().attach(vobj)
        self.__module__ = "Render"

    def setEdit(self, vobj, mode):
        self.taskd = MaterialTaskPanel(vobj.Object)
        Gui.Control.showDialog(self.taskd)
        self.taskd.form.FieldName.setFocus()
        self.taskd.form.FieldName.selectAll()
        return True

    def setupContextMenu(self, vobj, menu):  # pylint: disable=no-self-use
        """Set up the object's context menu in GUI (callback)."""
        # Edit Render Settings
        action = QAction(
            QT_TRANSLATE_NOOP("Render", "Edit Render Settings"), menu
        )
        QObject.connect(
            action,
            SIGNAL("triggered()"),
            lambda: Gui.Control.showDialog(MaterialSettingsTaskPanel()),
        )
        menu.addAction(action)

        # Edit General Settings
        action = QAction(
            QT_TRANSLATE_NOOP("Render", "Edit General Settings"), menu
        )
        QObject.connect(
            action,
            SIGNAL("triggered()"),
            lambda: Gui.activeDocument().setEdit(vobj.Object.Name, 0),
        )
        menu.addAction(action)

        # Add a texture to material
        action = QAction(QT_TRANSLATE_NOOP("Render", "Add Texture"), menu)
        QObject.connect(
            action, SIGNAL("triggered()"), lambda: self._add_texture(vobj)
        )
        menu.addAction(action)

    def claimChildren(self):
        """Deliver the children belonging to this object (callback)."""
        try:
            return self.Object.Group
        except AttributeError:
            return []

    def _add_texture(self, vobj):
        """Add texture to related Material (private)."""
        App.ActiveDocument.openTransaction("Material_AddTexture")
        # TODO Add image file selection
        vobj.Object.Proxy.add_texture("")
        App.ActiveDocument.commitTransaction()

    def onDelete(self, vobj, subelements):
        """Respond to delete event."""
        # Remove all subelements (textures) belonging to this material...
        for subobj in vobj.Object.Group:
            subobj.Document.removeObject(subobj.Name)
        return True
