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

Prop = namedtuple("Prop", ["Type", "Group", "Doc", "Default", "EditorMode"])


class BaseFeature():
    """A base class for FreeCAD Feature.

    This base is to be used for workbench scripted objects.
    It provides the following features:
    - Properties management (automatically create/update properties list
      from PROPERTIES class constant)
    - Access to the FeaturePython related object, via 'fpo' property
    """

    MODULE = "Render"
    TYPE = ""
    PROPERTIES = {}

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
        self.__module__ = self.MODULE
        self.type = self.TYPE  # TODO Should be Type?
        fpo.Proxy = self
        for name in self.PROPERTIES.keys() - set(fpo.PropertiesList):
            spec = self.PROPERTIES[name]
            prop = fpo.addProperty(spec.Type, name, spec.Group, spec.Doc, 0)
            setattr(prop, name, spec.Default)
            fpo.setEditorMode(spec.EditorMode)
        self.on_set_properties(fpo)

    def on_set_properties(self, fpo):
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
