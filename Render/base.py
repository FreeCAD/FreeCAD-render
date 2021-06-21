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

import FreeCAD as App

Prop = namedtuple("Prop", ["Type", "Group", "Doc", "Default", "EditorMode"])


class BaseFeature():
    """A base class for FreeCAD Feature.

    This base is to be used for workbench scripted objects.
    It provides the following features:
    - Properties management (automatically create/update properties list
      from PROPERTIES class constant)
    - Access to the FeaturePython related object, via 'fpo' property
    - Factory method 'create' to generate new instances, along with view
      providers
    """

    # These constants must be overriden when subclassing (mandatory)
    VIEWPROVIDER = ""  # The name of the associated ViewProvider class (str)
    PROPERTIES = {}  # The properties of the object (dict of Prop)

    # These constants can be overriden when subclassing (optional)
    NAMESPACE = "Render"  # The namespace where feature and viewprovider are
    TYPE = ""  # The type of the object (str). If empty, default to class name

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

    def on_set_properties_cb(self, fpo):
        """Complete the operation of internal _set_properties (callback).

        This method is a hook for sub-class to complete properties setting,
        in addition to canonic _set_properties mechanism.
        """

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
        assert doc, ("Cannot create object if no document is provided "
                     "and no document is active")
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
        viewp =viewp_class(fpo.ViewObject)
        obj.on_create_cb(fpo, viewp, **kwargs)
        App.ActiveDocument.recompute()
        return obj, fpo, viewp

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
