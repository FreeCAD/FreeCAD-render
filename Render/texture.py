# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2022 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements Texture object for Render workbench.

Texture object allows to add an image file as texture to a material.
"""

from collections import namedtuple
import ast

from PySide.QtCore import QT_TRANSLATE_NOOP
from PySide.QtGui import QMessageBox, QInputDialog

import FreeCAD as App

from Render.base import FeatureBase, ViewProviderBase, Prop, CtxMenuItem
from Render.utils import translate


ImageId = namedtuple("ImageId", "texture image")


def str2imageid(string):
    """Convert a ({texture}, {image})-like string to an ImageId."""
    parsed = map(str, ast.literal_eval(string))
    return ImageId._make(parsed)


class Texture(FeatureBase):
    """An object to add an image file as texture to a material."""

    VIEWPROVIDER = "ViewProviderTexture"

    IMAGE_GROUP = QT_TRANSLATE_NOOP("Render", "Image(s)")
    MAPPING_GROUP = QT_TRANSLATE_NOOP("Render", "Mapping")

    PROPERTIES = {
        "Image": Prop(
            "App::PropertyFileIncluded",
            IMAGE_GROUP,
            QT_TRANSLATE_NOOP("Render", "Texture Image File"),
            "",
        ),
        "Rotation": Prop(
            "App::PropertyAngle",
            MAPPING_GROUP,
            QT_TRANSLATE_NOOP("Render", "UV rotation (in degrees)"),
            0,
        ),
        "ScaleU": Prop(
            "App::PropertyFloat",
            MAPPING_GROUP,
            QT_TRANSLATE_NOOP("Render", "UV scale - U component"),
            0,
        ),
        "ScaleV": Prop(
            "App::PropertyFloat",
            MAPPING_GROUP,
            QT_TRANSLATE_NOOP("Render", "UV scale - V component"),
            0,
        ),
        "TranslationU": Prop(
            "App::PropertyDistance",
            MAPPING_GROUP,
            QT_TRANSLATE_NOOP("Render", "UV translation - U component"),
            0,
        ),
        "TranslationV": Prop(
            "App::PropertyDistance",
            MAPPING_GROUP,
            QT_TRANSLATE_NOOP("Render", "UV translation - V component"),
            0,
        ),
    }

    def on_create_cb(self, fpo, viewp, **kwargs):
        try:
            filepath = kwargs["filepath"]
        except KeyError:
            pass
        else:
            fpo.Image = filepath

        try:
            group = kwargs["group"]
        except KeyError:
            pass
        else:
            group.addObject(fpo)

    def add_image(self):
        """Add an image property."""
        self.fpo.addProperty(
            "App::PropertyFileIncluded", "Image", self.IMAGE_GROUP
        )

    def get_images(self):
        """Get the list of images properties of the texture."""
        images = tuple(
            ImageId(self.fpo.Name, p)
            for p in self.fpo.PropertiesList
            if self.fpo.getTypeIdOfProperty(p) == "App::PropertyFileIncluded"
        )
        return images

    def remove_image(self, img_name):
        """Remove an image, given its property name.

        Args:
            img_name -- the name of the property containing the image
        """
        find_image = [
            o.image for o in self.get_images() if o.image == img_name
        ]
        if find_image:
            self.fpo.removeProperty(img_name)


class ViewProviderTexture(ViewProviderBase):
    """View Provider of Texture class.

    (no Coin representation)
    """

    ICON = ""  # TODO Add Icon

    CONTEXT_MENU = [
        CtxMenuItem(
            QT_TRANSLATE_NOOP("Render", "Add Image Entry"), "_add_image"
        ),
        CtxMenuItem(
            QT_TRANSLATE_NOOP("Render", "Remove Image Entry"), "_del_image"
        ),
    ]

    def _add_image(self):
        """Add an new image property to the related texture."""
        App.ActiveDocument.openTransaction("Texture_AddImage")
        self.fpo.Proxy.add_image()
        App.ActiveDocument.commitTransaction()

    def _del_image(self):
        """Remove an image property."""
        images = self.fpo.Proxy.get_images()

        # Test if enough remaining images
        if len(images) < 2:
            title = translate("Render", "Unallowed Image Removal")
            msg = translate(
                "Render",
                "Unallowed removal: " "not enough images in texture (<2)!\n",
            )
            msg2 = translate(
                "Render",
                "Leaving less than 1 image in texture is not allowed...",
            )
            App.Console.PrintError(msg)
            QMessageBox.critical(None, title, msg + "\n" + msg2)
            return

        # Proceed
        App.ActiveDocument.openTransaction("Texture_RemoveImage")
        image_names = [o.image for o in images]
        userinput, status = QInputDialog.getItem(
            None,
            translate("Render", "Texture Image Removal"),
            translate("Render", "Choose Image to remove:"),
            image_names,
            current=len(image_names) - 1,  # Default selection: last image
            editable=False,
        )
        if not status:
            return
        self.fpo.Proxy.remove_image(userinput)
        App.ActiveDocument.commitTransaction()