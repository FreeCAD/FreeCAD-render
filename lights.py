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

"""This module implements lights objects, which allow to illuminate rendering
scenes"""


# ===========================================================================
#                           Module imports
# ===========================================================================


from collections import namedtuple
from types import SimpleNamespace
from os import path
import itertools
import math

from pivy import coin
from PySide.QtGui import QAction
from PySide.QtCore import QT_TRANSLATE_NOOP, QObject, SIGNAL
import FreeCAD as App
import FreeCADGui as Gui


# ===========================================================================
#                           Module functions
# ===========================================================================


def make_star(subdiv=8, radius=1):
    """Creates a 3D star graph, in which every single vertex is connected
    to the center vertex and nobody else."""

    def cartesian(radius, theta, phi):
        return (radius * math.sin(theta) * math.cos(phi),
                radius * math.sin(theta) * math.sin(phi),
                radius * math.cos(theta))

    rng_theta = [math.pi * i / subdiv for i in range(0, subdiv + 1)]
    rng_phi = [math.pi * i / subdiv for i in range(0, 2 * subdiv)]
    rng = itertools.product(rng_theta, rng_phi)
    pnts = [cartesian(radius, theta, phi) for theta, phi in rng]
    vecs = [x for y in zip(itertools.repeat((0, 0, 0)), pnts) for x in y]
    return vecs


# ===========================================================================
#                           Point Light object
# ===========================================================================


class PointLight:
    """A point light"""

    Prop = namedtuple('Prop', ['Type', 'Group', 'Doc', 'Default'])

    # FeaturePython object properties
    PROPERTIES = {
        "Location": Prop(
            "App::PropertyVector",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Location of light"),
            App.Vector(0, 0, 15)),

        "Color": Prop(
            "App::PropertyColor",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Color of light"),
            (1.0, 1.0, 1.0)),

        "Power": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Rendering power"),
            60.0),

        "Radius": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Light representation radius.\n"
                                        "Note: This parameter has no impact "
                                        "on rendering"),
            2.0),

    }
    # ~FeaturePython object properties

    def __init__(self, fpo):
        """PointLight initializer

        Parameters
        ----------
        fpo: a FeaturePython object created with FreeCAD.addObject
        """
        self.type = "PointLight"
        fpo.Proxy = self
        self.set_properties(fpo)

    @classmethod
    def set_properties(cls, fpo):
        """Set underlying FeaturePython object's properties"""
        for name in cls.PROPERTIES.keys() - set(fpo.PropertiesList):
            spec = cls.PROPERTIES[name]
            prop = fpo.addProperty(spec.Type, name, spec.Group, spec.Doc, 0)
            setattr(prop, name, spec.Default)

    @staticmethod
    def create(document=None):
        """Create a PointLight object in a document

        Factory method to create a new pointlight object.
        The light is created into the active document (default).
        Optionally, it is possible to specify a target document, in that case
        the light is created in the given document.

        This method also create the FeaturePython and the
        ViewProviderPointLight related objects.

        Params:
        document: the document where to create pointlight (optional)

        Returns:
        The newly created PointLight object, FeaturePython object and
        ViewProviderPointLight object"""

        doc = document if document else App.ActiveDocument
        fpo = doc.addObject("App::FeaturePython", "PointLight")
        lgt = PointLight(fpo)
        viewp = ViewProviderPointLight(fpo.ViewObject)
        App.ActiveDocument.recompute()
        return lgt, fpo, viewp

    def onDocumentRestored(self, fpo):
        """Callback triggered when document is restored"""
        self.type = "PointLight"
        fpo.Proxy = self
        self.set_properties(fpo)

    def execute(self, fpo):
        # pylint: disable=no-self-use
        """Callback triggered on document recomputation (mandatory)."""


