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


from types import SimpleNamespace
import itertools
import math

from pivy import coin
from PySide.QtCore import QT_TRANSLATE_NOOP
import FreeCAD as App
import FreeCADGui as Gui

from Render.base import (
    BaseFeature,
    Prop,
    BaseViewProvider,
    PointableFeatureMixin,
    PointableViewProviderMixin,
)


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


class PointLight(BaseFeature):
    """A point light object."""

    VIEWPROVIDER = "ViewProviderPointLight"

    PROPERTIES = {
        "Location": Prop(
            "App::PropertyVector",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Location of light"),
            App.Vector(0, 0, 15),
        ),
        "Color": Prop(
            "App::PropertyColor",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Color of light"),
            (1.0, 1.0, 1.0),
        ),
        "Power": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Rendering power"),
            60.0,
        ),
        "Radius": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP(
                "Render",
                "Light representation radius.\n"
                "Note: This parameter has no impact "
                "on rendering",
            ),
            2.0,
        ),
    }


class ViewProviderPointLight(BaseViewProvider):
    """View Provider of PointLight class."""

    SHAPE = make_star(radius=1)

    ICON = "PointLight.svg"

    DISPLAY_MODES = ["Shaded", "Wireframe"]

    ON_CHANGED = {"Visibility": "_change_visibility"}

    ON_UPDATE = {
        "Location": "_update_location",
        "Power": "_update_power",
        "Color": "_update_color",
        "Radius": "_update_radius",
    }

    def on_attach_cb(self, vobj):
        """Complete 'attach' method (callback)."""
        # Here we create coin representation, which is in 2 parts: a light,
        # and a geometry (the latter being a lineset embedded inside a switch)

        # pylint: disable=attribute-defined-outside-init
        self.coin = SimpleNamespace()
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()

        # Create pointlight in scenegraph
        self.coin.light = coin.SoPointLight()
        scene.insertChild(self.coin.light, 0)  # Insert frontwise

        # Create geometry in scenegraph
        self.coin.geometry = coin.SoSwitch()

        self.coin.node = coin.SoSeparator()
        self.coin.transform = coin.SoTransform()
        self.coin.node.addChild(self.coin.transform)
        self.coin.material = coin.SoMaterial()
        self.coin.node.addChild(self.coin.material)
        self.coin.drawstyle = coin.SoDrawStyle()
        self.coin.drawstyle.style = coin.SoDrawStyle.LINES
        self.coin.drawstyle.lineWidth = 1
        self.coin.drawstyle.linePattern = 0xAAAA
        self.coin.node.addChild(self.coin.drawstyle)
        self.coin.coords = coin.SoCoordinate3()
        self.coin.coords.point.setValues(0, len(self.SHAPE), self.SHAPE)
        self.coin.node.addChild(self.coin.coords)
        self.coin.lineset = coin.SoLineSet()
        self.coin.lineset.numVertices.setValues(
            0, len(self.SHAPE) // 2, [2] * (len(self.SHAPE) // 2)
        )
        self.coin.node.addChild(self.coin.lineset)

        self.coin.geometry.addChild(self.coin.node)
        self.coin.geometry.whichChild.setValue(coin.SO_SWITCH_ALL)
        scene.addChild(self.coin.geometry)  # Insert back
        vobj.addDisplayMode(self.coin.geometry, "Shaded")

        # Update coin elements with actual object properties
        self._update_location(self.fpo)
        self._update_color(self.fpo)
        self._update_power(self.fpo)
        self._update_radius(self.fpo)

    def onDelete(self, feature, subelements):
        """Respond to delete object event (callback)."""
        # Delete coin representation
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        scene.removeChild(self.coin.geometry)
        scene.removeChild(self.coin.light)
        return True  # If False, the object wouldn't be deleted

    def _change_visibility(self, vpdo):
        """Change light visibility."""
        self.coin.light.on.setValue(vpdo.Visibility)
        self.coin.geometry.whichChild = (
            coin.SO_SWITCH_ALL if vpdo.Visibility else coin.SO_SWITCH_NONE
        )

    def _update_location(self, fpo):
        """Update pointlight location."""
        location = fpo.Location[:3]
        self.coin.transform.translation.setValue(location)
        self.coin.light.location.setValue(location)

    def _update_power(self, fpo):
        """Update pointlight power."""
        intensity = fpo.Power / 100 if fpo.Power <= 100 else 1
        self.coin.light.intensity.setValue(intensity)

    def _update_color(self, fpo):
        """Update pointlight color."""
        color = fpo.Color[:3]
        self.coin.material.diffuseColor.setValue(color)
        self.coin.light.color.setValue(color)

    def _update_radius(self, fpo):
        """Update pointlight radius."""
        scale = [fpo.Radius] * 3
        self.coin.transform.scaleFactor.setValue(scale)


