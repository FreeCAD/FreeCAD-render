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

from PySide.QtGui import QAction, QIcon, QFileDialog, QMessageBox
from PySide.QtCore import QT_TRANSLATE_NOOP, QObject, SIGNAL
import FreeCAD as App
import FreeCADGui as Gui

from Render.constants import TEMPLATEDIR, ICONDIR
from Render.rdrhandler import RendererHandler, RendererNotFoundError
from Render.utils import translate
from Render.view import View
from Render.camera import DEFAULT_CAMERA_STRING, set_cam_from_coin_string


class Project:
    """A rendering project."""

    # Related FeaturePython object has to be stored in a class variable,
    # (not in an instance variable...), otherwise it causes trouble in
    # serialization...
    _fpos = dict()

    def __init__(self, obj):
        """Initialize Project class."""
        obj.Proxy = self
        self.set_properties(obj)

    @property
    def fpo(self):
        """Get underlying FeaturePython object."""
        return self._fpos[id(self)]

    @fpo.setter
    def fpo(self, new_fpo):
        """Set underlying FeaturePython object."""
        self._fpos[id(self)] = new_fpo

    def set_properties(self, obj):
        """Set underlying FeaturePython object's properties.

        Args:
            obj -- FeaturePython Object related to this project
        """
        self.fpo = obj
        self.__module__ = "Render"

        if "Renderer" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyString",
                "Renderer",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The name of the raytracing engine to use"))

        if "DelayedBuild" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyBool",
                "DelayedBuild",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "If true, the views will be updated on render only"))
            obj.DelayedBuild = True

        if "Template" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyString",
                "Template",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The template to be used by this rendering "
                    "(use Project's context menu to modify)"))
            obj.setEditorMode("Template", 1)

        if "PageResult" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyFileIncluded",
                "PageResult",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The result file to be sent to the renderer"))
        obj.setEditorMode("PageResult", 2)

        if "Group" not in obj.PropertiesList:
            obj.addExtension("App::GroupExtensionPython", self)

        if "RenderWidth" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyInteger",
                "RenderWidth",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The width of the rendered image in pixels"))
            parname = "User parameter:BaseApp/Preferences/Mod/Render"
            obj.RenderWidth = App.ParamGet(parname).GetInt("RenderWidth", 800)

        if "RenderHeight" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyInteger",
                "RenderHeight",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The height of the rendered image in pixels"))
            par = "User parameter:BaseApp/Preferences/Mod/Render"
            obj.RenderHeight = App.ParamGet(par).GetInt("RenderHeight", 600)

        if "GroundPlane" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyBool",
                "GroundPlane",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "If true, a default ground plane will be added to the "
                    "scene"))
            obj.GroundPlane = False

        if "GroundPlaneZ" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyDistance",
                "GroundPlaneZ",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Z position for ground plane"))
            obj.GroundPlaneZ = 0

        if "GroundPlaneColor" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyColor",
                "GroundPlaneColor",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Ground plane color"))
            obj.GroundPlaneColor = (0.8, 0.8, 0.8)

        if "GroundPlaneSizeFactor" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyFloat",
                "GroundPlaneSizeFactor",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Ground plane size factor"))
            obj.GroundPlaneSizeFactor = 1.0

        if "OutputImage" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyFile",
                "OutputImage",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The image saved by this render"))

        if "OpenAfterRender" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyBool",
                "OpenAfterRender",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "If true, the rendered image is opened in FreeCAD after "
                    "the rendering is finished"))
            obj.OpenAfterRender = True

        if "LinearDeflection" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyFloat",
                "LinearDeflection",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Linear deflection for the mesher: "
                    "The maximum linear deviation of a mesh section from the "
                    "surface of the object."))
            obj.LinearDeflection = 0.1

        if "AngularDeflection" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyFloat",
                "AngularDeflection",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Angular deflection for the mesher: "
                    "The maximum angular deviation from one mesh section to "
                    "the next, in radians. This setting is used when meshing "
                    "curved surfaces."))
            obj.AngularDeflection = math.pi / 6

        if "TransparencySensitivity" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "TransparencySensitivity",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Overweigh transparency in rendering "
                    "(0=None (default), 10=Very high)."
                    "When this parameter is set, low transparency ratios will "
                    "be rendered more transparent. NB: This parameter affects "
                    "only implicit materials (generated via Shape "
                    "Appearance), not explicit materials (defined via Material"
                    " property)."))
            obj.TransparencySensitivity = (0, 0, 10, 1)

    def onDocumentRestored(self, obj):  # pylint: disable=no-self-use
        """Respond to document restoration event (callback)."""
        self.set_properties(obj)

    def execute(self, obj):  # pylint: disable=no-self-use
        """Respond to document recomputation event (callback, mandatory)."""
        return True

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

    @staticmethod
    def create(document, renderer, template=""):
        """Create a new rendering project (factory method).

        This method creates a new rendering project in a given FreeCAD
        Document.
        Providing a Document is mandatory: no rendering project should be
        created "off-ground".
        The method also creates the FeaturePython and the ViewProviderProject
        objects related to the new rendering project.

        Args:
        ----------
        document -- the document where the project is to be created
        renderer -- the path to the renderer module to associate with
            project
        template -- (opt.) the path to the rendering template to associate with
            project

        Returns: the newly created Project, the related FeaturePython object
                 and the related ViewProviderProject
        """
        rdr = str(renderer)
        assert document, "Document must not be None"
        project_fpo = document.addObject("App::FeaturePython",
                                         "%sProject" % rdr)
        project = Project(project_fpo)
        project_fpo.Label = "%s Project" % rdr
        project_fpo.Renderer = rdr
        project_fpo.Template = str(template)
        viewp = ViewProviderProject(project_fpo.ViewObject)
        return project, project_fpo, viewp

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
                if (hasattr(obj, "Group") and
                        not obj.isDerivedFrom("App::Part") and
                        not obj.isDerivedFrom("PartDesign::Body")):
                    assert obj != group  # Just in case (infinite recursion)...
                    label = View.view_label(obj, group, True)
                    new_group = App.ActiveDocument.addObject(
                        "App::DocumentObjectGroup", label)
                    new_group.Label = label
                    group.addObject(new_group)
                    add_to_group(obj.Group, new_group)
                    success = True
                if RendererHandler.is_renderable(obj):
                    View.create(obj, group)
                    success = True
                if not success:
                    msg = translate(
                        "Render",
                        "[Render] Unable to create rendering view for object "
                        "'{o}': unhandled object type") + '\n'
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
                    [obj] if not obj.isDerivedFrom("App::DocumentObjectGroup")
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
                transparency_boost=obj.TransparencySensitivity)
        except ModuleNotFoundError:
            msg = translate(
                "Render",
                "[Render] Cannot render project: Renderer '%s' not "
                "found") + '\n'
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
            msg = translate("Render",
                            "Cannot render projet: Template not found ('%s')")
            msg = "[Render] " + (msg % template_path) + "\n"
            App.Console.PrintError(msg)
            return ""

        with open(template_path, "r") as template_file:
            template = template_file.read()

        # Build a default camera, to be used if no camera is present in the
        # scene
        camstr = (Gui.ActiveDocument.ActiveView.getCamera() if App.GuiUp
                  else DEFAULT_CAMERA_STRING)
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
        get_rdr_string =\
            renderer.get_rendering_string if obj.DelayedBuild\
            else attrgetter("ViewResult")
        if App.GuiUp:
            objstrings = [get_rdr_string(v) for v in views
                          if v.Source.ViewObject.Visibility]
        else:
            objstrings = [get_rdr_string(v) for v in views]

        # Add a ground plane if required
        if getattr(obj, "GroundPlane", False):
            objstrings.append(self.write_groundplane(renderer))

        # Merge all strings (cam, objects, ground plane...) into rendering
        # template
        renderobjs = '\n'.join(objstrings)
        if "RaytracingCamera" in template:
            template = re.sub("(.*RaytracingCamera.*)", cam, template)
            template = re.sub("(.*RaytracingContent.*)", renderobjs, template)
        else:
            template = re.sub("(.*RaytracingContent.*)",
                              cam + "\n" + renderobjs, template)
        template = (template.encode("utf8") if sys.version_info.major < 3
                    else template)

        # Write instantiated template into a temporary file
        fhandle, fpath = mkstemp(prefix=obj.Name,
                                 suffix=os.path.splitext(obj.Template)[-1])
        with open(fpath, "w") as fobj:
            fobj.write(template)
        os.close(fhandle)
        obj.PageResult = fpath
        os.remove(fpath)
        assert obj.PageResult, "Rendering error: No page result"

        App.ActiveDocument.recompute()

        # Fetch the rendering parameters
        params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
        prefix = params.GetString("Prefix", "")
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


