# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
# *   Copyright (c) 2023 Howetuft <howetuft@gmail.com>                      *
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
from collections import namedtuple
import concurrent.futures
import time

from PySide.QtGui import QFileDialog, QMessageBox
from PySide.QtCore import QT_TRANSLATE_NOOP
import FreeCAD as App
import FreeCADGui as Gui

from Render.constants import TEMPLATEDIR, PARAMS, FCDVERSION
from Render.rdrhandler import RendererHandler, RendererNotFoundError
from Render.rdrexecutor import RendererExecutor
from Render.utils import (
    translate,
    set_last_cmd,
    clear_report_view,
    fcdcolor2rgba,
)
from Render.view import View
from Render.camera import DEFAULT_CAMERA_STRING, get_cam_from_coin_string
from Render.base import FeatureBase, Prop, ViewProviderBase, CtxMenuItem


class Project(FeatureBase):
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
        "BatchMode": Prop(
            "App::PropertyBool",
            "Execution Control",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Execute in batch mode (True) or GUI interactive mode (False)",
            ),
            False,
        ),
        "SamplesPerPixel": Prop(
            "App::PropertyInteger",
            "Execution Control",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Halt condition: number of samples per pixel "
                "(0 or negative = indefinite).",
            ),
            0,
        ),
        "Denoiser": Prop(
            "App::PropertyBool",
            "Execution Control",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "Make renderer invoke denoiser. WARNING: may not work with "
                "all renderers - the renderer must have denoising "
                "capabilities.",
            ),
            False,
        ),
    }

    ON_CHANGED = {
        "DelayedBuild": "_on_changed_delayed_build",
    }

    def on_set_properties_cb(self, fpo):
        """Complete the operation of internal _set_properties (callback)."""
        if "Group" not in fpo.PropertiesList:
            if FCDVERSION >= (0, 19):
                fpo.addExtension("App::GroupExtensionPython")
                # See https://forum.freecadweb.org/viewtopic.php?f=10&t=54370
            else:
                fpo.addExtension("App::GroupExtensionPython", self)
        fpo.setEditorMode("Group", 2)

    def _on_changed_delayed_build(self, fpo):
        """Respond to DelayedBuild property change event."""
        if fpo.DelayedBuild:
            return
        for view in self.all_views():
            view.touch()

    def on_create_cb(self, fpo, viewp, **kwargs):
        """Complete the operation of 'create' (callback)."""
        rdr = str(kwargs["renderer"])
        template = str(kwargs.get("template", ""))

        fpo.Label = f"{rdr} Project"
        fpo.Renderer = rdr
        fpo.Template = template

    def get_bounding_box(self):
        """Compute project bounding box.

        This the bounding box of the underlying objects referenced in the
        scene.
        """
        bbox = App.BoundBox()
        for view in self.all_views():
            source = view.Source
            for attr_name in ("Shape", "Mesh"):
                try:
                    attr = getattr(source, attr_name)
                except AttributeError:
                    pass
                else:
                    bbox.add(attr.BoundBox)
                    break
        return bbox

    def write_groundplane(self, renderer):
        """Generate a ground plane rendering string for the scene.

        Args:
        ----------
        renderer -- the renderer handler

        Returns
        -------
        The rendering string for the ground plane
        """
        bbox = self.get_bounding_box()
        result = ""
        if bbox.isValid():
            zpos = self.fpo.GroundPlaneZ
            color = fcdcolor2rgba(self.fpo.GroundPlaneColor)
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
        if not self.fpo.DelayedBuild:
            App.ActiveDocument.recompute()

    def add_view(self, obj):
        """Add a single object as a new view to the project.

        This method is essentially provided for console mode, as above method
        'add_views' may not be handy for a single object.  However, it heavily
        relies on 'add_views', so please check the latter for more information.

        Args::
        -----------
        obj -- a FreeCAD object to add to project
        """
        objs = []
        objs.append(obj)
        self.add_views(objs)

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

    def render(self, wait_for_completion=False):
        """Render the project, calling an external renderer.

        Args:
            wait_for_completion -- flag to wait for rendering completion before
                return, in a blocking way (default to False)

        Returns:
            Output file path
        """
        wait_for_completion = bool(wait_for_completion)

        # Check project parameters
        if self.fpo.RenderHeight <= 0 or self.fpo.RenderWidth <= 0:
            msg = translate(
                "Render",
                "[Render][Project] CRITICAL ERROR - Negative or zero value(s) "
                "for Render Height and/or Render Width: cannot render. "
                "Aborting...\n",
            )
            App.Console.PrintError(msg)
            return None

        # Set export directories
        project_directory = self.fpo.Document.TransientDir
        object_directory = os.path.join(project_directory, self.fpo.Name)
        if not os.path.exists(object_directory):
            os.mkdir(object_directory)

        # Clear report view (if required)
        clear_report = PARAMS.GetBool("ClearReport")
        if clear_report:
            clear_report_view()

        # Get a handle to renderer module
        try:
            renderer = RendererHandler(
                rdrname=self.fpo.Renderer,
                linear_deflection=self.fpo.LinearDeflection,
                angular_deflection=self.fpo.AngularDeflection,
                transparency_boost=self.fpo.TransparencySensitivity,
                project_directory=project_directory,
                object_directory=object_directory,
            )
        except RendererNotFoundError as err:
            msg = translate("Render", "Renderer not found ('{}') ")
            msg = msg.format(self.fpo.Renderer)
            raise RenderingError(msg) from err

        # Get the rendering template
        template = self._get_rendering_template()

        # Build a default camera, to be used if no camera is present in the
        # scene
        defaultcam = _get_default_cam(renderer, self.fpo)

        # Get objects rendering strings (including lights, cameras...)
        objstrings = self._get_objstrings(renderer)

        # Add a ground plane if required
        if getattr(self.fpo, "GroundPlane", False):
            objstrings.append(self.write_groundplane(renderer))

        # Instantiate template: merge all strings (cam, objects, ground
        # plane...) into rendering template
        instantiated = _instantiate_template(template, objstrings, defaultcam)

        # Write instantiated template into a temporary file
        fpath = self._write_instantiated_template_to_file(
            instantiated, project_directory
        )

        # Fetch the rendering parameters
        params = self._get_rendering_params()

        # Get the renderer command on the generated temp file, with rendering
        # params
        cmd, img = renderer.render(
            self.fpo,
            params.prefix,
            params.batch,
            fpath,
            params.output,
            params.width,
            params.height,
            params.spp,
            params.denoise,
        )
        if not cmd:
            # Command is empty (perhaps lack of data in parameters)
            msg = translate("Render", "Empty rendering command")
            raise RenderingError(msg)

        # Record this command (debug purpose)
        set_last_cmd(cmd)

        # Dry run?
        dryrun = PARAMS.GetBool("DryRun")
        if dryrun:
            # "Dry run": Print command and return without running renderer
            # Debug purpose only
            App.Console.PrintWarning("*** DRY RUN ***\n")
            App.Console.PrintMessage(cmd)
            return None

        # Execute renderer
        rdr_executor = RendererExecutor(
            cmd, img, self.fpo.OpenAfterRender, os.path.dirname(fpath)
        )
        rdr_executor.start()
        if wait_for_completion:
            # Useful in console mode...
            rdr_executor.join()

        # And eventually return result path
        return img

    def _get_rendering_template(self):
        """Get the rendering template for the project.

        This method is a (private) subroutine of `render` method.
        RenderingError is raised if template file is not found.
        """
        # Compute template_path from project's Template parameter.
        # This parameter gives a relative path to template.
        # However, a legacy behaviour (absolute path) is also handled.
        if self.fpo.getTypeIdOfProperty("Template") == "App::PropertyFile":
            # Legacy template path (absolute path)
            template_path = self.fpo.Template
        else:
            # Current template path (relative path)
            template_path = os.path.join(TEMPLATEDIR, self.fpo.Template)

        # Open file and get content
        try:
            with open(template_path, "r", encoding="utf8") as template_file:
                template = template_file.read()
        except FileNotFoundError as err:
            msg = translate("Render", "Template not found ('{}')")
            msg = msg.format(template_path)
            raise RenderingError(msg) from err

        return template

    def _get_objstrings(self, renderer):
        """Get rendering strings for all objects in project.

        This method is a (private) subroutine of `render` method.
        Besides standard FCD objects (parts, shapes...), objects encompass
        lights and cameras.
        """
        # Gather the views to render
        # If App.Gui is up, we take View's Visibility property into account
        views = (
            [v for v in self.all_views() if v.Source.ViewObject.Visibility]
            if App.GuiUp
            else self.all_views()
        )

        # If DelayedBuild is false, we rely on views' ViewResult precomputed
        # values.
        if not self.fpo.DelayedBuild:
            return [v.ViewResult for v in views]

        # Otherwise, we have to compute strings
        get_rdr_string = renderer.get_rendering_string
        objstrings = _get_objstrings_helper(get_rdr_string, views)

        return objstrings

    def _write_instantiated_template_to_file(self, template, directory):
        """Write an instantiated template to a temporary file.

        This method is a (private) subroutine of `render` method.

        Returns path to temp file.
        """
        _, suffix = os.path.splitext(self.fpo.Template)
        fpath = os.path.join(directory, self.fpo.Name + suffix)
        with open(fpath, "w", encoding="utf8") as fobj:
            fobj.write(template)
        return fpath

    def _get_rendering_params(self):
        """Fetch the rendering parameters.

        This method is a (private) subroutine of `render` method.
        """
        Params = namedtuple(
            "Params", "prefix output width height batch spp denoise"
        )

        prefix = PARAMS.GetString("Prefix", "")
        if prefix:
            prefix += " "

        try:
            output = self.fpo.OutputImage
            assert output
        except (AttributeError, AssertionError):
            fname = f"{self.fpo.Name}_output.png"
            output = os.path.join(self.fpo.Document.TransientDir, fname)

        try:
            width = int(self.fpo.RenderWidth)
        except (AttributeError, ValueError, TypeError):
            width = 800

        try:
            height = int(self.fpo.RenderHeight)
        except (AttributeError, ValueError, TypeError):
            height = 600

        try:
            batch = bool(self.fpo.BatchMode)
        except (AttributeError, ValueError, TypeError):
            batch = False

        try:
            spp = int(self.fpo.SamplesPerPixel)
            spp = spp if spp >= 0 else 0
        except (AttributeError, ValueError, TypeError):
            spp = 32

        try:
            denoise = bool(self.fpo.Denoiser)
        except (AttributeError, ValueError, TypeError):
            denoise = False

        return Params(prefix, output, width, height, batch, spp, denoise)