# ===========================================================================
#                           Area Light object
# ===========================================================================


class AreaLight(PointableFeatureMixin, BaseFeature):
    """An area light."""

    VIEWPROVIDER = "ViewProviderAreaLight"

    PROPERTIES = {
        "SizeU": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Size on U axis"),
            4.0,
        ),
        "SizeV": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Size on V axis"),
            2.0,
        ),
        "Color": Prop(
            "App::PropertyColor",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Color of light"),
            (1.0, 1.0, 1.0),
        ),
        "Power": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Rendering power"),
            60.0,
        ),
        "Transparent": Prop(
            "App::PropertyBool",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Area light transparency"),
            False,
        ),
    }


class ViewProviderAreaLight(PointableViewProviderMixin, BaseViewProvider):
    """View Provider of AreaLight class."""

    ICON = "AreaLight.svg"

    DISPLAY_MODES = ["Shaded", "Wireframe"]

    ON_CHANGED = {"Visibility": "_change_visibility"}

    ON_UPDATE = {
        "Power": "_update_power",
        "Color": "_update_color",
        "SizeU": "_update_size",
        "SizeV": "_update_size",
    }

    SHAPE = (
        (-0.5, -0.5, 0),
        (0.5, -0.5, 0),
        (0.5, 0.5, 0),
        (-0.5, 0.5, 0),
        (-0.5, -0.5, 0),
    )

    def on_attach_cb(self, vobj):
        """Complete 'attach' method (callback)."""
        # Here we create coin representation, which is in 2 parts: a light,
        # and a geometry, the former being a point light, the latter being a
        # faceset embedded in a switch)

        # pylint: disable=attribute-defined-outside-init
        self.coin = SimpleNamespace()
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()

        # Create pointlight in scenegraph
        self.coin.light = coin.SoPointLight()
        scene.insertChild(self.coin.light, 0)  # Insert frontwise

        # Create geometry in scenegraph
        self.coin.geometry = coin.SoSwitch()
        self.coin.node = coin.SoSeparator()
        self.coin.transform = coin.SoTransform()
        self.coin.node.addChild(self.coin.transform)
        self.coin.material = coin.SoMaterial()
        self.coin.node.addChild(self.coin.material)
        self.coin.drawstyle = coin.SoDrawStyle()
        self.coin.drawstyle.style = coin.SoDrawStyle.FILLED
        self.coin.node.addChild(self.coin.drawstyle)
        self.coin.coords = coin.SoCoordinate3()
        self.coin.coords.point.setValues(0, len(self.SHAPE), self.SHAPE)
        self.coin.node.addChild(self.coin.coords)
        self.coin.faceset = coin.SoFaceSet()
        self.coin.faceset.numVertices.setValues(0, 1, [5])
        self.coin.node.addChild(self.coin.faceset)

        self.coin.geometry.addChild(self.coin.node)
        self.coin.geometry.whichChild.setValue(coin.SO_SWITCH_ALL)
        scene.addChild(self.coin.geometry)  # Insert back
        vobj.addDisplayMode(self.coin.geometry, "Shaded")

        # Update coin elements with actual object properties
        self.update_all(self.fpo)

    def onDelete(self, feature, subelements):
        """Respond to delete object event (callback)."""
        # Delete coin representation
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        scene.removeChild(self.coin.geometry)
        scene.removeChild(self.coin.light)
        return True  # If False, the object wouldn't be deleted

    def _update_placement(self, fpo):
        """Update object placement."""
        super()._update_placement(fpo)
        self.coin.light.location.setValue(fpo.Placement.Base[:3])

    def _change_visibility(self, vpdo):
        """Change light visibility."""
        self.coin.light.on.setValue(vpdo.Visibility)
        self.coin.geometry.whichChild = (
            coin.SO_SWITCH_ALL if vpdo.Visibility else coin.SO_SWITCH_NONE
        )

    def _update_power(self, fpo):
        """Update arealight power."""
        intensity = fpo.Power / 100 if fpo.Power <= 100 else 1
        self.coin.light.intensity.setValue(intensity)

    def _update_color(self, fpo):
        """Update arealight color."""
        color = fpo.Color[:3]
        self.coin.material.emissiveColor.setValue(color)
        self.coin.material.diffuseColor.setValue(color)
        self.coin.light.color.setValue(color)

    def _update_size(self, fpo):
        """Update arealight size."""
        size = (fpo.SizeU, fpo.SizeV, 0)
        self.coin.transform.scaleFactor.setValue(size)


