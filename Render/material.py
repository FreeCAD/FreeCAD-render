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
import os
import ast

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
from Render.utils import translate, warn


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
        return Texture.create(filepath=img_path, group=self.fpo)

    def get_textures(self):
        """Retrieve material's textures."""
        return [o for o in self.fpo.Group if o.Proxy.Type == "Texture"]

    def has_textures(self):
        """Check whether material has textures."""
        return len(self.get_textures()) != 0

    def get_texture_images(self):
        """Retrieve material's texture images."""
        return list(
            itertools.chain.from_iterable(
                [tex.Proxy.get_images() for tex in self.get_textures()]
            )
        )

    # TODO
    def import_textures(self, material, basepath):
        """Import textures declared in the material dictionary.

        This method is intended to be called after material card import.

        Args:
            material -- the material dictionary from which to import textures
            base path -- the base path where to search textures' image files
                         (in case of relative path)

        Returns:
            the material dictionary without textures data
        """
        return _import_textures(self, material, basepath)

    def _add_group_property(self, fpo):
        """Add a Group property to object, if missing."""
        if "Group" not in fpo.PropertiesList:
            if FCDVERSION >= (0, 19):
                fpo.addExtension("App::GroupExtensionPython")
                # See https://forum.freecadweb.org/viewtopic.php?f=10&t=54370
            else:
                fpo.addExtension("App::GroupExtensionPython", self)
        fpo.setEditorMode("Group", 2)


# TODO Implementation trick
# TODO Update documentation (markdown)
# TODO Test complete chain: with shader fields referencing textures...


