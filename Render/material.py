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
import functools
import os
import re
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
        # To facilitate debugging, this method is implemented in a separate
        # function...
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


# ===========================================================================
#                             Texture import
# ===========================================================================

# TODO Update documentation (markdown)

_TEXPREFIX = "Render.Textures."
_TEXIMGFIELD = "Images"
_TEXWARNDOMAIN = "Material card import"  # For warning messages

# TODO replace input_material_dict by fcdmaterial
def _separate_texture(input_material_dict, texwarn):

    # Separate texture data and other material data in input_material_dict
    texdata = {}
    otherdata = {}
    for key, value in input_material_dict.items():

        if not key.startswith(_TEXPREFIX):
            # Other material data (not texture...)
            otherdata[key] = value
            continue

        # Split key using '.' separator
        texname, *texsubnames = key[len(_TEXPREFIX) :].split(".")

        # If texture name is unknown at this stage, create a
        # dictionary to store its forthcoming data
        if texname not in texdata:
            texdata[texname] = {_TEXIMGFIELD: {}}

        # Check whether it is an image field. If not, it must be another
        # texture parameter: just add value to texdata and continue
        if texsubnames[0] != _TEXIMGFIELD:
            texdata[texname][".".join(texsubnames)] = value
            continue

        # It is an image field: cast its index to int and add value to texdata
        try:
            index = int(texsubnames[1])
        except ValueError:
            msg = translate(
                "Render",
                "Invalid image index ('{}') in texture '{}' -- Skipping",
            ).format(texsubnames[1], texname)
            texwarn(msg)
        else:
            texdata[texname][_TEXIMGFIELD][index] = value


    return texdata, otherdata

# TODO Move up and after ViewProviderMaterial
def _import_textures(material, input_material_dict, basepath=None):
    """Import textures data into a Material.

    Nota: This function could be a method of Material class. However, it has
    been isolated for debugging purpose.

    Args:
        material -- The Render.Material object to update
        input_material_dict -- A material dictionary, resulting from the import
          of a material card, containing the data to update 'material'.
          WARNING: this is NOT a Render.Material object.
        basepath -- A string giving the base path to use for relative paths
          when looking for texture files.

    Returns:
        the 'input_material_dict' after texture data have been removed
    """
    cardname = input_material_dict.get("CardName")
    texwarn = functools.partial(warn, _TEXWARNDOMAIN, cardname)

    # Separate texture data from other material data
    texdata, otherdata = _separate_texture(input_material_dict, texwarn)

    # Process texture data (create textures)
    for texname, params in texdata.items():  # Iterate on textures
        # Get images subdictionary
        images = params[_TEXIMGFIELD]

        # Get primary image path parameter
        try:
            imagepath = images[0]
        except KeyError:
            msg = translate(
                "Render",
                "Missing primary image (index 0) in texture '{}' -- Skipping",
            ).format(texname)
            texwarn(msg)
            continue

        # Format image path to absolute path and check whether the path exists
        if not os.path.isabs(imagepath):
            imagepath = os.path.join(basepath, imagepath)
        if not os.path.exists(imagepath):
            msg = translate(
                "Render",
                "Invalid image path ('{}') in texture '{}' -- Skipping",
            ).format(imagepath, texname)
            texwarn(msg)
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
                texwarn(msg)
                continue
            imagename = f"Image{index}"
            texture.add_image(imagename, imagepath)
        del params[_TEXIMGFIELD]  # Remove all textures data

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
                texwarn(msg)
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
                texwarn(msg)
                continue
            else:
                setattr(texture.fpo, key, cast_value)

        fcd_texname = texture.fpo.Name  # The internal object name
        _update_texture_references(otherdata, fcd_texname, texname, texwarn)

    # Finally return material data without texture data
    return otherdata

def _update_texture_references(otherdata, fcd_texname, texname, texwarn):
    # Parse and update material fields that reference this texture:
    # In the card:
    # - the expected syntax is:
    #   Texture("<texture_name>", <index>); <fallback_color>
    # - <texture_name> reference the texture by the name given in the card
    # In FreeCAD:
    # - the expected syntax is:
    #   Texture;("<texture_name>", "<property_name>"); <fallback_color>
    # - <texture_name> must reference the texture by the internal
    #   object name, which may be slightly different (name collisions
    #   etc.),
    # Thus we have to translate...
    # We update otherdata accordingly...
    for key, value in otherdata.items():
        # Look for Render parameter only
        if not key.startswith("Render."):
            continue  # Not Render stuff

        # Search for texture statement
        parsed = [v.strip() for v in value.split(";")]  # Split and strip
        texture_statement = re.search(r"Texture\s*(.*)", parsed[0])
        if texture_statement is None:
            continue  # Not a texture statement

        # Find texture argument
        try:
            texture_argument = texture_statement.group(1)
        except IndexError:
            msg = translate(
                "Render",
                "Invalid syntax for texture '{}': "
                "No valid arguments in statement ('{}') -- Skipping",
            ).format(texname, texture_statement)
            texwarn(msg)
            continue

        # Parse texture argument (into texture reference)
        try:
            texture_ref = ast.literal_eval(texture_argument)
        except (ValueError, SyntaxError):
            msg = translate(
                "Render",
                "Invalid syntax for attribute '{}' in texture '{}': "
                """Expecting 'Texture("<texname>", <texindex>)', """
                "got '{}' instead -- Skipping",
            ).format(key, texname, parsed[0])
            texwarn(msg)
            continue

        if not isinstance(texture_ref, tuple) or len(texture_ref) != 2:
            msg = translate(
                "Render",
                "Invalid syntax for attribute '{}' in texture '{}': "
                "Reference to texture should be a tuple "
                "('<texture>', <index>) -- Skipping",
            ).format(key, texname)
            texwarn(msg)
            continue

        # Substitute texture reference in internal format
        # Internal format is ("<texturename>", "<imagepropertyname>")
        # We have to recompute <imagepropertyname>
        imgpropname = f"Image{texture_ref[1]}" if texture_ref[1] != 0 else "Image"

        # Translate in internal format and update 'otherdata'
        internal = ["Texture", str((fcd_texname, imgpropname))]
        internal += parsed[1:]
        otherdata[key] = ";".join(internal)


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
