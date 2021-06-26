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

"""This module implements base classes for Render workbench."""

from collections import namedtuple
import sys
import os

import FreeCAD as App
from PySide.QtGui import QAction, QIcon
from PySide.QtCore import QObject, SIGNAL

from Render.constants import ICONDIR

Prop = namedtuple("Prop", ["Type", "Group", "Doc", "Default", "EditorMode"])


class InterfaceBaseFeature:
    """An interface to base class for FreeCAD scripted objects (BaseFeature).

    This class lists methods and properties that can/should be overriden by
    subclasses.
    """
    # These constants must be overriden when subclassing (mandatory)
    VIEWPROVIDER = ""  # The name of the associated ViewProvider class (str)
    PROPERTIES = {}  # The properties of the object (dict of Prop)

    # These constants can be overriden when subclassing (optional)
    NAMESPACE = "Render"  # The namespace where feature and viewprovider are
    TYPE = ""  # The type of the object (str). If empty, default to class name

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


class BaseFeature(InterfaceBaseFeature):
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
    _fpos = dict()

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

        for name in self.PROPERTIES.keys() - set(fpo.PropertiesList):
            spec = Prop._make(self.PROPERTIES[name])
            prop = fpo.addProperty(spec.Type, name, spec.Group, spec.Doc, 0)
            setattr(prop, name, spec.Default)
            fpo.setEditorMode(name, spec.EditorMode)
        self.on_set_properties_cb(fpo)

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
        fpo = doc.addObject("App::FeaturePython", _type)
        obj = cls(fpo)
        try:
            viewp_class = getattr(sys.modules[cls.NAMESPACE], cls.VIEWPROVIDER)
        except AttributeError as original_exc:
            msg = "Bad {d}.VIEWPROVIDER value in '{d}' creation: '{v}'\n"
            msg = msg.format(d=cls.__name__, v=cls.VIEWPROVIDER)
            trace = sys.exc_info()[2]
            raise ValueError(msg).with_traceback(trace) from original_exc
        viewp = viewp_class(fpo.ViewObject)
        obj.on_create_cb(fpo, viewp, **kwargs)
        App.ActiveDocument.recompute()
        return obj, fpo, viewp


CtxMenuItem = namedtuple("CtxMenuItem", ["name", "action", "icon"])


class InterfaceBaseViewProvider:
    """An interface to base class for FreeCAD ViewProvider.

    This class lists methods and properties that can/should be overriden by
    subclasses.
    """

    ICON = ""
    CONTEXT_MENU = []  # An iterable of CtxMenuItem
    ON_CHANGED = {}  # A dictionary Property: Method
    ON_UPDATE_DATA = {}  # A dictionary Property: Method

    def on_attach_cb(self, vobj):
        """Complete 'attach' method (callback).

        Subclasses can override this method.
        """


class BaseViewProvider(InterfaceBaseViewProvider):
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
        self.on_attach_cb(vobj)

    def setupContextMenu(self, vobj, menu):
        """Set up the object's context menu in GUI (callback)."""
        for item in self.CONTEXT_MENU:
            if item.icon:
                icon = QIcon(os.path.join(ICONDIR, item.icon))
                action = QAction(icon, item.name, menu)
            else:
                action = QAction(item.name, menu)
            method = getattr(self, item.action)
            QObject.connect(action, SIGNAL("triggered()"), method)
            menu.addAction(action)

    def isShow(self):  # pylint: disable=no-self-use
        """Define the visibility of the object in the tree view (callback)."""
        return True

    def claimChildren(self):
        """Deliver the children belonging to this object (callback)."""
        try:
            return self.fpo.Group
        except AttributeError:
            return []

    def getIcon(self):
        # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)."""
        return os.path.join(ICONDIR, self.ICON)

    def onChanged(self, vpdo, prop):
        """Respond to property changed event (callback).

        This code is executed when a property of the FeaturePython object is
        changed.

        Args:
            vpdo -- related ViewProviderDocumentObject (where properties are
                stored)
            prop -- property name (as a string)
        """
        try:
            method = self.ON_CHANGED[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            method(self, vpdo)

    def updateData(self, fpo, prop):
        """Respond to FeaturePython's property changed event (callback).

        This code is executed when a property of the underlying FeaturePython
        object is changed.

        Args:
            fpo -- related FeaturePython object
            prop -- property name
        """
        try:
            method = self.ON_UPDATE_DATA[prop]
        except KeyError:
            pass  # Silently ignore when switcher provides no action
        else:
            method(self, fpo)

    def __getstate__(self):
        """Provide data representation for object."""
        return None

    def __setstate__(self, state):
        """Restore object state from data representation."""
        return None

    def getDisplayModes(self, vobj):  # pylint: disable=no-self-use
        """Return a list of display modes (callback)."""
        return ["Default"]

    def getDefaultDisplayMode(self):  # pylint: disable=no-self-use
        """Return the name of the default display mode (callback).

        The display mode must be defined in getDisplayModes.
        """
        return "Default"

    def setDisplayMode(self, mode):  # pylint: disable=no-self-use
        """Set the display mode (callback).

        Map the display mode defined in attach with those defined in
        getDisplayModes. Since they have the same names nothing needs to be
        done.
        """
        return mode