def _get_default_cam(renderer, project):
    """Build a default camera for rendering.

    This function is a (private) subroutine of `render` method.
    If GUI is up, the default camera is built from the ActiveView camera, ie
    the camera from which objects are seen in FreeCAD viewport. Otherwise
    (console mode), the camera is built from a hardcoded value, hosted in
    DEFAULT_CAMERA_STRING constant.
    """
    camstr = (
        Gui.ActiveDocument.ActiveView.getCamera()
        if App.GuiUp
        else DEFAULT_CAMERA_STRING
    )
    try:
        camsource = get_cam_from_coin_string(camstr)
    except ValueError:
        camsource = get_cam_from_coin_string(DEFAULT_CAMERA_STRING)
    return renderer.get_camsource_string(camsource, project)


def _instantiate_template(template, objstrings, defaultcam):
    """Instantiate template (merge all objects into template).

    This function is a (private) subroutine of `render` method.
    """
    renderobjs = "\n".join(objstrings)

    if "RaytracingCamera" in template:
        template = re.sub("(.*RaytracingCamera.*)", defaultcam, template)
        template = re.sub("(.*RaytracingContent.*)", renderobjs, template)
    else:
        content = defaultcam + "\n" + renderobjs
        template = re.sub("(.*RaytracingContent.*)", content, template)

    version_major = sys.version_info.major

    return template.encode("utf8") if version_major < 3 else template


