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

"""This module implements the rendering project object for Render workbench.

The rendering project contains rendering views and parameters to describe
the scene to render
"""

import math
import sys
import os
import re
from types import SimpleNamespace
from operator import attrgetter
from tempfile import mkstemp

from PySide.QtGui import QFileDialog, QMessageBox
from PySide.QtCore import QT_TRANSLATE_NOOP
import FreeCAD as App
import FreeCADGui as Gui

try:
    import ImageGui
except ImportError:
    pass

from Render.constants import TEMPLATEDIR, PARAMS
from Render.rdrhandler import RendererHandler, RendererNotFoundError
from Render.utils import translate
from Render.view import View
from Render.camera import DEFAULT_CAMERA_STRING, set_cam_from_coin_string
from Render.base import BaseFeature, Prop, BaseViewProvider, CtxMenuItem


class Project(BaseFeature):
    """A rendering project."""

    VIEWPROVIDER = "ViewProviderProject"

    PROPERTIES = {
        "Renderer": Prop(
            "App::PropertyString",
            "Base",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The name of the raytracing engine to use",
            ),
            "",
        ),
        "DelayedBuild": Prop(
            "App::PropertyBool",
            "Output",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "If true, the views will be updated on render only",
            ),
            True,
        ),
        "Template": Prop(
            "App::PropertyString",
            "Base",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "The template to be used by this rendering "
                "(use Project's context menu to modify)",
            ),
            "",
            1,
        ),
        "PageResult": Prop(
            "App::PropertyFileIncluded",
            "Render",
            QT_TRANSLATE_NOOP(
                "App::Property", "The result file to be sent to the renderer"
            ),
            "",
            2,
        ),
        "RenderWidth": Prop(
            "App::PropertyInteger",
            "Render",
            QT_TRANSLATE_NOOP(
                "App::Property", "The width of the rendered image in pixels"
            ),
            PARAMS.GetInt("RenderWidth", 800),
        ),
        "RenderHeight": Prop(
            "App::PropertyInteger",
            "Render",
            QT_TRANSLATE_NOOP(
                "App::Property", "The height of the rendered image in pixels"
            ),
            PARAMS.GetInt("RenderHeight", 600),
        ),
        "GroundPlane": Prop(
            "App::PropertyBool",
            "Ground Plane",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "If true, a default ground plane will be added to the scene",
            ),
            False,
        ),
        "GroundPlaneZ": Prop(
            "App::PropertyDistance",
            "Ground Plane",
            QT_TRANSLATE_NOOP("App::Property", "Z position for ground plane"),
            0,
        ),
        "GroundPlaneColor": Prop(
            "App::PropertyColor",
            "Ground Plane",
            QT_TRANSLATE_NOOP("App::Property", "Ground plane color"),
            (0.8, 0.8, 0.8),
        ),
        "GroundPlaneSizeFactor": Prop(
            "App::PropertyFloat",
            "Ground Plane",
            QT_TRANSLATE_NOOP("App::Property", "Ground plane size factor"),
            1.0,
        ),
        "OutputImage": Prop(
            "App::PropertyFile",
            "Output",
            QT_TRANSLATE_NOOP(
                "App::Property", "The image saved by this render"
            ),
            "",
        ),
        "OpenAfterRender": Prop(
            "App::PropertyBool",
            "Output",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "If true, the rendered image is opened in FreeCAD after "
                "the rendering is finished",
            ),
            True,
        ),
        "LinearDeflection": Prop(
            "App::PropertyFloat",
            "Mesher",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Linear deflection for the mesher: "
                "The maximum linear deviation of a mesh section from the "
                "surface of the object.",
            ),
            0.1,
        ),
        "AngularDeflection": Prop(
            "App::PropertyFloat",
            "Mesher",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Angular deflection for the mesher: "
                "The maximum angular deviation from one mesh section to "
                "the next, in radians. This setting is used when meshing "
                "curved surfaces.",
            ),
            math.pi / 6,
        ),
        "TransparencySensitivity": Prop(
            "App::PropertyIntegerConstraint",
            "Render",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Overweigh transparency in rendering "
                "(0=None (default), 10=Very high)."
                "When this parameter is set, low transparency ratios will "
                "be rendered more transparent. NB: This parameter affects "
                "only implicit materials (generated via Shape "
                "Appearance), not explicit materials (defined via Material"
                " property).",
            ),
            (0, 0, 10, 1),
        ),
    }

    def on_set_properties_cb(self, fpo):
        """Complete the operation of internal _set_properties (callback)."""
        if "Group" not in fpo.PropertiesList:
            fpo.addExtension("App::GroupExtensionPython", self)
        fpo.setEditorMode("Group", 2)

    def onChanged(self, obj, prop):  # pylint: disable=no-self-use
        """Respond to property changed event (callback).

        This code is executed when a property of the FeaturePython object is
        changed.
        """
        if prop == "DelayedBuild" and not obj.DelayedBuild:
            for view in obj.Proxy.all_views():
                view.touch()
        if prop == "Renderer":
            obj.PageResult = ""

    def on_create_cb(self, fpo, viewp, **kwargs):
        """Complete the operation of 'create' (callback)."""
        rdr = str(kwargs["renderer"])
        template = str(kwargs.get("template", ""))

        fpo.Label = "%s Project" % rdr
        fpo.Renderer = rdr
        fpo.Template = str(template)

    def write_groundplane(self, renderer):
        """Generate a ground plane rendering string for the scene.

        For that purpose, dummy objects are temporarily added to the document
        which the project belongs to, and eventually deleted

        Args:
        ----------
        renderer -- the renderer handler

        Returns
        -------
        The rendering string for the ground plane
        """
        # Compute scene bounding box
        bbox = App.BoundBox()
        for view in self.all_views():
            try:
                bbox.add(view.Source.Shape.BoundBox)
            except AttributeError:
                pass

        # Compute rendering string
        result = ""
        if bbox.isValid():
            zpos = self.fpo.GroundPlaneZ
            color = self.fpo.GroundPlaneColor
            factor = self.fpo.GroundPlaneSizeFactor
            result = renderer.get_groundplane_string(bbox, zpos, color, factor)

        return result

    def add_views(self, objs):
        """Add objects as new views to the project.

        This method can handle objects groups, recursively.

        This function checks if each object is renderable before adding it,
        via 'RendererHandler.is_renderable'; if not, a warning is issued and
        the faulty object is ignored.

        Args::
        -----------
        objs -- an iterable on FreeCAD objects to add to project
        """

        def add_to_group(objs, group):
            """Add objects as views to a group.

            objs -- FreeCAD objects to add
            group -- The group (App::DocumentObjectGroup) to add to
            """
            for obj in objs:
                success = False
                if (
                    hasattr(obj, "Group")
                    and not obj.isDerivedFrom("App::Part")
                    and not obj.isDerivedFrom("PartDesign::Body")
                ):
                    assert obj != group  # Just in case (infinite recursion)...
                    label = View.view_label(obj, group, True)
                    new_group = App.ActiveDocument.addObject(
                        "App::DocumentObjectGroup", label
                    )
                    new_group.Label = label
                    group.addObject(new_group)
                    add_to_group(obj.Group, new_group)
                    success = True
                if RendererHandler.is_renderable(obj):
                    View.create(source=obj, project=group)
                    success = True
                if not success:
                    msg = (
                        translate(
                            "Render",
                            "[Render] Unable to create rendering view for "
                            "object '{o}': unhandled object type",
                        )
                        + "\n"
                    )
                    App.Console.PrintWarning(msg.format(o=obj.Label))

        # add_views starts here
        add_to_group(iter(objs), self.fpo)

    def all_views(self, include_groups=False):
        """Give the list of all the views contained in the project.

        Args:
            include_groups -- Flag to include containing groups (including
                the project) in returned objects. If False, only pure views are
                returned.
        """

        def all_group_objs(group, include_groups=False):
            """Return all objects in a group.

            This method recursively explodes subgroups.

            Args:
                group -- The group where the objects are to be searched.
                include_groups -- See 'all_views'
            """
            res = [] if not include_groups else [group]
            for obj in group.Group:
                res.extend(
                    [obj]
                    if not obj.isDerivedFrom("App::DocumentObjectGroup")
                    else all_group_objs(obj, include_groups)
                )
            return res

        return all_group_objs(self.fpo, include_groups)

    def render(self, external=True):
        """Render the project, calling an external renderer.

        Args:
            external -- flag to switch between internal/external version of
                renderer

        Returns:
            Output file path
        """
        obj = self.fpo

        # Get a handle to renderer module
        try:
            renderer = RendererHandler(
                rdrname=obj.Renderer,
                linear_deflection=obj.LinearDeflection,
                angular_deflection=obj.AngularDeflection,
                transparency_boost=obj.TransparencySensitivity,
            )
        except ModuleNotFoundError:
            msg = (
                translate(
                    "Render",
                    "[Render] Cannot render project: Renderer '%s' not "
                    "found",
                )
                + "\n"
            )
            App.Console.PrintError(msg % obj.Renderer)
            return ""

        # Get the rendering template
        if obj.getTypeIdOfProperty("Template") == "App::PropertyFile":
            # Legacy template path (absolute path)
            template_path = obj.Template
        else:
            # Current template path (relative path)
            template_path = os.path.join(TEMPLATEDIR, obj.Template)

        if not os.path.isfile(template_path):
            msg = translate(
                "Render", "Cannot render projet: Template not found ('%s')"
            )
            msg = "[Render] " + (msg % template_path) + "\n"
            App.Console.PrintError(msg)
            return ""

        with open(template_path, "r") as template_file:
            template = template_file.read()

        # Build a default camera, to be used if no camera is present in the
        # scene
        camstr = (
            Gui.ActiveDocument.ActiveView.getCamera()
            if App.GuiUp
            else DEFAULT_CAMERA_STRING
        )
        defaultcamview = SimpleNamespace()
        defaultcamview.Source = SimpleNamespace()
        defaultcamview.Source.Proxy = SimpleNamespace()
        defaultcamview.Source.Proxy.type = "Camera"
        defaultcamview.Source.Name = "Default_Camera"
        defaultcamview.Source.Label = "Default_Camera"
        defaultcamview.Name = "Default_CameraView"
        defaultcamview.Label = View.view_label(defaultcamview.Source, obj)
        set_cam_from_coin_string(defaultcamview.Source, camstr)
        cam = renderer.get_rendering_string(defaultcamview)
        del defaultcamview, camstr

        # Get objects rendering strings (including lights, cameras...)
        views = self.all_views()
        get_rdr_string = (
            renderer.get_rendering_string
            if obj.DelayedBuild
            else attrgetter("ViewResult")
        )
        if App.GuiUp:
            objstrings = [
                get_rdr_string(v)
                for v in views
                if v.Source.ViewObject.Visibility
            ]
        else:
            objstrings = [get_rdr_string(v) for v in views]

        # Add a ground plane if required
        if getattr(obj, "GroundPlane", False):
            objstrings.append(self.write_groundplane(renderer))

        # Merge all strings (cam, objects, ground plane...) into rendering
        # template
        renderobjs = "\n".join(objstrings)
        if "RaytracingCamera" in template:
            template = re.sub("(.*RaytracingCamera.*)", cam, template)
            template = re.sub("(.*RaytracingContent.*)", renderobjs, template)
        else:
            template = re.sub(
                "(.*RaytracingContent.*)", cam + "\n" + renderobjs, template
            )
        version_major = sys.version_info.major
        template = template.encode("utf8") if version_major < 3 else template

        # Write instantiated template into a temporary file
        fhandle, fpath = mkstemp(
            prefix=obj.Name, suffix=os.path.splitext(obj.Template)[-1]
        )
        with open(fpath, "w") as fobj:
            fobj.write(template)
        os.close(fhandle)
        obj.PageResult = fpath
        os.remove(fpath)
        assert obj.PageResult, "Rendering error: No page result"

        App.ActiveDocument.recompute()

        # Fetch the rendering parameters
        prefix = PARAMS.GetString("Prefix", "")
        if prefix:
            prefix += " "

        try:
            output = obj.OutputImage
            assert output
        except (AttributeError, AssertionError):
            output = os.path.splitext(obj.PageResult)[0] + ".png"

        try:
            width = int(obj.RenderWidth)
        except (AttributeError, ValueError, TypeError):
            width = 800

        try:
            height = int(obj.RenderHeight)
        except (AttributeError, ValueError, TypeError):
            height = 600

        # Run the renderer on the generated temp file, with rendering params
        img = renderer.render(obj, prefix, external, output, width, height)

        # Open result in GUI if relevant
        try:
            if img and obj.OpenAfterRender:
                ImageGui.open(img)
        except (AttributeError, NameError):
            pass

        # And eventually return result path
        return img


