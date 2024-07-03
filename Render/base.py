# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
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

"""This module implements base classes for Render workbench."""

from collections import namedtuple
from types import SimpleNamespace
from math import degrees
import functools
import itertools
import sys
import os

from pivy import coin
import FreeCAD as App
import FreeCADGui as Gui
from PySide.QtGui import QAction, QIcon
from PySide.QtCore import QObject, SIGNAL, QT_TRANSLATE_NOOP

from Render.utils import translate
from Render.constants import ICONDIR, FCDVERSION
from Render.coin import (
    ShapeCoinNode,
    PointLightCoinNode,
    DirectionalLightCoinNode,
)

# ===========================================================================
#                                 Helpers
# ===========================================================================


def get_cumulative_dict_attribute(obj, attr_name):
    """Get a merged attribute from dictionary attributes in a class hierarchy.

    Nota: A list is created for each property, thus duplicate values in
    hierarchy are recorded

    Args:
    obj -- obj from which to determine class hierarchy
    attr_name -- class attribute name to cumulate (string). The class attribute
        thus designated should be a dictionary

    Returns:
    {<key>: [(<class>, <value>)]}
    """
    properties = [
        (getattr(cls, attr_name), cls)
        for cls in obj.__class__.__mro__
        if attr_name in vars(cls)
    ]
    res = {key: [] for prop, _ in properties for key in prop}  # Initialize res
    for prop, cls in properties:
        for key, value in prop.items():
            res[key].append((cls, value))

    return res


Prop = namedtuple(
    "Prop",
    ["Type", "Group", "Doc", "Default", "EditorMode", "PropertyType"],
)
Prop.__new__.__defaults__ = (0,) * 2  # Python 3.6 style
# NB: for EditorMode and PropertyType valid values, see
# https://wiki.freecadweb.org/Scripted_objects#Property_Type

CtxMenuItem = namedtuple(
    "CtxMenuItem",
    ["name", "action", "icon"],
)
CtxMenuItem.__new__.__defaults__ = (None,)  # Python 3.6 style


# ===========================================================================
#                                 Interfaces
# ===========================================================================


class FeatureBaseInterface:
    """An interface to base class for FreeCAD scripted objects (FeatureBase).

    This class lists methods and properties that can/should be overridden by
    subclasses.
    """

    # These constants must be overridden when subclassing (mandatory)
    VIEWPROVIDER = ""  # The name of the associated ViewProvider class (str)
    PROPERTIES = {}  # The properties of the object (dict of Prop)

    # 'On change' mapping
    ON_CHANGED = {}
    # A dictionary Property: Method (strings).
    # Handles changes in this object's properties,
    # See 'onChanged' in FreeCAD scripted objects framework

    # These constants can be overridden when subclassing (optional)
    NAMESPACE = "Render"  # The namespace where feature and viewprovider are
    TYPE = ""  # The type of the object (str). If empty, default to class name
    FCDTYPE = ""  # The FreeCAD type (str, defaults to "App::FeaturePython")

    def on_set_properties_cb(self, fpo):
        """Complete the operation of internal _set_properties (callback).

        This method is a hook for sub-class to complete properties setting,
        in addition to canonic _set_properties mechanism.
        """

    def on_create_cb(self, fpo, viewp, **kwargs):
        """Complete the operation of 'create' (callback).

        This method is a hook for subclass to complete object creation,
        in addition to canonic 'create' mechanism. Subclass can override if
        needed.

        Params:
            fpo -- Related FeaturePython object
            viewp -- Related ViewProvider object
            kwargs -- Keyword arguments
        """

    @classmethod
    def pre_create_cb(cls, **kwargs):
        """Precede the operation of 'create' (callback).

        This method is a hook for subclass to precede object creation,
        in addition to canonic 'create' mechanism. Subclass can override if
        needed.

        Params:
            kwargs -- Keyword arguments
        """


