# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
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

"""This module implements the rendering view object for Render workbench.

The rendering view designates a FreeCad object to be rendered as part of a
rendering project.
"""


from PySide.QtCore import QT_TRANSLATE_NOOP

from Render.constants import FCDVERSION
from Render.base import FeatureBase, Prop, ViewProviderBase
from Render.rdrhandler import RendererHandler


class View(FeatureBase):
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
            "Base",
            QT_TRANSLATE_NOOP(
                "App::Property", "The source object of this view"
            ),
            None,
            0,
        ),
        "Material": Prop(
            "App::PropertyLink",
            "Material & Textures",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The material of this view (optional, should preferably be "
                "set in the source object)",
            ),
            None,
            0,
        ),
        "ViewResult": Prop(
            "App::PropertyString",
            "Base",
            QT_TRANSLATE_NOOP(
                "App::Property", "The rendering output of this view (computed)"
            ),
            "",
            1,
        ),
        "UvProjection": Prop(
            "App::PropertyEnumeration",
            "Material & Textures",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The type of UV projection to use for textures",
            ),
            ("Cubic", "Spherical", "Cylindric"),
            0,
        ),
    }

    @classmethod
    def pre_create_cb(cls, **kwargs):
        """Precede the operation of 'create' (callback)."""
        project = kwargs["project"]  # Note: 'project' kw argument is mandatory
        source = kwargs["source"]  # Note: 'source' kw argument is mandatory
        assert project.Document == source.Document or FCDVERSION >= (
            0,
            19,
        ), "Unable to create View: Project and Object not in same document"

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
            prop = fpo.addProperty(
                "App::PropertyXLink", name, spec.Group, spec.Doc, 0
            )
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
            proj = next(
                x for x in obj.InListRecursive if RendererHandler.is_project(x)
            )
            assert not proj.DelayedBuild
        except (StopIteration, AttributeError, AssertionError):
            return

        # Get object rendering string and set ViewResult property
        renderer = RendererHandler(
            rdrname=proj.Renderer,
            linear_deflection=proj.LinearDeflection,
            angular_deflection=proj.AngularDeflection,
            transparency_boost=proj.TransparencySensitivity,
        )

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

    def group_params(self, group):
        """Retrieve source parameters belonging to a specific group.

        This method is especially intended for renderer's specific parameters.

        Args:
            group -- the name of the group (str)

        Returns:
            a dictionary (name, value)
        """
        src = self.fpo.Source
        res = {
            p: src.getPropertyByName(p)
            for p in src.PropertiesList
            if src.getGroupOfProperty(p) == group
        }
        return res


class ViewProviderView(ViewProviderBase):
    """ViewProvider of rendering view object."""

    ICON = "RenderViewTree.svg"
    ALWAYS_VISIBLE = True

    def __init__(self, vobj):
        """Initialize ViewProviderView."""
        super().__init__(vobj)
        self._create_usematerialcolor(vobj)

    def on_attach_cb(self, vobj):
        """Respond to created/restored object event (callback)."""
        self._create_usematerialcolor(vobj)

    @staticmethod
    def _create_usematerialcolor(vobj):
        """Create UseMaterialColor on view object and set it to False.

        This is required for ArchMaterial not to try to ShapeColor on this
        object.
        """
        if "UseMaterialColor" not in vobj.PropertiesList:
            vobj.addProperty(
                "App::PropertyBool", "UseMaterialColor", "Render", ""
            )
        vobj.UseMaterialColor = False