def _import_textures(material, input_material_dict, basepath=None):
    """Import textures data into a Material.

    This function could be a method of Material class. However, it has been
    isolated for debugging purpose.

    Args:
        material -- The Material object to update
        input_material_dict -- A material dictionary, resulting from the import
            of a material card, containing the data to update 'material'.
            WARNING: this is NOT a Material object.
        basepath -- A string giving the base path to use for relative paths when
            looking for texture files.

    Returns:
        the 'input_material_dict' after texture data have been removed
    """
    cardname = input_material_dict.get("CardName")
    domain = "Material card import"  # For warning messages

    # Separate texture data and other material data in input_material_dict
    texdata = {}
    otherdata = {}
    prefix = "Render.Textures."
    imgfield = "Images"
    for key in input_material_dict.keys():
        if key.startswith(prefix):
            # Texture data
            texname, *texparam = key[len(prefix) :].split(".")

            if texname not in texdata:
                # If texture name is unknown at this stage, create an empty dictionary
                texdata[texname] = {}
                texdata[texname][imgfield] = {}

            if texparam[0] == imgfield:
                # Image: cast image index to int
                try:
                    index = int(texparam[1])
                except ValueError:
                    msg = translate(
                        "Render",
                        "Invalid image index ('{}') in texture '{}' -- Skipping",
                    ).format(texparam[1], texname)
                    warn(domain, cardname, msg)
                else:
                    texdata[texname][imgfield][index] = input_material_dict[
                        key
                    ]
            else:
                # Not an image (must be another texture parameter)
                texdata[texname][".".join(texparam)] = input_material_dict[key]
        else:
            # Other material data
            otherdata[key] = input_material_dict[key]

    # Process texture data (create textures)
    errmsg = translate(
        "Render",
        "Error importing material card '{}' - Cannot create texture '{}': ",
    )
    for texname, params in texdata.items():  # Iterate on textures
        # Get images subdictionary
        images = params[imgfield]

        # Get primary image path parameter
        try:
            imagepath = images[0]
        except KeyError:
            msg = translate(
                "Render",
                "Missing primary image (index 0) in texture '{}' -- Skipping",
            ).format(texname)
            warn(domain, cardname, msg)
            continue

        # Format image path to absolute path and check whether the path exists
        if not os.path.isabs(imagepath):
            imagepath = os.path.join(basepath, imagepath)
        if not os.path.exists(imagepath):
            msg = translate(
                "Render",
                "Invalid image path ('{}') in texture '{}' -- Skipping",
            ).format(imagepath, texname)
            warn(domain, cardname, msg)
            continue

        # Add texture, with primary image
        texture, *_ = material.add_texture(imagepath)
        texture.fpo.Label = texname
        del images[0]  # Primary image is now processed, so remove it...

        # Add other images
        for index, imagepath in images.items():
            if not os.path.isabs(imagepath):
                imagepath = os.path.join(basepath, imagepath)
            if not os.path.exists(imagepath):
                msg = translate(
                    "Render",
                    "Invalid image path ('{}') in texture '{}' -- Skipping",
                ).format(imagepath, texname)
                warn(domain, cardname, msg)
                continue
            imagename = f"Image{index}"
            texture.add_image(imagename, imagepath)
        del params[imgfield]  # Remove all textures data

        # Add other parameters
        for key, value in params.items():
            # Check property existence
            try:
                prop = texture.fpo.getPropertyByName(key)
            except AttributeError:
                msg = translate(
                    "Render",
                    "Invalid attribute '{}' in texture '{}' -- Skipping",
                ).format(key, texname)
                warn(domain, cardname, msg)
                continue

            # Try to cast and assign value to property
            proptype = type(prop)
            try:
                cast_value = proptype(value)
            except ValueError:
                msg = translate(
                    "Render",
                    "Invalid type for attribute '{}' in texture '{}': "
                    "Cannot convert '{}' to '{}' -- Skipping",
                ).format(key, texname, value, proptype)
                warn(domain, cardname, msg)
                continue
            else:
                setattr(texture.fpo, key, cast_value)

        # Update material fields that reference this texture:
        # In the card, the fields reference the texture by the name given
        # in the card (texname), but in FreeCAD, we must reference it by the
        # internal object name.
        # We update otherdata accordingly...
        fcd_texname = texture.fpo.Name  # The internal object name
        for key, value in otherdata.items():
            # Look for Render parameter only
            if not key.startswith("Render."):
                continue  # Not Render stuff
            # Check that value references a texture
            parsed = [v.strip() for v in value.split(";")]
            if len(parsed) < 2 or parsed[0] != "Texture":
                continue  # Not a texture
            # Parse texture reference
            try:
                texture_ref = ast.literal_eval(parsed[1])
            except ValueError:
                msg = translate(
                    "Render",
                    "Invalid syntax for attribute '{}' in texture '{}': "
                    "Maybe strings are not enclosed in quotes? "
                    "Attribute = {} "
                    "-- Skipping",
                ).format(key, texname, parsed[1])
                warn(domain, cardname, msg)
                continue

            if not isinstance(texture_ref, tuple) or len(texture_ref) != 2:
                msg = translate(
                    "Render",
                    "Invalid syntax for attribute '{}' in texture '{}': "
                    "Reference to texture should be a 2-strings tuple -- Skipping",
                ).format(key, texname)
                warn(domain, cardname, msg)
                continue
            # Substitute texture reference in internal format
            parsed[1] = str((str(fcd_texname), texture_ref[1]))
            otherdata[key] = ";".join(parsed)

    # TODO Use cases to test:
    #   Material has already data

    # Finally return material data without texture data
    return otherdata


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
            action, SIGNAL("triggered()"), lambda: _add_texture(vobj)
        )
        menu.addAction(action)

    def claimChildren(self):
        """Deliver the children belonging to this object (callback)."""
        try:
            return self.Object.Group
        except AttributeError:
            return []

    def onDelete(self, vobj, subelements):  # pylint: disable=no-self-use
        """Respond to delete event."""
        # Remove all subelements (textures) belonging to this material...
        for subobj in vobj.Object.Group:
            subobj.Document.removeObject(subobj.Name)
        return True


def _add_texture(vobj):
    """Add texture to a related Material (private)."""
    App.ActiveDocument.openTransaction("Material_AddTexture")
    vobj.Object.Proxy.add_texture("")
    App.ActiveDocument.commitTransaction()