class ViewProviderBaseInterface:
    """An interface to base class for FreeCAD ViewProvider.

    This class lists methods and properties that can/should be overridden by
    subclasses.
    """

    # Icon name
    ICON = ""
    # By default, look into ICONDIR.
    # If name starts with ":", will look into FreeCAD icons
    # See 'getIcon' in FreeCAD scripted objects framework

    # Display modes
    DISPLAY_MODES = ["Default"]
    # First item provides the default mode, so
    # please keep at least one item there
    # See 'getDisplayModes' in FreeCAD scripted objects framework

    # Visibility flag
    ALWAYS_VISIBLE = False
    # If True, make the object always visible in tree
    # See 'isShow' in FreeCAD scripted objects framework

    # 'On change' mapping
    ON_CHANGED = {}
    # A dictionary Property: Method (strings).
    # Handles changes in ViewProviderDocumentObject data,
    # See 'onChanged' in FreeCAD scripted objects framework

    # 'On update' mapping
    ON_UPDATE = {}
    # A dictionary Property: Method (strings)
    # Handles changes in ViewProviderDocument data,
    # See 'onUpdateData' in FreeCAD scripted objects framework

    # Context menu
    CONTEXT_MENU = []
    # An list of CtxMenuItem, for the object context menu
    # See 'getContextMenu' in FreeCAD scripted objects framework

    def on_attach_cb(self, vobj):
        """Complete 'attach' method (callback).

        Subclasses can override this method (optional).
        """

    # pylint: disable=no-self-use
    def on_delete_cb(self, feature, subelements):
        """Complete 'onDelete' method (callback).

        Subclasses can override this method (optional).
        This method must return a bool, like onDelete.
        """
        return True


# ===========================================================================
#                                 Implementations
# ===========================================================================