class ViewProviderPointLight:
    """View Provider of PointLight class"""

    SHAPE = make_star(radius=1)

    def __init__(self, vobj):
        """Initializer

        Parameters:
        -----------
        vobj: related ViewProviderDocumentObject
        """
        vobj.Proxy = self
        self.fpo = vobj.Object  # Related FeaturePython object

    def attach(self, vobj):
        """Code executed when object is created/restored (callback)

        Parameters:
        -----------
        vobj: related ViewProviderDocumentObject
        """
        # pylint: disable=attribute-defined-outside-init

        self.fpo = vobj.Object
        PointLight.set_properties(self.fpo)

        # Here we create coin representation, which is in 2 parts: a light,
        # and a geometry (the latter being a lineset embedded inside a switch)
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
        self.coin.drawstyle.linePattern = 0xaaaa
        self.coin.node.addChild(self.coin.drawstyle)
        self.coin.coords = coin.SoCoordinate3()
        self.coin.coords.point.setValues(0, len(self.SHAPE), self.SHAPE)
        self.coin.node.addChild(self.coin.coords)
        self.coin.lineset = coin.SoLineSet()
        self.coin.lineset.numVertices.setValues(
            0, len(self.SHAPE) // 2, [2] * (len(self.SHAPE) // 2))
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
        """Code executed when object is deleted (callback)"""
        # Delete coin representation
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        scene.removeChild(self.coin.geometry)
        scene.removeChild(self.coin.light)
        return True  # If False, the object wouldn't be deleted

    def getDisplayModes(self, _):
        # pylint: disable=no-self-use
        """Return a list of display modes (callback)"""
        return ["Shaded", "Wireframe"]

    def getDefaultDisplayMode(self):
        # pylint: disable=no-self-use
        """Return the name of the default display mode (callback)

        The returned mode must be defined in getDisplayModes.
        """
        return "Shaded"

    def setDisplayMode(self, mode):
        # pylint: disable=no-self-use
        """Map the display mode defined in attach with those defined in
        getDisplayModes (callback)

        Since they have the same names nothing needs to be done.
        This method is optional.
        """
        return mode

    def getIcon(self):
        # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)"""
        return path.join(path.dirname(__file__), "icons", "PointLight.svg")

    def onChanged(self, vpdo, prop):
        """Code executed when a ViewProvider's property got modified (callback)

        Parameters:
        -----------
        vpdo: related ViewProviderDocumentObject (where properties are stored)
        prop: property name (as a string)
        """
        if prop == "Visibility":
            self.coin.light.on.setValue(vpdo.Visibility)
            self.coin.geometry.whichChild =\
                coin.SO_SWITCH_ALL if vpdo.Visibility else coin.SO_SWITCH_NONE

    def updateData(self, fpo, prop):
        """Code executed when a FeaturePython's property got modified
        (callback)

        Parameters:
        -----------
        fpo: related FeaturePython object
        prop: property name
        """
        switcher = {
            "Location": ViewProviderPointLight._update_location,
            "Power": ViewProviderPointLight._update_power,
            "Color": ViewProviderPointLight._update_color,
            "Radius": ViewProviderPointLight._update_radius,
        }

        try:
            update_method = switcher[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            update_method(self, fpo)

    def _update_location(self, fpo):
        """Update pointlight location"""
        location = fpo.Location[:3]
        self.coin.transform.translation.setValue(location)
        self.coin.light.location.setValue(location)

    def _update_power(self, fpo):
        """Update pointlight power"""
        intensity = fpo.Power / 100 if fpo.Power <= 100 else 1
        self.coin.light.intensity.setValue(intensity)

    def _update_color(self, fpo):
        """Update pointlight color"""
        color = fpo.Color[:3]
        self.coin.material.diffuseColor.setValue(color)
        self.coin.light.color.setValue(color)

    def _update_radius(self, fpo):
        """Update pointlight radius"""
        scale = [fpo.Radius] * 3
        self.coin.transform.scaleFactor.setValue(scale)

    def __getstate__(self):
        """Called while saving the document"""
        return None

    def __setstate__(self, state):
        """Called while restoring document"""
        return None


# ===========================================================================
#                           Area Light object
# ===========================================================================


class AreaLight:
    """An area light"""

    Prop = namedtuple('Prop', ['Type', 'Group', 'Doc', 'Default'])

    # FeaturePython object properties
    PROPERTIES = {
        "Placement": Prop(
            "App::PropertyPlacement",
            "",
            QT_TRANSLATE_NOOP("Render", "Placement of camera"),
            App.Placement(App.Vector(0, 0, 0),
                          App.Vector(0, 0, 1),
                          0)),

        "SizeU": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Size on U axis"),
            4.0),

        "SizeV": Prop(
            "App::PropertyLength",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Size on V axis"),
            2.0),

        "Color": Prop(
            "App::PropertyColor",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Color of light"),
            (1.0, 1.0, 1.0)),

        "Power": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP("Render", "Rendering power"),
            60.0),

    }
    # ~FeaturePython object properties

    _fpos = dict()  # FeaturePython objects

    def __init__(self, fpo):
        """AreaLight initializer

        Parameters
        ----------
        fpo: a FeaturePython object created with FreeCAD.addObject
        """
        self.type = "AreaLight"
        fpo.Proxy = self
        self.fpo = fpo
        self.set_properties(fpo)

    @property
    def fpo(self):
        """Underlying FeaturePython object getter"""
        return self._fpos[id(self)]

    @fpo.setter
    def fpo(self, new_fpo):
        """Underlying FeaturePython object setter"""
        self._fpos[id(self)] = new_fpo

    @classmethod
    def set_properties(cls, fpo):
        """Set underlying FeaturePython object's properties"""
        for name in cls.PROPERTIES.keys() - set(fpo.PropertiesList):
            spec = cls.PROPERTIES[name]
            prop = fpo.addProperty(spec.Type, name, spec.Group, spec.Doc, 0)
            setattr(prop, name, spec.Default)

    @staticmethod
    def create(document=None):
        """Create an AreaLight object in a document

        Factory method to create a new arealight object.
        The light is created into the active document (default).
        Optionally, it is possible to specify a target document, in that case
        the light is created in the given document.

        This method also create the FeaturePython and the
        ViewProvider related objects.

        Params:
        document: the document where to create arealight (optional)

        Returns:
        The newly created PointLight object, FeaturePython object and
        ViewProvider object"""

        doc = document if document else App.ActiveDocument
        fpo = doc.addObject("App::FeaturePython", "AreaLight")
        lgt = AreaLight(fpo)
        viewp = ViewProviderAreaLight(fpo.ViewObject)
        App.ActiveDocument.recompute()
        return lgt, fpo, viewp

    def onDocumentRestored(self, fpo):
        """Callback triggered when document is restored"""
        self.type = "AreaLight"
        fpo.Proxy = self
        self.fpo = fpo
        self.set_properties(fpo)

    def execute(self, fpo):
        # pylint: disable=no-self-use
        """Callback triggered on document recomputation (mandatory)."""

    def point_at(self, point):
        """Make Area light point at a given target point

        Parameters:
        -----------
        point -- point to point at (must have x, y, z properties)
        """
        fpo = self.fpo
        current_normal = fpo.Placement.Rotation.multVec(App.Vector(0, 0, 1))
        base = fpo.Placement.Base
        new_normal = App.Vector(point.x - base.x,
                                point.y - base.y,
                                point.z - base.z)
        axis = current_normal.cross(new_normal)
        if not axis.Length:
            # Don't try to rotate if axis is a null vector...
            return
        angle = math.degrees(new_normal.getAngle(current_normal))
        rotation = App.Rotation(axis, angle)
        fpo.Placement.Rotation = rotation.multiply(fpo.Placement.Rotation)


