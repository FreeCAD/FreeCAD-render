# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements lights objects for Render workbench.

Light objects allow to illuminate rendering scenes.
"""


# ===========================================================================
#                           Module imports
# ===========================================================================

import itertools
import math

from PySide.QtCore import QT_TRANSLATE_NOOP

from Render.base import (
    FeatureBase,
    PointableFeatureMixin,
    Prop,
    ViewProviderBase,
    PointableViewProviderMixin,
    CoinShapeViewProviderMixin,
    CoinPointLightViewProviderMixin,
    CoinDirectionalLightViewProviderMixin,
)
from Render.rdrhandler import RenderingTypes


# ===========================================================================
#                           Module functions
# ===========================================================================


def make_star(subdiv=8, radius=1):
    """Create a 3D star graph.

    In the created graph, every single vertex is connected to the center vertex
    and to nothing else.
    This graph is mainly used in point light graphical representation.
    """

    def cartesian(radius, theta, phi):
        return (
            radius * math.sin(theta) * math.cos(phi),
            radius * math.sin(theta) * math.sin(phi),
            radius * math.cos(theta),
        )

    rng_theta = [math.pi * i / subdiv for i in range(0, subdiv + 1)]
    rng_phi = [math.pi * i / subdiv for i in range(0, 2 * subdiv)]
    rng = itertools.product(rng_theta, rng_phi)
    pnts = [cartesian(radius, theta, phi) for theta, phi in rng]
    vecs = [x for y in zip(itertools.repeat((0, 0, 0)), pnts) for x in y]
    return vecs


# ===========================================================================
#                           Point Light object
# ===========================================================================


class PointLight(FeatureBase):
    """A point light object."""

    VIEWPROVIDER = "ViewProviderPointLight"

    # Note: Point light location is mainly controlled by its Location property.
    # However, to allow the use of Placement and Location features
    # (Edit-->Placement... & Edit-->Location...), a replicated underlying
    # Placement property is introduced, and some code has been added to keep it
    # constantly synchronized with Location.
    PROPERTIES = {
        "Location": Prop(
            "App::PropertyVector",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Location of light"),
            (0, 0, 15),
        ),
        "Color": Prop(
            "App::PropertyColor",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Color of light"),
            (1.0, 1.0, 1.0),
        ),
        "Power": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Rendering power"),
            60.0,
        ),
        "Radius": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Light representation radius.\n"
                "Note: This parameter has no impact "
                "on rendering",
            ),
            2.0,
        ),
    }

    ON_CHANGED = {
        "Location": "_on_changed_location",
        "Placement": "_on_changed_placement",
    }

    FCDTYPE = "App::GeometryPython"

    RENDERING_TYPE = RenderingTypes.POINTLIGHT

    def _on_changed_location(self, obj):  # pylint: disable=no-self-use
        """Respond to Location change event (by synchronizing Placement)."""
        if (
            "Placement" in obj.PropertiesList
            and obj.Placement.Base != obj.Location
        ):
            obj.Placement.Base = obj.Location

    def _on_changed_placement(self, obj):  # pylint: disable=no-self-use
        """Respond to Placement change event (by synchronizing Location)."""
        if (
            "Location" in obj.PropertiesList
            and obj.Location != obj.Placement.Base
        ):
            obj.Location = obj.Placement.Base

    def on_create_cb(self, fpo, viewp, **kwargs):
        """Complete the operation of 'create' (callback).

        Initialize Placement.
        """
        fpo.setEditorMode("Placement", 3)
        self._on_changed_location(fpo)


class ViewProviderPointLight(
    CoinPointLightViewProviderMixin,
    CoinShapeViewProviderMixin,
    ViewProviderBase,
):
    """View Provider of PointLight class."""

    ICON = "PointLight.svg"

    ON_UPDATE = {
        "Radius": "_update_radius",
    }

    COIN_SHAPE_POINTS = make_star(radius=1)
    COIN_SHAPE_VERTICES = [2] * (len(COIN_SHAPE_POINTS) // 2)
    COIN_SHAPE_WIREFRAME = True

    def _update_radius(self, fpo):
        """Update pointlight radius."""
        scale = [fpo.Radius] * 3
        self.coin.shape.set_scale(scale)


# ===========================================================================
#                           Area Light object
# ===========================================================================


class AreaLight(PointableFeatureMixin, FeatureBase):
    """An area light."""

    VIEWPROVIDER = "ViewProviderAreaLight"

    PROPERTIES = {
        "SizeU": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Size on U axis"),
            4.0,
        ),
        "SizeV": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Size on V axis"),
            2.0,
        ),
        "Color": Prop(
            "App::PropertyColor",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Color of light"),
            (1.0, 1.0, 1.0),
        ),
        "Power": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Rendering power"),
            60.0,
        ),
        "Transparent": Prop(
            "App::PropertyBool",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Area light transparency"),
            False,
        ),
    }

    RENDERING_TYPE = RenderingTypes.AREALIGHT


class ViewProviderAreaLight(
    CoinPointLightViewProviderMixin,
    CoinShapeViewProviderMixin,
    PointableViewProviderMixin,
    ViewProviderBase,
):
    """View Provider of AreaLight class."""

    ICON = "AreaLight.svg"

    ON_UPDATE = {
        "SizeU": "_update_size",
        "SizeV": "_update_size",
    }

    COIN_SHAPE_POINTS = (
        (-0.5, -0.5, 0.0),
        (+0.5, -0.5, 0.0),
        (+0.5, +0.5, 0.0),
        (-0.5, +0.5, 0.0),
        (-0.5, -0.5, 0.0),
    )
    COIN_SHAPE_VERTICES = [5]
    COIN_SHAPE_COLORS = ["diffuse", "emissive"]

    def _update_size(self, fpo):
        """Update arealight size."""
        scale = (fpo.SizeU, fpo.SizeV, 0)
        self.coin.shape.set_scale(scale)


# ===========================================================================
#                           Sunsky Light object
# ===========================================================================


class SunskyLight(FeatureBase):
    """A sun+sky light."""

    VIEWPROVIDER = "ViewProviderSunskyLight"

    PROPERTIES = {
        "SunDirection": Prop(
            "App::PropertyVector",
            "Light",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Direction of sun from observer's point of view "
                "-- (0,0,1) is zenith",
            ),
            (1, 1, 1),
        ),
        "Turbidity": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Atmospheric haziness (turbidity can go from 2.0 to 30+. 2-6 "
                "are most useful for clear days)",
            ),
            2.0,
        ),
        "GroundAlbedo": Prop(
            "App::PropertyFloatConstraint",
            "Light",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Ground albedo = reflection coefficient of the ground",
            ),
            (0.3, 0.0, 1.0, 0.01),
        ),
        "SunIntensity": Prop(
            "App::PropertyFloat",
            "Light - Advanced",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Factor to tune sun light intensity. Default at 1.0",
            ),
            1.0,
        ),
        "SkyIntensity": Prop(
            "App::PropertyFloat",
            "Light - Advanced",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Factor to tune sky light intensity. "
                "Default at 1.0. "
                "WARNING: not supported by Ospray.",
            ),
            1.0,
        ),
        # Cycles
        "CyclesModel": Prop(
            "App::PropertyEnumeration",
            chr(127) + "Specifics",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The model to use for sun & sky (Cycles only)",
            ),
            ("Nishita", "Hosek-Wilkie"),
            0,
        ),
        # Luxcore
        "LuxcoreGainPreset": Prop(
            "App::PropertyEnumeration",
            chr(127) + "Specifics",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The gain preset to use for sun & sky (Luxcore only):\n"
                "* 'Physical' yields accurate real light power, needing tone "
                "mapping or camera advanced settings\n"
                "* 'Mitigated' allows to render without tone mapping\n"
                "* 'Interior' is intended for interior scenes "
                "(through glass...)\n"
                "* 'Custom' gives full control on gain value",
            ),
            ("Mitigated", "Physical", "Interior", "Custom"),
            0,
        ),
        "LuxcoreCustomGain": Prop(
            "App::PropertyFloat",
            chr(127) + "Specifics",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The gain to use for sun & sky when preset gain "
                "is set to 'Custom' (Luxcore only)",
            ),
            1.0,
        ),
    }

    RENDERING_TYPE = RenderingTypes.SUNSKYLIGHT


class ViewProviderSunskyLight(
    CoinDirectionalLightViewProviderMixin, ViewProviderBase
):
    """View Provider of SunskyLight class."""

    ICON = "SunskyLight.svg"

    DISPLAY_MODES = ["Shaded", "Wireframe"]

    ON_UPDATE = {"SunDirection": "_update_sun_direction"}

    def _update_sun_direction(self, fpo):
        """Update sunsky light direction."""
        sundir = fpo.SunDirection
        direction = (-sundir.x, -sundir.y, -sundir.z)
        self.coin.light.set_direction(direction)


# ===========================================================================
#                           Image-Based Light object
# ===========================================================================


class ImageLight(FeatureBase):
    """An image-based light."""

    VIEWPROVIDER = "ViewProviderImageLight"

    PROPERTIES = {
        "ImageFile": Prop(
            "App::PropertyFileIncluded",
            "Light",
            QT_TRANSLATE_NOOP(
                "App::Property", "Image file (included in document)"
            ),
            "",
        ),
    }

    RENDERING_TYPE = RenderingTypes.IMAGELIGHT


class ViewProviderImageLight(ViewProviderBase):
    """View Provider of ImageLight class.

    (no Coin representation)
    """

    ICON = "ImageLight.svg"


# ===========================================================================
#                           Distant Light object
# ===========================================================================


class DistantLight(FeatureBase):
    """An distant light."""

    VIEWPROVIDER = "ViewProviderDistantLight"

    PROPERTIES = {
        "Color": Prop(
            "App::PropertyColor",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Color of light"),
            (1.0, 1.0, 1.0),
        ),
        "Power": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP("App::Property", "Rendering power"),
            5.0,
        ),
        "Direction": Prop(
            "App::PropertyVector",
            "Light",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Direction of light from light's point of view ",
            ),
            (-1, 1, -1),
        ),
        "Angle": Prop(
            "App::PropertyAngle",
            chr(127) + "Specifics",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Apparent size of the light source, as an angle. "
                "Must be > 0 for soft shadows.\n"
                "Not all renderers support this parameter, please refer to "
                "your renderer's documentation.",
            ),
            0,
        ),
    }

    RENDERING_TYPE = RenderingTypes.DISTANTLIGHT


class ViewProviderDistantLight(
    CoinDirectionalLightViewProviderMixin, ViewProviderBase
):
    """View Provider of DistantLight class."""

    ICON = "DistantLight.svg"

    DISPLAY_MODES = ["Shaded", "Wireframe"]

    ON_UPDATE = {"Direction": "_update_direction"}

    def _update_direction(self, fpo):
        """Update sunsky light direction."""
        direction = fpo.Direction
        self.coin.light.set_direction(direction)