class FeatureBase(FeatureBaseInterface):
    """A base class for FreeCAD Feature.

    This base is to be used for workbench scripted objects.
    It provides the following features:
    - Properties management (automatically create/update properties list
      from PROPERTIES class constant)
    - Access to the FeaturePython related object, via 'fpo' property
    - Factory method 'create' to generate new instances, along with view
      providers
    """

    # Internal variables, do not modify
    _fpos = {}

    def __init__(self, fpo):
        """Initialize object.

        Params:
            fpo -- Related FeaturePython object
        """
        self._set_properties(fpo)

    def onDocumentRestored(self, fpo):
        """Respond to document restoration event (callback).

        Params:
            fpo -- Related FeaturePython object
        """
        self._set_properties(fpo)

    def _set_properties(self, fpo):
        """Set underlying FeaturePython object's properties."""
        self.fpo = fpo
        self.__module__ = self.NAMESPACE

        fpo.Proxy = self

        properties = get_cumulative_dict_attribute(self, "PROPERTIES")
        for name in properties.keys() - set(fpo.PropertiesList):
            self._set_property(name, properties)
        self.on_set_properties_cb(fpo)

    def _set_property(self, name, properties=None):
        """Set one property for underlying FeaturePython.

        fpo is assumed to have already been set.
        if no 'properties' parameter is provided, properties are computed
        from object's PROPERTIES attributes.
        """
        if not properties:
            properties = get_cumulative_dict_attribute(self, "PROPERTIES")

        _, specdata = properties[name][0]
        spec = Prop._make(specdata)
        prop = self.fpo.addProperty(
            spec.Type, name, spec.Group, spec.Doc, spec.PropertyType
        )
        setattr(prop, name, spec.Default)
        self.fpo.setEditorMode(name, spec.EditorMode)

    def reset_property(self, propname):
        """Set one property for underlying FeaturePython.

        Remark: 'on_set_properties_cb' is called after.
        """
        self.fpo.removeProperty(propname)
        self._set_property(propname)
        self.on_set_properties_cb(self.fpo)

    @property
    def fpo(self):
        """Get underlying FeaturePython object."""
        return self._fpos[id(self)]

    @fpo.setter
    def fpo(self, new_fpo):
        """Set underlying FeaturePython object."""
        self._fpos[id(self)] = new_fpo

    @property
    def type(self):
        """Get 'type' property."""
        return self.TYPE if self.TYPE else self.__class__.__name__

    @property
    def Type(self):  # pylint: disable=invalid-name
        """Get 'Type' property."""
        return self.TYPE if self.TYPE else self.__class__.__name__

    @functools.lru_cache(maxsize=128)
    def _on_changed_mapping(self):
        """Get 'on change' mapping."""
        return get_cumulative_dict_attribute(self, "ON_CHANGED")

    def onChanged(self, obj, prop):
        """Respond to property changed event (callback).

        This code is executed when a property of the FeaturePython object is
        changed.

        Args:
            obj -- related FeaturePython object (where properties are
                stored)
            prop -- property name (as a string)
        """
        on_changed = self._on_changed_mapping()
        try:
            actions = on_changed[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            # Apply methods to object
            for cls, action_name in actions:
                action = getattr(cls, action_name)
                action(self, obj)

    @classmethod
    def create(cls, document=None, **kwargs):
        """Create an instance of object in a document.

        Factory method to create a new instance of this object.
        The instance is created into the active document (default).
        Optionally, it is possible to specify a target document, in which case
        the object is created in the given document.

        This method also create the FeaturePython and the ViewProvider related
        objects. Please note that the ViewProvider class must exists in module
        namespace.

        Args:
            document -- The document where to create the instance (optional,
              default is ActiveDocument).

        Returns:
            The newly created Object, the FeaturePython and the
            ViewProvider objects.
        """
        cls.pre_create_cb(**kwargs)
        doc = document if document else App.ActiveDocument
        assert doc, (
            "Cannot create object if no document is provided "
            "and no document is active"
        )
        _type = cls.TYPE if cls.TYPE else cls.__name__
        fcdtype = cls.FCDTYPE if cls.FCDTYPE else "App::FeaturePython"
        fpo = doc.addObject(fcdtype, _type)
        obj = cls(fpo)
        try:
            viewp_class = getattr(sys.modules[cls.NAMESPACE], cls.VIEWPROVIDER)
        except AttributeError as original_exc:
            msg = "Bad {d}.VIEWPROVIDER value in '{d}' creation: '{v}'\n"
            msg = msg.format(d=cls.__name__, v=cls.VIEWPROVIDER)
            trace = sys.exc_info()[2]
            raise ValueError(msg).with_traceback(trace) from original_exc
            # Hint: have you declared object and its ViewProvider in
            # __init__.py?

        if fpo.ViewObject:
            viewp = viewp_class(fpo.ViewObject)
        else:
            # Console case: no view provider is available
            viewp = None

        obj.on_create_cb(fpo, viewp, **kwargs)
        return obj, fpo, viewp


class ViewProviderBase(ViewProviderBaseInterface):
    """A base class for FreeCAD ViewProvider.

    This base is to be used for workbench scripted objects' ViewProviders.
    """

    def __init__(self, vobj):
        """Initialize View Provider.

        Args:
            vobj -- Related ViewProviderDocumentObject
        """
        vobj.Proxy = self
        self.fpo = vobj.Object  # Related FeaturePython object
        self.__module__ = "Render"

    def attach(self, vobj):
        """Respond to created/restored object event (callback).

        Args:
            vobj -- Related ViewProviderDocumentObject
        """
        self.fpo = vobj.Object  # Related FeaturePython object
        self.__module__ = "Render"

        # Hook for mixins
        self.on_attach_mixin_cb(vobj)  # Can be overridden by mixins

        # Hook for objects
        self.on_attach_cb(vobj)

        # Update all properties
        self.update_all(self.fpo)

    def on_attach_mixin_cb(self, vobj):
        """Complete 'attach' method (callback, mixin version).

        Args:
            vobj -- Related ViewProviderDocumentObject

        Mixins which overrides this method are requested to call
        super().on_attach_mixin_cb
        """

    def onDelete(self, feature, subelements):
        """Respond to delete object event (callback).

        Args:
            feature -- Related ViewProviderDocumentObject
        """
        res = True

        # Hook for mixins
        try:
            callback = self.on_delete_mixin_cb
        except AttributeError:
            pass
        else:
            res &= callback(feature, subelements)

        # Hook for objects
        res &= self.on_delete_cb(feature, subelements)

        return res

    # pylint: disable=no-self-use
    def on_delete_mixin_cb(self, feature, subelements):
        """Complete 'delete' method (callback, mixin version).

        Args:
            feature -- Related ViewProviderDocumentObject

        Mixins which overrides this method are requested to call
        super().on_attach_mixin_cb
        """
        return True

    @functools.lru_cache(maxsize=128)
    def _context_menu_mapping(self):
        """Get context menu items."""
        res = itertools.chain.from_iterable(
            [
                cls.CONTEXT_MENU
                for cls in reversed(self.__class__.__mro__)
                if "CONTEXT_MENU" in vars(cls)
            ]
        )
        return list(res)

    def setupContextMenu(self, vobj, menu):
        """Set up the object's context menu in GUI (callback)."""
        for item in self._context_menu_mapping():
            if item.icon:
                icon = QIcon(os.path.join(ICONDIR, item.icon))
                action = QAction(icon, item.name, menu)
            else:
                action = QAction(item.name, menu)
            method = getattr(self, item.action)
            QObject.connect(action, SIGNAL("triggered()"), method)
            menu.addAction(action)

    def isShow(self):
        """Define the visibility of the object in the tree view (callback)."""
        return True if self.ALWAYS_VISIBLE else self.fpo.Visibility

    def claimChildren(self):
        """Deliver the children belonging to this object (callback)."""
        try:
            return self.fpo.Group
        except AttributeError:
            return []

    def getIcon(self):
        """Return the icon which will appear in the tree view (callback)."""
        icon = (
            self.ICON
            if self.ICON.startswith(":")
            else os.path.join(ICONDIR, self.ICON)
        )
        return icon

    @functools.lru_cache(maxsize=128)
    def _on_changed_mapping(self):
        """Get 'on change' mapping."""
        return get_cumulative_dict_attribute(self, "ON_CHANGED")

    def onChanged(self, vpdo, prop):
        """Respond to property changed event (callback).

        This code is executed when a property of the FeaturePython object is
        changed.

        Args:
            vpdo -- related ViewProviderDocumentObject (where properties are
                stored)
            prop -- property name (as a string)
        """
        on_changed = self._on_changed_mapping()
        try:
            actions = on_changed[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            # Apply methods to object
            for cls, action_name in actions:
                action = getattr(cls, action_name)
                action(self, vpdo)

    @functools.lru_cache(maxsize=128)
    def _on_update_mapping(self):
        """Get 'on update data' mapping."""
        return get_cumulative_dict_attribute(self, "ON_UPDATE")

    def updateData(self, fpo, prop):
        """Respond to FeaturePython's property changed event (callback).

        This code is executed when a property of the underlying FeaturePython
        object is changed.

        Args:
            fpo -- related FeaturePython object
            prop -- property name (str)
        """
        prop = str(prop)
        on_update = self._on_update_mapping()
        try:
            actions = on_update[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            # Apply methods to object
            for cls, action_name in actions:
                action = getattr(cls, action_name)
                action(self, fpo)

    def update_all(self, fpo):
        """Force update callback for all data."""
        for prop_name in self._on_update_mapping():
            self.updateData(fpo, prop_name)

    if FCDVERSION < (0, 21, 2):

        def __getstate__(self):
            """Provide data representation for object."""
            return None

        def __setstate__(self, state):
            """Restore object state from data representation."""

    else:

        def dumps(self):
            """Provide data representation for object."""
            return None

        def loads(self, _):
            """Restore object state from data representation.

            Args:
                state -- previous state to restore object to
            """

    def getDisplayModes(self, vobj):
        """Return a list of display modes (callback)."""
        return self.DISPLAY_MODES

    def getDefaultDisplayMode(self):
        """Return the name of the default display mode (callback).

        The display mode must be defined in getDisplayModes.
        """
        return self.DISPLAY_MODES[0]

    def setDisplayMode(self, mode):  # pylint: disable=no-self-use
        """Set the display mode (callback).

        Map the display mode defined in attach with those defined in
        getDisplayModes. Since they have the same names nothing needs to be
        done.
        """
        return mode


# ===========================================================================
#                                 Mixins
# ===========================================================================


class PointableFeatureMixin:  # pylint: disable=too-few-public-methods
    """Mixin for Pointable feature.

    This mixin allows a feature to be "pointable", ie to support
    'point_at' action.
    """

    FCDTYPE = "App::GeometryPython"

    def point_at(self, point):
        """Make camera point at a given target point.

        Args:
            point -- Geometrical point to point at (having x, y, z properties).
        """
        fpo = self.fpo
        current_target = fpo.Placement.Rotation.multVec(App.Vector(0, 0, -1))
        base = fpo.Placement.Base
        new_target = App.Vector(
            point.x - base.x, point.y - base.y, point.z - base.z
        )
        axis = current_target.cross(new_target)
        if not axis.Length:
            # Don't try to rotate if axis is a null vector...
            return
        angle = degrees(new_target.getAngle(current_target))
        rotation = App.Rotation(axis, angle)
        fpo.Placement.Rotation = rotation.multiply(fpo.Placement.Rotation)


class PointableViewProviderMixin:  # pylint: disable=too-few-public-methods
    """Mixin for Pointable ViewProviders.

    This mixin allows a ViewProvider to be "pointable", ie to support
    'point_at' actions.
    """

    CONTEXT_MENU = [
        CtxMenuItem(
            QT_TRANSLATE_NOOP("Render", "Point at..."),
            "point_at",
        ),
    ]

    def __init__(self, vobj):
        """Initialize Mixin."""
        super().__init__(vobj)
        self.callback = None  # For point_at method

    def point_at(self):
        """Make this object interactively point at another object.

        User will be requested to select an object to point at.
        """
        msg = (
            translate(
                "Render", "[Point at] Please select target (on geometry)"
            )
            + "\n"
        )
        App.Console.PrintMessage(msg)
        self.callback = Gui.ActiveDocument.ActiveView.addEventCallbackPivy(
            coin.SoMouseButtonEvent.getClassTypeId(), self._point_at_cb
        )

    def _point_at_cb(self, event_cb):
        """`point_at` callback.

        Args:
            event_cb -- coin event callback object
        """
        event = event_cb.getEvent()
        if (
            event.getState() == coin.SoMouseButtonEvent.DOWN
            and event.getButton() == coin.SoMouseButtonEvent.BUTTON1
        ):
            # Get point
            picked_point = event_cb.getPickedPoint()
            try:
                point = App.Vector(picked_point.getPoint())
            except AttributeError:
                # No picked point (outside geometry)
                msg = (
                    translate(
                        "Render",
                        "[Point at] Target outside geometry -- Aborting",
                    )
                    + "\n"
                )
                App.Console.PrintMessage(msg)
            else:
                # Make underlying object point at target point
                self.fpo.Proxy.point_at(point)
                msg = (
                    translate(
                        "Render",
                        "[Point at] Now pointing at ({0.x}, {0.y}, {0.z})",
                    )
                    + "\n"
                )
                App.Console.PrintMessage(msg.format(point))
            finally:
                # Remove coin event catcher
                Gui.ActiveDocument.ActiveView.removeEventCallbackPivy(
                    coin.SoMouseButtonEvent.getClassTypeId(), self.callback
                )


class CoinShapeViewProviderMixin:
    """Mixin for ViewProviders implementing a Coin shape.

    This mixin allows a ViewProvider to be represented by a Coin shape (either
    a SoFaceSet or a SoLineSet) in FreeCAD viewport.
    """

    DISPLAY_MODES = ["Shaded", "Wireframe"]

    COIN_SHAPE_POINTS = ()
    COIN_SHAPE_VERTICES = ()
    COIN_SHAPE_WIREFRAME = False
    COIN_SHAPE_COLORS = ["diffuse"]  # diffuse, emissive, ambient

    ON_CHANGED = {"Visibility": "_change_visibility"}
    ON_UPDATE = {
        "Placement": "_update_placement",
        "Location": "_update_location",
        "Color": "_update_color",
    }

    def on_attach_mixin_cb(self, vobj):
        """Complete 'attach' method (callback, mixin version)."""
        super().on_attach_mixin_cb(vobj)
        if not hasattr(self, "coin"):
            self.coin = SimpleNamespace()
        self.coin.shape = ShapeCoinNode(
            self.COIN_SHAPE_POINTS,
            self.COIN_SHAPE_VERTICES,
            wireframe=self.COIN_SHAPE_WIREFRAME,
        )
        self.coin.shape.add_display_modes(vobj, self.DISPLAY_MODES)

    def on_delete_mixin_cb(self, feature, subelements):
        """Complete 'onDelete' method (callback, mixin version)."""
        res = super().on_delete_mixin_cb(feature, subelements)
        # Delete coin representation
        Gui.setActiveDocument(self.fpo.Document)
        Gui.activateView("Gui::View3DInventor", False)
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        self.coin.shape.remove_from_scene(scene)
        return res  # If False, the object wouldn't be deleted

    def _change_visibility(self, vpdo):
        """Respond to Visibility change."""
        self.coin.shape.set_visibility(vpdo.Visibility)

    def _update_placement(self, fpo):
        """Update object placement."""
        if fpo.isDerivedFrom("App::GeometryPython"):
            return  # GeometryPython already provides Coin placement update...
        try:
            placement = fpo.Placement
        except AttributeError:
            pass
        else:
            self.coin.shape.set_placement(placement)

    def _update_location(self, fpo):
        """Update object location."""
        if fpo.isDerivedFrom("App::GeometryPython"):
            return  # GeometryPython already provides Coin placement update...
        try:
            location = fpo.Location
        except AttributeError:
            pass
        else:
            self.coin.shape.set_position(location)

    def _update_color(self, fpo):
        """Update object color."""
        try:
            color = fpo.Color[:3]
        except AttributeError:
            pass
        else:
            kwargs = {colortype: color for colortype in self.COIN_SHAPE_COLORS}
            self.coin.shape.set_color(**kwargs)


class CoinLightViewProviderMixin:
    """Mixin for ViewProviders implementing a Coin light.

    This mixin allows a ViewProvider to be represented by a Coin Light.
    This mixin is abstract and should not be used as-is. Only subclasses
    should be used (see PointLight, DirectionalLight...)
    """

    DISPLAY_MODES = ["Shaded", "Wireframe"]
    ON_CHANGED = {"Visibility": "_change_visibility"}
    ON_UPDATE = {
        "Power": "_update_power",
        "Color": "_update_color",
    }
    LIGHT_COIN_NODE = None  # Must be overridden by subclass

    def on_attach_mixin_cb(self, vobj):
        """Complete 'attach' method (callback, mixin version)."""
        super().on_attach_mixin_cb(vobj)
        if not hasattr(self, "coin"):
            self.coin = SimpleNamespace()

        # Create light in scenegraph
        Gui.setActiveDocument(self.fpo.Document)
        Gui.activateView("Gui::View3DInventor", False)
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        # pylint: disable=not-callable
        self.coin.light = self.LIGHT_COIN_NODE()
        self.coin.light.add_to_scene(scene)  # Insert frontwise

    def on_delete_mixin_cb(self, feature, subelements):
        """Complete 'onDelete' method (callback, mixin version)."""
        res = super().on_delete_mixin_cb(feature, subelements)
        # Delete coin representation
        Gui.setActiveDocument(self.fpo.Document)
        Gui.activateView("Gui::View3DInventor", False)
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        self.coin.light.remove_from_scene(scene)
        return res  # If False, the object wouldn't be deleted

    def _change_visibility(self, vpdo):
        """Change light visibility."""
        self.coin.light.set_visibility(vpdo.Visibility)

    def _update_power(self, fpo):
        """Update light power."""
        try:
            power = fpo.Power
        except AttributeError:
            pass
        else:
            intensity = power / 100 if power <= 100 else 1
            self.coin.light.set_intensity(intensity)

    def _update_color(self, fpo):
        """Update light color."""
        try:
            color = fpo.Color[:3]
        except AttributeError:
            pass
        else:
            self.coin.light.set_color(color)


class CoinPointLightViewProviderMixin(CoinLightViewProviderMixin):
    """Mixin for ViewProviders implementing a Coin light.

    This mixin allows a ViewProvider to be represented by a Coin PointLight.
    """

    LIGHT_COIN_NODE = PointLightCoinNode

    ON_UPDATE = {
        "Location": "_update_location",
        "Placement": "_update_placement",
    }

    def _update_placement(self, fpo):
        """Update object placement."""
        try:
            placement = fpo.Placement
        except AttributeError:
            pass
        else:
            self.coin.light.set_location(placement.Base)

    def _update_location(self, fpo):
        """Update pointlight location."""
        try:
            location = fpo.Location
        except AttributeError:
            pass
        else:
            self.coin.light.set_location(location)


class CoinDirectionalLightViewProviderMixin(CoinLightViewProviderMixin):
    """Mixin for ViewProviders implementing a directional light.

    This mixin allows a ViewProvider to be represented by a Directional Light.
    """

    LIGHT_COIN_NODE = DirectionalLightCoinNode

    ON_UPDATE = {
        "Direction": "_update_direction",
    }

    def _update_direction(self, fpo):
        """Update light direction."""
        try:
            direction = fpo.Direction
        except AttributeError:
            pass
        else:
            self.coin.light.set_direction(direction)