class RenderingError(Exception):
    """Exception to be raised when a blocking error occurs during rendering."""

    def __init__(self, message):
        """Initialize exception."""
        super().__init__()
        prefix1 = "[Render] "
        prefix2 = translate("Render", "Cannot render project:")
        self.message = prefix1 + prefix2 + " " + message


class ViewProviderProject(ViewProviderBase):
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

    def __init__(self, vobj):
        super().__init__(vobj)
        # This is a workaround to avoid a subtle bug in _ArchMaterial.execute
        # if a material is erroneously set on the project (it can happen...)
        vobj.addProperty(
            "App::PropertyBool", "UseMaterialColor"
        ).UseMaterialColor = False

    def on_delete_cb(self, feature, subelements):
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
            render_method = self.fpo.Proxy.render
        except AttributeError as err:
            msg = translate("Render", "[Render] Cannot render: {e}") + "\n"
            App.Console.PrintError(msg.format(e=err))
            return

        try:
            render_method()
        except RenderingError as err:
            App.Console.PrintError(err.message + "\n")

    def change_template(self):
        """Change the template of the project."""
        fpo = self.fpo
        new_template = user_select_template(fpo.Renderer)
        if new_template:
            App.ActiveDocument.openTransaction("ChangeTemplate")
            if fpo.getTypeIdOfProperty("Template") != "App::PropertyString":
                # Ascending compatibility: convert Template property type if
                # still of legacy type
                fpo.Proxy.reset_property("Template")
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


def _get_objstrings_helper(get_rdr_string, views, run_concurrent=True):
    """Get strings from renderer (helper).

    This helper is convenient for debugging purpose (easier to reload).
    """
    if PARAMS.GetBool("EnableMultiprocessing"):
        run_concurrent = False  # runpy is not compatible with multithread...

    if run_concurrent:
        App.Console.PrintLog(
            "[Render][Objstrings] STARTING - CONCURRENT MODE\n"
        )
        time0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(get_rdr_string, view) for view in views]
            objstrings = [
                f.result() for f in concurrent.futures.as_completed(futures)
            ]
    else:
        App.Console.PrintLog(
            "[Render][Objstrings] STARTING - SEQUENTIAL MODE\n"
        )
        time0 = time.time()
        objstrings = [get_rdr_string(v) for v in views]

    App.Console.PrintLog(
        f"[Render][Objstrings] ENDED - TIME: {time.time() - time0}\n"
    )
    return objstrings
