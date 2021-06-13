# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
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

"""This module implements the rendering view object for Render workbench.

The rendering view designates a FreeCad object to be rendered as part of a
rendering project
"""


import os

from PySide.QtCore import QT_TRANSLATE_NOOP

from Render.constants import FCDVERSION, ICONDIR
from Render.rdrhandler import RendererHandler


class View:
    """A rendering view of a FreeCAD object."""

    # Related FeaturePython object has to be stored in a class variable,
    # (not in an instance variable...), otherwise it causes trouble in
    # serialization...
    _fpos = dict()

    def __init__(self, obj, xlink=False):
        """Initialize view.

        Args:
        obj -- FreeCAD underlying object
        xlink -- flag to indicate if the source property must be created as a
                 App::PropertyLink (source object inside document) or
                 App::PropertyXLink (source object outside document, only for
                 FreeCAD >= 0.19)
        """
        obj.Proxy = self
        self.set_properties(obj, xlink)

    @property
    def fpo(self):
        """Get underlying FeaturePython object."""
        return self._fpos[id(self)]

    @fpo.setter
    def fpo(self, new_fpo):
        """Set underlying FeaturePython object."""
        self._fpos[id(self)] = new_fpo

    def set_properties(self, obj, xlink=False):
        """Set underlying FeaturePython object's properties.

        Args:
            obj -- FeaturePython Object related to this project
        """
        self.fpo = obj
        self.__module__ = "Render"

        if "Source" not in obj.PropertiesList:
            hi_version = FCDVERSION >= ("0", "19")
            assert not (xlink and not hi_version),\
                ("Error with View: FreeCAD version is < 0.19 whereas source "
                 "object is external to document")
            obj.addProperty(
                "App::PropertyXLink" if xlink else "App::PropertyLink",
                "Source",
                "Render",
                QT_TRANSLATE_NOOP("App::Property",
                                  "The source object of this view"))

        if "Material" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyLink",
                "Material",
                "Render",
                QT_TRANSLATE_NOOP("App::Property",
                                  "The material of this view"))

        if "ViewResult" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyString",
                "ViewResult",
                "Render",
                QT_TRANSLATE_NOOP("App::Property",
                                  "The rendering output of this view"))

    def onDocumentRestored(self, obj):  # pylint: disable=no-self-use
        """Respond to document restoration event (callback)."""
        self.set_properties(obj)

    def execute(self, obj):  # pylint: disable=no-self-use
        """Respond to document recomputation event (callback, mandatory).

        Write or rewrite the ViewResult string if containing project is not
        'delayed build'
        """
        # Find containing project and check DelayedBuild is false
        try:
            proj = next(x for x in obj.InListRecursive
                        if RendererHandler.is_project(x))
            assert not proj.DelayedBuild
        except (StopIteration, AttributeError, AssertionError):
            return

        # Get object rendering string and set ViewResult property
        renderer = RendererHandler(
            rdrname=proj.Renderer,
            linear_deflection=proj.LinearDeflection,
            angular_deflection=proj.AngularDeflection,
            transparency_boost=proj.TransparencySensitivity)

        obj.ViewResult = renderer.get_rendering_string(obj)

    @staticmethod
    def view_label(obj, proj, is_group=False):
        """Give a standard label for the view of an object.

        Args:
            obj -- object which the view is built for
            proj -- project which the view will be inserted in
            is_group -- flag to indicate whether the view is a group

        Both obj and proj should have valid Label attributes
        """
        obj_label = str(obj.Label)
        proj_label = str(proj.Label)

        proj_label = proj_label.replace(" ", "")
        fmt = "{o}Group@{p}" if is_group else "{o}@{p}"
        res = fmt.format(o=obj_label, p=proj_label)
        return res

    @staticmethod
    def create(fcd_obj, project):
        """Create a new rendering object in a given project (factory method).

        This method creates a new rendering object in a given rendering
        project, for a given FreeCAD object (of any type: Mesh, Part...).
        Please note that providing a Project is mandatory: no rendering
        view should be created "off-ground". Moreover, project's document
        and FreeCAD object document should be the same.
        The method also creates the FeaturePython and the ViewProviderView
        objects related to the new rendering view.

        Args:
            fcdobj -- The object for which the rendering view is to be created
            project -- The rendering project in which the view is to be created

        Returns:
            The newly created View, the related FeaturePython object and the
            related ViewProviderView object
        """
        doc = project.Document
        assert doc == fcd_obj.Document or FCDVERSION >= ("0", "19"),\
            "Unable to create View: Project and Object not in same document"
        fpo = doc.addObject("App::FeaturePython", "%sView" % fcd_obj.Name)
        fpo.Label = View.view_label(fcd_obj, project)
        xlink = doc != fcd_obj.Document
        view = View(fpo, xlink)
        fpo.Source = fcd_obj
        project.addObject(fpo)
        viewp = ViewProviderView(fpo.ViewObject)
        return view, fpo, viewp


class ViewProviderView:
    """ViewProvider of rendering view object."""

    def __init__(self, vobj):
        """Initialize ViewProviderView."""
        vobj.Proxy = self
        self.__module__ = "Render"
        self.object = None
        self._create_usematerialcolor(vobj)

    def attach(self, vobj):  # pylint: disable=no-self-use
        """Respond to created/restored object event (callback)."""
        self.object = vobj.Object
        self.__module__ = "Render"
        self._create_usematerialcolor(vobj)

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

        This display mode must be defined in getDisplayModes.
        """
        return "Default"

    def setDisplayMode(self, mode):  # pylint: disable=no-self-use
        """Set the display mode (callback).

        Map the display mode defined in attach with those defined in
        getDisplayModes. Since they have the same names nothing needs to be
        done.
        """
        return mode

    def isShow(self):  # pylint: disable=no-self-use
        """Define the visibility of the object in the tree view (callback)."""
        return True

    def getIcon(self):  # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)."""
        return os.path.join(ICONDIR, "RenderViewTree.svg")

    @staticmethod
    def _create_usematerialcolor(vobj):
        """Create UseMaterialColor on view object and set it to False.

        This is required for ArchMaterial not to try to ShapeColor on this
        object.
        """
        if "UseMaterialColor" not in vobj.PropertiesList:
            vobj.addProperty(
                    "App::PropertyBool", "UseMaterialColor", "Render", "")
        vobj.UseMaterialColor = False
