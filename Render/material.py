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


# ===========================================================================
#                             Texture import
# ===========================================================================

# TODO Update documentation (markdown)

# TODO Merge into Material
def _import_textures(material, matcard_dict, basepath=None):
    """Import textures data into a Material.

    Textures are created under the Material object. A version of
    'matcard_dict' without the textures data is returned.
    Nota: This function could be a method of Material class. However, it has
    been isolated for debugging purpose.

    Args:
        material -- The Render.Material object to update
        matcard_dict -- A material card dictionary, resulting from the import
          of a material card, containing the data to update 'material'.
        basepath -- A string giving the base path to use for relative paths
          when looking for texture files.

    Returns:
        'matcard_dict' after texture data have been removed
    """
    # Initialize helper
    tih = _TextureImportHelper(material, matcard_dict, basepath)

    # Separate texture data from other material data
    texdata, otherdata = tih.separate_texture_data()

    # Process texture data: create textures
    for texname, params in texdata.items():  # Iterate on textures

        # Add texture
        texture = tih.add_texture_to_material(texname, params)
        if texture is None:  # TODO prefer exception
            continue

        # Update references to this texture
        internal_texname = texture.fpo.Name  # The internal object name
        tih.update_texture_references(
            otherdata, internal_texname, texname
        )

    # Finally return material data without texture data
    return otherdata


