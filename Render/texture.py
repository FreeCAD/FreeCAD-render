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

from PySide.QtCore import QT_TRANSLATE_NOOP

from Render.base import FeatureBase, ViewProviderBase, Prop


class Texture(FeatureBase):
    """An object to add an image file as texture to a material."""

    VIEWPROVIDER = "ViewProviderTexture"

    PROPERTIES = {
        "Image": Prop(
            "App::PropertyFileIncluded",
            "Image",
            QT_TRANSLATE_NOOP("Render", "Texture Image File"),
            "",
        ),
        "Rotation": Prop(
            "App::PropertyAngle",
            "Mapping",
            QT_TRANSLATE_NOOP("Render", "UV rotation (in degrees)"),
            0,
        ),
        "ScaleU": Prop(
            "App::PropertyFloat",
            "Mapping",
            QT_TRANSLATE_NOOP("Render", "UV scale - U component"),
            0,
        ),
        "ScaleV": Prop(
            "App::PropertyFloat",
            "Mapping",
            QT_TRANSLATE_NOOP("Render", "UV scale - V component"),
            0,
        ),
        "TranslationU": Prop(
            "App::PropertyDistance",
            "Mapping",
            QT_TRANSLATE_NOOP("Render", "UV translation - U component"),
            0,
        ),
        "TranslationV": Prop(
            "App::PropertyDistance",
            "Mapping",
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


class ViewProviderTexture(ViewProviderBase):
    """View Provider of Texture class.

    (no Coin representation)
    """

    ICON = ""  # TODO