class ViewProviderAreaLight:
    """View Provider of PointLight class"""

    SHAPE = ((-0.5, -0.5, 0),
             (0.5, -0.5, 0),
             (0.5, 0.5, 0),
             (-0.5, 0.5, 0),
             (-0.5, -0.5, 0))

    def __init__(self, vobj):
        """Initializer

        Parameters:
        -----------
        vobj: related ViewProviderDocumentObject
        """
        vobj.Proxy = self
        self.fpo = vobj.Object  # Related FeaturePython object
        self.callback = None  # For point_at method

    def attach(self, vobj):
        """Code executed when object is created/restored (callback)

        Parameters:
        -----------
        vobj: related ViewProviderDocumentObject
        """
        # pylint: disable=attribute-defined-outside-init

        self.fpo = vobj.Object
        AreaLight.set_properties(self.fpo)

        # Here we create coin representation, which is in 2 parts: a light,
        # and a geometry, the former being a point light, the latter being a
        # faceset embedded in a switch)

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
        self._update_placement(self.fpo)
        self._update_color(self.fpo)
        self._update_power(self.fpo)
        self._update_size(self.fpo)

    def onDelete(self, feature, subelements):
        """Code executed when object is deleted (callback)"""
        # Delete coin representation
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        scene.removeChild(self.coin.geometry)
        scene.removeChild(self.coin.light)
        return True  # If False, the object wouldn't be deleted

    def getDisplayModes(self, _):
        # pylint: disable=no-self-use
        """Return a list of display modes (callback)"""
        return ["Shaded", "Wireframe"]

    def getDefaultDisplayMode(self):
        # pylint: disable=no-self-use
        """Return the name of the default display mode (callback)

        The returned mode must be defined in getDisplayModes.
        """
        return "Shaded"

    def setDisplayMode(self, mode):
        # pylint: disable=no-self-use
        """Map the display mode defined in attach with those defined in
        getDisplayModes (callback)

        Since they have the same names nothing needs to be done.
        This method is optional.
        """
        return mode

    def getIcon(self):
        # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)"""
        return path.join(path.dirname(__file__), "icons", "AreaLight.svg")

    def onChanged(self, vpdo, prop):
        """Code executed when a ViewProvider's property got modified (callback)

        Parameters:
        -----------
        vpdo: related ViewProviderDocumentObject (where properties are stored)
        prop: property name (as a string)
        """
        if prop == "Visibility":
            self.coin.light.on.setValue(vpdo.Visibility)
            self.coin.geometry.whichChild =\
                coin.SO_SWITCH_ALL if vpdo.Visibility else coin.SO_SWITCH_NONE

    def setupContextMenu(self, vobj, menu):
        """Setup the context menu associated to the object in tree view
        (callback)
        """
        action1 = QAction(QT_TRANSLATE_NOOP("Render",
                                            "Point at..."),
                          menu)
        QObject.connect(action1,
                        SIGNAL("triggered()"),
                        self.point_at)
        menu.addAction(action1)

    def updateData(self, fpo, prop):
        """Code executed when a FeaturePython's property got modified
        (callback)

        Parameters:
        -----------
        fpo: related FeaturePython object
        prop: property name
        """
        switcher = {
            "Placement": ViewProviderAreaLight._update_placement,
            "Power": ViewProviderAreaLight._update_power,
            "Color": ViewProviderAreaLight._update_color,
            "SizeU": ViewProviderAreaLight._update_size,
            "SizeV": ViewProviderAreaLight._update_size,
        }

        try:
            update_method = switcher[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            update_method(self, fpo)

    def _update_placement(self, fpo):
        """Update arealight location"""
        location = fpo.Placement.Base[:3]
        self.coin.transform.translation.setValue(location)
        angle = float(fpo.Placement.Rotation.Angle)
        axis = coin.SbVec3f(fpo.Placement.Rotation.Axis)
        self.coin.transform.rotation.setValue(axis, angle)
        self.coin.light.location.setValue(location)

    def _update_power(self, fpo):
        """Update arealight power"""
        intensity = fpo.Power / 100 if fpo.Power <= 100 else 1
        self.coin.light.intensity.setValue(intensity)

    def _update_color(self, fpo):
        """Update arealight color"""
        color = fpo.Color[:3]
        self.coin.material.emissiveColor.setValue(color)
        self.coin.material.diffuseColor.setValue(color)
        self.coin.light.color.setValue(color)

    def _update_size(self, fpo):
        """Update arealight size"""
        size = (fpo.SizeU, fpo.SizeV, 0)
        self.coin.transform.scaleFactor.setValue(size)

    def point_at(self):
        """Make this area light point at another object

        User will be requested to select an object to point at"""
        msg = QT_TRANSLATE_NOOP("Render",
                                "[Point at] Please select target "
                                "(on geometry)\n")
        App.Console.PrintMessage(msg)
        self.callback = Gui.ActiveDocument.ActiveView.addEventCallbackPivy(
            coin.SoMouseButtonEvent.getClassTypeId(),
            self._point_at_cb)

    def _point_at_cb(self, event_cb):
        """Point at callback

        Parameters:
        event_cb -- coin event callback object
        """
        event = event_cb.getEvent()
        if (event.getState() == coin.SoMouseButtonEvent.DOWN and
                event.getButton() == coin.SoMouseButtonEvent.BUTTON1):
            # Get point
            picked_point = event_cb.getPickedPoint()
            try:
                point = App.Vector(picked_point.getPoint())
            except AttributeError:
                # No picked point (outside geometry)
                msg = QT_TRANSLATE_NOOP("Render",
                                        "[Point at] Target outside geometry "
                                        "-- Aborting\n")
                App.Console.PrintMessage(msg)
            else:
                # Make underlying object point at target point
                self.fpo.Proxy.point_at(point)
                msg = QT_TRANSLATE_NOOP("Render",
                                        "[Point at] Now pointing at "
                                        "({0.x}, {0.y}, {0.z})\n")
                App.Console.PrintMessage(msg.format(point))
            finally:
                # Remove coin event catcher
                Gui.ActiveDocument.ActiveView.removeEventCallbackPivy(
                    coin.SoMouseButtonEvent.getClassTypeId(), self.callback)

    def __getstate__(self):
        """Called while saving the document"""
        return None

    def __setstate__(self, state):
        """Called while restoring document"""
        return None


# ===========================================================================
#                           Sunsky Light object
# ===========================================================================


class SunskyLight:
    """A sunsky light - Hosek-Wilkie"""

    Prop = namedtuple('Prop', ['Type', 'Group', 'Doc', 'Default'])

    # FeaturePython object properties
    PROPERTIES = {
        "SunDirection": Prop(
            "App::PropertyVector",
            "Light",
            QT_TRANSLATE_NOOP(
                "Render",
                "Direction of sun from observer's point of view "
                "-- (0,0,1) is zenith"),
            App.Vector(0, 0, -1)),

        "Turbidity": Prop(
            "App::PropertyFloat",
            "Light",
            QT_TRANSLATE_NOOP(
                "Render",
                "Atmospheric haziness (turbidity can go from 2.0 to 30+. 2-6 "
                "are most useful for clear days)"),
            2.0),
    }
    # ~FeaturePython object properties

    def __init__(self, fpo):
        """PointLight initializer

        Parameters
        ----------
        fpo: a FeaturePython object created with FreeCAD.addObject
        """
        self.type = "SunskyLight"
        fpo.Proxy = self
        self.set_properties(fpo)

    @classmethod
    def set_properties(cls, fpo):
        """Set underlying FeaturePython object's properties"""
        for name in cls.PROPERTIES.keys() - set(fpo.PropertiesList):
            spec = cls.PROPERTIES[name]
            prop = fpo.addProperty(spec.Type, name, spec.Group, spec.Doc, 0)
            setattr(prop, name, spec.Default)

    @staticmethod
    def create(document=None):
        """Create a SunskyLight object in a document

        Factory method to create a new sunsky light object.
        The light is created into the active document (default).
        Optionally, it is possible to specify a target document, in that case
        the light is created in the given document.

        This method also create the FeaturePython and the
        ViewProviderPointLight related objects.

        Params:
        document: the document where to create pointlight (optional)

        Returns:
        The newly created SunskyLight object, FeaturePython object and
        ViewProviderSunskyLight object"""

        doc = document if document else App.ActiveDocument
        fpo = doc.addObject("App::FeaturePython", "SunskyLight")
        lgt = SunskyLight(fpo)
        viewp = ViewProviderSunskyLight(fpo.ViewObject)
        App.ActiveDocument.recompute()
        return lgt, fpo, viewp

    def onDocumentRestored(self, fpo):
        """Callback triggered when document is restored"""
        self.type = "SunskyLight"
        fpo.Proxy = self
        self.set_properties(fpo)

    def execute(self, fpo):
        # pylint: disable=no-self-use
        """Callback triggered on document recomputation (mandatory)."""


class ViewProviderSunskyLight:
    """View Provider of SunskyLight class"""

    def __init__(self, vobj):
        """Initializer

        Parameters:
        -----------
        vobj: related ViewProviderDocumentObject
        """
        vobj.Proxy = self
        self.fpo = vobj.Object  # Related FeaturePython object

    def attach(self, vobj):
        """Code executed when object is created/restored (callback)

        Parameters:
        -----------
        vobj: related ViewProviderDocumentObject
        """
        # pylint: disable=attribute-defined-outside-init

        self.fpo = vobj.Object
        SunskyLight.set_properties(self.fpo)

        # Here we create coin representation, which is a directional light,

        self.coin = SimpleNamespace()
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()

        # Create pointlight in scenegraph
        self.coin.light = coin.SoDirectionalLight()
        scene.insertChild(self.coin.light, 0)  # Insert frontwise
        vobj.addDisplayMode(self.coin.light, "Shaded")

    def onDelete(self, feature, subelements):
        """Code executed when object is deleted (callback)"""
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        scene.removeChild(self.coin.light)
        return True  # If False, the object wouldn't be deleted

    def getDisplayModes(self, _):
        # pylint: disable=no-self-use
        """Return a list of display modes (callback)"""
        return ["Shaded", "Wireframe"]

    def getDefaultDisplayMode(self):
        # pylint: disable=no-self-use
        """Return the name of the default display mode (callback)

        The returned mode must be defined in getDisplayModes.
        """
        return "Shaded"

    def setDisplayMode(self, mode):
        # pylint: disable=no-self-use
        """Map the display mode defined in attach with those defined in
        getDisplayModes (callback)

        Since they have the same names nothing needs to be done.
        This method is optional.
        """
        return mode

    def setupContextMenu(self, vobj, menu):
        # pylint: disable=no-self-use
        """Setup the context menu associated to the object in tree view
        (callback)
        """

    def getIcon(self):
        # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)"""
        return path.join(path.dirname(__file__), "icons", "SunskyLight.svg")

    def onChanged(self, vpdo, prop):
        """Code executed when a ViewProvider's property got modified (callback)

        Parameters:
        -----------
        vpdo: related ViewProviderDocumentObject (where properties are stored)
        prop: property name (as a string)
        """
        if prop == "Visibility":
            self.coin.light.on.setValue(vpdo.Visibility)

    def updateData(self, fpo, prop):
        """Code executed when a FeaturePython's property got modified
        (callback)

        Parameters:
        -----------
        fpo: related FeaturePython object
        prop: property name
        """
        switcher = {
            "SunDirection": ViewProviderSunskyLight._update_direction,
        }

        try:
            update_method = switcher[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            update_method(self, fpo)

    def _update_direction(self, fpo):
        """Update sunsky light direction"""
        sundir = fpo.SunDirection
        direction = (-sundir.x, -sundir.y, -sundir.z)
        self.coin.light.direction.setValue(direction)

    def __getstate__(self):
        """Called while saving the document"""
        return None

    def __setstate__(self, state):
        """Called while restoring document"""
        return None