class ViewProviderProject:
    """View provider for the rendering project object."""

    def __init__(self, vobj):
        """Initialize view provider."""
        vobj.Proxy = self
        self.object = vobj.Object
        self.__module__ = "Render"

    def attach(self, vobj):  # pylint: disable=no-self-use
        """Respond to created/restored object event (callback)."""
        self.object = vobj.Object
        self.__module__ = "Render"
        return True

    def onDelete(self, vobj, subelements):
        """Respond to delete object event (callback)."""
        delete = True

        if self.object.Group:
            # Project is not empty
            title = translate("Render", "Warning: Deleting Non-Empty Project")
            msg = translate(
                "Render",
                "Project is not empty. "
                "All its contents will be deleted too.\n\n"
                "Are you sure you want to continue?")
            box = QMessageBox(
                QMessageBox.Warning,
                title,
                msg,
                QMessageBox.Yes | QMessageBox.No)
            usr_confirm = box.exec()
            if usr_confirm == QMessageBox.Yes:
                subobjs = self.object.Proxy.all_views(include_groups=True)[1:]
                for obj in subobjs:
                    obj.Document.removeObject(obj.Name)
            else:
                delete = False

        return delete

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

    def isShow(self):  # pylint: disable=no-self-use
        """Define the visibility of the object in the tree view (callback)."""
        return True

    def getIcon(self):  # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)."""
        return os.path.join(ICONDIR, "RenderProject.svg")

    def setupContextMenu(self, vobj, menu):  # pylint: disable=no-self-use
        """Set up the object's context menu in GUI (callback)."""
        icon = QIcon(os.path.join(ICONDIR, "Render.svg"))
        action1 = QAction(icon, "Render", menu)
        QObject.connect(action1, SIGNAL("triggered()"), self.render)
        menu.addAction(action1)

        action2 = QAction(QT_TRANSLATE_NOOP("Render", "Change template"),
                          menu)
        QObject.connect(action2,
                        SIGNAL("triggered()"),
                        self.change_template)
        menu.addAction(action2)

    def claimChildren(self):
        """Deliver the children belonging to this object (callback)."""
        try:
            return self.object.Group
        except AttributeError:
            return []

    def render(self):
        """Render project.

        This method calls proxy's 'render' method.
        """
        try:
            self.object.Proxy.render()
        except AttributeError as err:
            msg = translate("Render", "[Render] Cannot render: {e}") + '\n'
            App.Console.PrintError(msg.format(e=err))

    def change_template(self):
        """Change the template of the project."""
        fpo = self.object
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
        msg = ("[Render] Failed to open template selector - Renderer '%s' "
               "not found\n")
        App.Console.PrintError(msg % err.renderer)
        return None
    filefilter = handler.get_template_file_filter()
    filefilter += ";; All files (*.*)"
    caption = translate("Render", "Select template")
    openfilename = QFileDialog.getOpenFileName(
        Gui.getMainWindow(), caption, TEMPLATEDIR, filefilter)
    template_path = openfilename[0]
    if not template_path:
        return None
    return os.path.relpath(template_path, TEMPLATEDIR)