class ViewProviderProject(BaseViewProvider):
    """View provider for the rendering project object."""

    ICON = "RenderProject.svg"
    ALWAYS_VISIBLE = True
    CONTEXT_MENU = [
        CtxMenuItem(
            QT_TRANSLATE_NOOP("Render", "Render"),
            "render",
            "Render.svg",
        ),
        CtxMenuItem(
            QT_TRANSLATE_NOOP("Render", "Change template"),
            "change_template",
        ),
    ]

    def onDelete(self, vobj, subelements):
        """Respond to delete object event (callback)."""
        delete = True

        if self.fpo.Group:
            # Project is not empty
            title = translate("Render", "Warning: Deleting Non-Empty Project")
            msg = translate(
                "Render",
                "Project is not empty. "
                "All its contents will be deleted too.\n\n"
                "Are you sure you want to continue?",
            )
            box = QMessageBox(
                QMessageBox.Warning,
                title,
                msg,
                QMessageBox.Yes | QMessageBox.No,
            )
            usr_confirm = box.exec()
            if usr_confirm == QMessageBox.Yes:
                subobjs = self.fpo.Proxy.all_views(include_groups=True)[1:]
                for obj in subobjs:
                    obj.Document.removeObject(obj.Name)
            else:
                delete = False

        return delete

    def render(self):
        """Render project.

        This method calls proxy's 'render' method.
        """
        try:
            self.fpo.Proxy.render()
        except AttributeError as err:
            msg = translate("Render", "[Render] Cannot render: {e}") + "\n"
            App.Console.PrintError(msg.format(e=err))

    def change_template(self):
        """Change the template of the project."""
        fpo = self.fpo
        new_template = user_select_template(fpo.Renderer)
        if new_template:
            App.ActiveDocument.openTransaction("ChangeTemplate")
            if fpo.getTypeIdOfProperty("Template") != "App::PropertyString":
                # Ascending compatibility: convert Template property type if
                # still in legacy
                fpo.removeProperty("Template")
                fpo.Proxy.set_properties(fpo)
            fpo.Template = new_template
            App.ActiveDocument.commitTransaction()


def user_select_template(renderer):
    """Make user select a template for a given renderer.

    This method opens a UI file dialog and asks user to select a template file.
    The returned path is the *relative* path starting from Render.TEMPLATEDIR.

    Args:
        renderer -- a renderer name (str)

    Returns:
        A string containing the (relative) path to the selected template.
    """
    try:
        handler = RendererHandler(renderer)
    except RendererNotFoundError as err:
        msg = (
            "[Render] Failed to open template selector - Renderer '%s' "
            "not found\n"
        )
        App.Console.PrintError(msg % err.renderer)
        return None
    filefilter = handler.get_template_file_filter()
    filefilter += ";; All files (*.*)"
    caption = translate("Render", "Select template")
    openfilename = QFileDialog.getOpenFileName(
        Gui.getMainWindow(), caption, TEMPLATEDIR, filefilter
    )
    template_path = openfilename[0]
    if not template_path:
        return None
    return os.path.relpath(template_path, TEMPLATEDIR)