class _TextureImportHelper:
    """A helper class for texture import.

    This class gather functions, constants, exceptions etc. needed to import
    textures in a Material.
    """

    TEXPREFIX = "Render.Textures."
    TEXIMGFIELD = "Images"
    TEXWARNDOMAIN = "Material card import"  # For warning messages

    def __init__(self, material, matcard_dict, basepath=None):
        """Initialize helper.

        Args:
            material -- The Render.Material to add textures to.
              (Render.Material)
            matcard_dict -- A material card dictionary, resulting from the
              import of a material card, containing the data to update
              'material'. (dict)
            basepath -- A string giving the base path to use for relative
              paths when looking for texture files. (str)
        """
        self.material = material
        self.matcard_dict = matcard_dict.copy()
        self.cardname = self.matcard_dict.get("CardName")
        self.basepath = basepath

    def _warn(self, msg):
        """Emit a warning."""
        warn(self.TEXWARNDOMAIN, self.cardname, msg)

    def separate_texture_data(self):
        """Split material card dictionary into texture and non texture data.

        Returns:
            A dictionary with texture data
            A dictionary with other data
        """

        # Separate texture data and other material data in matcard_dict
        texdata = {}
        otherdata = {}
        for key, value in self.matcard_dict.items():

            if not key.startswith(self.TEXPREFIX):
                # Other material data (not texture...), put in otherdata
                otherdata[key] = value
                continue

            # Split key using '.' separator
            texname, *texsubnames = key[len(self.TEXPREFIX) :].split(".")

            # If texture name is unknown at this stage, create a
            # dictionary to store its forthcoming data
            if texname not in texdata:
                texdata[texname] = {self.TEXIMGFIELD: {}}

            # Check whether it is an image field. If not, it must be another
            # texture parameter: just add value to texdata and continue
            if texsubnames[0] != self.TEXIMGFIELD:
                texdata[texname][".".join(texsubnames)] = value
                continue

            # It is an image field: cast its index to int and add value to
            # texdata
            try:
                index = int(texsubnames[1])
            except ValueError:
                msg = translate(
                    "Render",
                    "Invalid image index ('{}') in texture '{}' -- Skipping",
                ).format(texsubnames[1], texname)
                self._warn(msg)

            texdata[texname][self.TEXIMGFIELD][index] = value

        return texdata, otherdata

    def _get_absolute_imagepath(self, imagepath, texname):
        # TODO Get rid of texname
        """Get an absolute image path from relative or absolute one.

        The function checks whether the obtained path exists and will return
        None otherwise.

        Args:
            imagepath -- The input image path, relative or absolute (str)

        Returns: absolute image path if exists, None otherwise.
        """
        if not os.path.isabs(imagepath):
            imagepath = os.path.join(self.basepath, imagepath)

        if not os.path.exists(imagepath):
            msg = translate(
                "Render",
                "Invalid image path ('{}') in texture '{}' -- Skipping",
            ).format(imagepath, texname)
            self._warn(msg)
            return None

        return imagepath

    def add_texture_to_material(self, texname, texparams):
        """Add a texture to a Material based on material card data.

        Args:
            texname -- texture name (str)
            texparams -- texture parameters, from material card (dict)

        Returns:
            The newly created texture (a Render.Texture object).
            None if something wrong occured.
        """
        # Get images subdictionary
        images = texparams[self.TEXIMGFIELD]

        # Get primary image path from parameters
        try:
            imagepath = images[0]
        except KeyError:
            msg = translate(
                "Render",
                "Missing primary image (index 0) in texture '{}' -- Skipping",
            ).format(texname)
            self._warn(msg)
            return None

        # Get absolute image path for primary image
        imagepath = self._get_absolute_imagepath(imagepath, texname)
        if imagepath is None:
            return None

        # Create texture with primary image
        texture, *_ = self.material.add_texture(imagepath)
        texture.fpo.Label = texname

        # Add other images
        for index, imagepath in images.items():
            if index == 0:
                continue  # Primary image, already processed...

            # Find image path and add to texture
            imagepath = self._get_absolute_imagepath(imagepath, texname)
            if imagepath is None:
                continue

            # Add image
            imagename = f"Image{index}"
            texture.add_image(imagename, imagepath)

        # Add other parameters
        for key, value in filter(
            lambda i: i[0] != self.TEXIMGFIELD, texparams.items()
        ):
            # Check property existence
            try:
                prop = texture.fpo.getPropertyByName(key)
            except AttributeError:
                msg = translate(
                    "Render",
                    "Invalid attribute '{}' in texture '{}' -- Skipping",
                ).format(key, texname)
                self._warn(msg)
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
                self._warn(msg)
                continue

            # Set property
            setattr(texture.fpo, key, cast_value)

        return texture

    def update_texture_references(
        self, otherdata, internal_texname, card_texname
    ):
        """Update material card fields which reference a texture.

        This method translates the texture syntax from the material card to the
        internal Texture syntax. It also updates references from the material
        to the texture, as the internal name of the texture may vary from its
        card name.

        In the material card:
        - the expected syntax is:
          Texture("<texture_name>", <index>); <fallback_color>
        - <texture_name> references the texture by the name given in the card
        In FreeCAD:
        - the expected syntax is:
          Texture;("<texture_name>", "<property_name>"); <fallback_color>
        - <texture_name> must reference the texture by the internal
          object name, which may be slightly different (name collisions
          etc.)

        Args:
            otherdata -- The material card data that may reference the texture
              This object will be modified (dict)
            internal_texname -- The name of the Texture object in FreeCAD
            card_texname -- The name of the texture in the material card
        """
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
                ).format(card_texname, texture_statement)
                self._warn(msg)
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
                ).format(key, card_texname, parsed[0])
                self._warn(msg)
                continue

            if not isinstance(texture_ref, tuple) or len(texture_ref) != 2:
                msg = translate(
                    "Render",
                    "Invalid syntax for attribute '{}' in texture '{}': "
                    "Reference to texture should be a tuple "
                    "('<texture>', <index>) -- Skipping",
                ).format(key, card_texname)
                self._warn(msg)
                continue

            # Substitute texture reference in internal format
            # Internal format is ("<texturename>", "<imagepropertyname>")
            # We have to recompute <imagepropertyname>
            imgpropname = (
                f"Image{texture_ref[1]}" if texture_ref[1] != 0 else "Image"
            )

            # Translate in internal format and update 'otherdata'
            internal = ["Texture", str((internal_texname, imgpropname))]

            internal += parsed[1:]
            otherdata[key] = ";".join(internal)