# ===========================================================================
#                           Sunsky Light object
# ===========================================================================


class SunskyLight(BaseFeature):
    """A sun+sky light - Hosek-Wilkie."""

    VIEWPROVIDER = "ViewProviderSunskyLight"

    PROPERTIES = {
        "SunDirection": Prop(
            "App::PropertyVector",
            "Light",
            QT_TRANSLATE_NOOP(
                "Render",
                "Direction of sun from observer's point of view "
                "-- (0,0,1) is zenith",
            ),
            App.Vector(1, 1, 1),
        ),
        "Turbidity": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP(
                "Render",
                "Atmospheric haziness (turbidity can go from 2.0 to 30+. 2-6 "
                "are most useful for clear days)",
            ),
            2.0,
        ),
        "GroundAlbedo": Prop(
            "App::PropertyFloatConstraint",
            "Light",
            QT_TRANSLATE_NOOP(
                "Render",
                "Ground albedo (reflection coefficient of the ground)",
            ),
            (0.3, 0.0, 1.0, 0.01),
        ),
    }


class ViewProviderSunskyLight(BaseViewProvider):
    """View Provider of SunskyLight class."""

    ICON = "SunskyLight.svg"

    DISPLAY_MODES = ["Shaded", "Wireframe"]

    ON_CHANGED = {"Visibility": "_change_visibility"}

    ON_UPDATE = {"SunDirection": "_update_direction"}

    def on_attach_cb(self, vobj):
        """Complete 'attach' method (callback)."""
        # Here we create coin representation, which is a directional light

        # pylint: disable=attribute-defined-outside-init
        self.coin = SimpleNamespace()
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()

        # Create pointlight in scenegraph
        self.coin.light = coin.SoDirectionalLight()
        scene.insertChild(self.coin.light, 0)  # Insert frontwise
        vobj.addDisplayMode(self.coin.light, "Shaded")

    def onDelete(self, feature, subelements):
        """Respond to delete object event (callback)."""
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        scene.removeChild(self.coin.light)
        return True  # If False, the object wouldn't be deleted

    def _change_visibility(self, vpdo):
        """Change light visibility."""
        self.coin.light.on.setValue(vpdo.Visibility)

    def _update_direction(self, fpo):
        """Update sunsky light direction."""
        sundir = fpo.SunDirection
        direction = (-sundir.x, -sundir.y, -sundir.z)
        self.coin.light.direction.setValue(direction)


# ===========================================================================
#                           Image-Based Light object
# ===========================================================================


class ImageLight(BaseFeature):
    """An image-based light."""

    VIEWPROVIDER = "ViewProviderImageLight"

    PROPERTIES = {
        "ImageFile": Prop(
            "App::PropertyFileIncluded",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Image file (included in document)"),
            "",
        ),
    }


class ViewProviderImageLight(BaseViewProvider):
    """View Provider of ImageLight class."""

    ICON = "ImageLight.svg"

    DISPLAY_MODES = ["Shaded", "Wireframe"]

    def on_attach_cb(self, vobj):
        """Complete 'attach' method (callback)."""
        # Here we create coin representation
        # NB: Coin representation is blank, as Coin does not handle
        # image-based lighting (the node is a dummy SoInfo)

        # pylint: disable=attribute-defined-outside-init
        self.coin = SimpleNamespace()
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        self.coin.dummy = coin.SoInfo()
        scene.addChild(self.coin.dummy)
        vobj.addDisplayMode(self.coin.dummy, "Shaded")
