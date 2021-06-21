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
rendering project.
"""


import os

from PySide.QtCore import QT_TRANSLATE_NOOP

from Render.constants import FCDVERSION, ICONDIR
from Render.base import BaseFeature, Prop
from Render.rdrhandler import RendererHandler


class View(BaseFeature):
    """A rendering view of a FreeCAD object.

    'create' factory method should be provided a project and a source (the
    object for which the view is created), via keyword arguments.
    Please note that providing a project is mandatory to create a view: no
    rendering view should be created "off-ground".
    """

    VIEWPROVIDER = "ViewProviderView"

    PROPERTIES = {
        "Source": Prop(
            "App::PropertyLink",
            "Render",
            QT_TRANSLATE_NOOP("App::Property",
                              "The source object of this view"),
            None,
            0),

        "Material": Prop(
            "App::PropertyLink",
            "Render",
            QT_TRANSLATE_NOOP("App::Property",
                              "The material of this view"),
            None,
            0),

        "ViewResult": Prop(
            "App::PropertyString",
            "Render",
            QT_TRANSLATE_NOOP("App::Property",
                              "The rendering output of this view"),
            "",
            0)
    }

    @classmethod
    def pre_create_cb(cls, **kwargs):
        """Precede the operation of 'create' (callback)."""
        project = kwargs["project"]  # Note: 'project' kw argument is mandatory
        source = kwargs["source"]  # Note: 'source' kw argument is mandatory
        version = FCDVERSION
        assert project.Document == source.Document or version >= ("0", "19"),\
            "Unable to create View: Project and Object not in same document"

    def on_create_cb(self, fpo, viewp, **kwargs):
        """Complete 'create' (callback)."""
        project = kwargs["project"]
        source = kwargs["source"]
        fpo.Label = View.view_label(source, project)
        if project.Document != source.Document:
            # Cross-link: Transform Source into App::PropertyXLink
            name = "Source"
            fpo.removeProperty(name)
            spec = self.PROPERTIES[name]
            prop = fpo.addProperty("App::PropertyXLink",
                                   name,
                                   spec.Group,
                                   spec.Doc,
                                   0)
            setattr(prop, name, spec.Default)
            fpo.setEditorMode(name, spec.EditorMode)
        fpo.Source = source
        project.addObject(fpo)

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
