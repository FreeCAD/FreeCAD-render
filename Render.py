# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
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


"""This is Render workbench main module.

It provides the necessary objects to deal with rendering:
- GUI Commands
- Rendering Projects and Views
- A RendererHandler class to simplify access to external renderers modules

On initialization, this module will retrieve all renderer modules and create
the necessary UI controls.
"""


# ===========================================================================
#                                   Imports
# ===========================================================================


import sys
import os
import re
import itertools
import functools
import collections
import traceback
from importlib import import_module
from tempfile import mkstemp
from types import SimpleNamespace
from operator import attrgetter

from PySide.QtGui import QAction, QIcon, QFileDialog
from PySide.QtCore import QT_TRANSLATE_NOOP, QObject, SIGNAL
import FreeCAD as App
import FreeCADGui as Gui
import Draft
import Part
import MeshPart
import ArchMaterial
try:
    import ImageGui
except ImportError:
    pass
try:
    from draftutils.translate import translate  # 0.19
except ImportError:
    from Draft import translate  # 0.18

import camera
import lights
import materials


# ===========================================================================
#                                 Constants
# ===========================================================================


# Paths to GUI resources
# This is for InitGui.py because it cannot import os
WBDIR = os.path.dirname(__file__)  # Workbench root directory
RDRDIR = os.path.join(WBDIR, "renderers")
ICONDIR = os.path.join(WBDIR, "icons")
PREFPAGE = os.path.join(WBDIR, "ui", "RenderSettings.ui")
# Renderers list
RENDERERS = [x.group(1)
             for x in map(lambda x: re.match(r"^([A-Z].*)\.py$", x),
                          os.listdir(RDRDIR))
             if x]
DEPRECATED_RENDERERS = ["Luxrender"]


# ===========================================================================
#                                  Utilities
# ===========================================================================


def debug(domain, object_name, msg):
    """Print debug message"""
    msg = "[Render][{d}] '{n}': {m}\n".format(d=domain, n=object_name, m=msg)
    App.Console.PrintLog(msg)


def getproxyattr(obj, name, default):
    """Get attribute on object's proxy

    Behaves like getattr, but on Proxy property, and with mandatory default...
    """
    try:
        res = getattr(obj.Proxy, name, default)
    except AttributeError:
        res = default
    return res


# ===========================================================================
#                     Core rendering objects (Project and View)
# ===========================================================================


class Project:
    """A rendering project"""

    # Related FeaturePython object has to be stored in a class variable,
    # (not in an instance variable...), otherwise it causes trouble in
    # serialization...
    _fpos = dict()

    def __init__(self, obj):
        obj.Proxy = self
        self.set_properties(obj)

    @property
    def fpo(self):
        """Underlying FeaturePython object getter"""
        return self._fpos[id(self)]

    @fpo.setter
    def fpo(self, new_fpo):
        """Underlying FeaturePython object setter"""
        self._fpos[id(self)] = new_fpo

    def set_properties(self, obj):
        """Set underlying FeaturePython object's properties

        Parameters
        ----------
        obj: FeaturePython Object related to this project
        """
        self.fpo = obj

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
                "App::PropertyFile",
                "Template",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The template to be used by this rendering"))

        if "PageResult" not in obj.PropertiesList:
            obj.addProperty(
                "App::PropertyFileIncluded",
                "PageResult",
                "Render",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "The result file to be sent to the renderer"))

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
            obj.GroundPlane = False
        obj.setEditorMode("PageResult", 2)

    def onDocumentRestored(self, obj):  # pylint: disable=no-self-use
        """Code to be executed when document is restored (callback)"""
        self.set_properties(obj)

    def execute(self, obj):  # pylint: disable=no-self-use
        """Code to be executed on document recomputation
        (callback, mandatory)
        """
        return True

    def onChanged(self, obj, prop):  # pylint: disable=no-self-use
        """Code to be executed when a property of the FeaturePython object is
        changed (callback)
        """
        if prop == "DelayedBuild" and not obj.DelayedBuild:
            for view in obj.Proxy.all_views():
                view.touch()

    @staticmethod
    def create(document, renderer, template=""):
        """Factory method to create a new rendering project.

        This method creates a new rendering project in a given FreeCAD
        Document.
        Providing a Document is mandatory: no rendering project should be
        created "off-ground".
        The method also creates the FeaturePython and the ViewProviderProject
        objects related to the new rendering project.

        Params:
        document:        the document where the project is to be created
        renderer:        the path to the renderer module to associate with
                         project
        template (opt.): the path to the rendering template to associate with
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
        """Generate a ground plane rendering string for the scene

        For that purpose, dummy objects are temporarily added to the document
        which the project belongs to, and eventually deleted

        Parameters
        ----------
        renderer:   the renderer handler

        Returns
        -------
        The rendering string for the ground plane
        """
        result = ""
        doc = self.fpo.Document
        bbox = App.BoundBox()
        for view in self.all_views():
            try:
                bbox.add(view.Source.Shape.BoundBox)
            except AttributeError:
                pass
        if bbox.isValid():
            # Create temporary object. We do this to keep renderers codes as
            # simple as possible: they only need to deal with one type of
            # object: RenderView objects
            margin = bbox.DiagonalLength / 2
            vertices = [App.Vector(bbox.XMin - margin, bbox.YMin - margin, 0),
                        App.Vector(bbox.XMax + margin, bbox.YMin - margin, 0),
                        App.Vector(bbox.XMax + margin, bbox.YMax + margin, 0),
                        App.Vector(bbox.XMin - margin, bbox.YMax + margin, 0)]
            vertices.append(vertices[0])  # Close the polyline...
            dummy1 = doc.addObject("Part::Feature", "dummygroundplane1")
            dummy1.Shape = Part.Face(Part.makePolygon(vertices))
            dummy2 = doc.addObject("App::FeaturePython", "dummygroundplane2")
            View(dummy2)
            dummy2.Source = dummy1
            ViewProviderView(dummy2.ViewObject)
            doc.recompute()

            result = renderer.get_rendering_string(dummy2)

            # Remove temp objects
            doc.removeObject(dummy2.Name)
            doc.removeObject(dummy1.Name)
            doc.recompute()

        return result

    def add_views(self, objs):
        """Add objects as new views to the project

        This method can handle objects groups, recursively.

        This function checks if each object is renderable before adding it,
        via 'RendererHandler.is_renderable'; if not, a warning is issued and
        the faulty object is ignored.

        Parameters
        objs -- an iterable on FreeCAD objects to add to project
        """

        def add_to_group(objs, group):
            """Add objects as views to a group

            objs -- FreeCAD objects to add
            group -- The  group (App::DocumentObjectGroup) to add to"""
            for obj in objs:
                if (obj.isDerivedFrom("App::DocumentObjectGroup") or
                        (obj.isDerivedFrom("App::GeometryPython") and
                         getproxyattr(obj, "Type", "") == "BuildingPart")):
                    assert obj != group  # Just in case...
                    label = View.view_label(obj, group)
                    new_group = App.ActiveDocument.addObject(
                        "App::DocumentObjectGroup", label)
                    new_group.Label = label
                    new_group.addProperty(
                        "App::PropertyLink",
                        "Source",
                        "Render",
                        QT_TRANSLATE_NOOP("App::Property",
                                          "The source object of this group"))
                    new_group.Source = obj  # For debug purpose...
                    group.addObject(new_group)
                    add_to_group(obj.Group, new_group)
                elif RendererHandler.is_renderable(obj):
                    View.create(obj, group)
                else:
                    msg = translate(
                        "Render",
                        "[Render] Unable to create rendering view for object "
                        "'{}': unhandled object type\n")
                    App.Console.PrintWarning(msg.format(obj.Label))

        # Here starts add_views
        add_to_group(iter(objs), self.fpo)

    def all_views(self):
        """Give the list of all views contained in the project"""
        def all_group_objs(group):
            """Returns all objects in group (recursively exploding
            subgroups)
            """
            res = []
            for obj in group.Group:
                res.extend(
                    [obj] if not obj.isDerivedFrom("App::DocumentObjectGroup")
                    else all_group_objs(obj)
                    )
            return res
        return all_group_objs(self.fpo)

    def render(self, external=True):
        """Render the project, calling external renderer

        Parameters
        ----------
        external: switch between internal/external version of renderer

        Returns
        -------
        Output file path
        """
        obj = self.fpo

        # Get a handle to renderer module
        try:
            renderer = RendererHandler(obj.Renderer)
        except ModuleNotFoundError:
            msg = translate(
                "Render",
                "[Render] Cannot render project: Renderer '%s' not found\n")
            App.Console.PrintError(msg % obj.Renderer)
            return ""

        # Get the rendering template
        assert (obj.Template and os.path.exists(obj.Template)),\
            "Cannot render project: Template not found"
        template = None
        with open(obj.Template, "r") as template_file:
            template = template_file.read()
        if sys.version_info.major < 3:
            template = template.decode("utf8")

        # Build a default camera, to be used if no camera is present in the
        # scene
        camstr = (Gui.ActiveDocument.ActiveView.getCamera() if App.GuiUp
                  else camera.DEFAULT_CAMERA_STRING)
        defaultcamview = SimpleNamespace()
        defaultcamview.Source = SimpleNamespace()
        defaultcamview.Source.Proxy = SimpleNamespace()
        defaultcamview.Source.Proxy.type = "Camera"
        defaultcamview.Source.Name = "Default_Camera"
        defaultcamview.Source.Label = "Default_Camera"
        defaultcamview.Name = "Default_CameraView"
        defaultcamview.Label = View.view_label(defaultcamview.Source, obj)
        camera.set_cam_from_coin_string(defaultcamview.Source, camstr)
        cam = renderer.get_rendering_string(defaultcamview)
        del defaultcamview, camstr

        # Get objects rendering strings (including lights, cameras...)
        views = self.all_views()
        get_rdr_string =\
            renderer.get_rendering_string if obj.DelayedBuild\
            else attrgetter("ViewResult")
        objstrings = [get_rdr_string(v) for v in views
                      if v.Source.ViewObject.Visibility]

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
    """View provider for rendering project object"""

    def __init__(self, vobj):
        vobj.Proxy = self
        self.object = vobj.Object

    def attach(self, vobj):  # pylint: disable=no-self-use
        """Code to be executed when object is created/restored (callback)"""
        self.object = vobj.Object
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def getDisplayModes(self, vobj):  # pylint: disable=no-self-use
        """Return a list of display modes (callback)"""
        return ["Default"]

    def getDefaultDisplayMode(self):  # pylint: disable=no-self-use
        """Return the name of the default display mode (callback).
        This display mode  must be defined in getDisplayModes.
        """
        return "Default"

    def setDisplayMode(self, mode):  # pylint: disable=no-self-use
        """Map the display mode defined in attach with those defined in
        getDisplayModes (callback).

        Since they have the same names nothing needs to be done.
        This method is optional
        """
        return mode

    def isShow(self):  # pylint: disable=no-self-use
        """Define the visibility of the object in the tree view (callback)"""
        return True

    def getIcon(self):  # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)."""
        return os.path.join(WBDIR, "icons", "RenderProject.svg")

    def setupContextMenu(self, vobj, menu):  # pylint: disable=no-self-use
        """Setup the context menu associated to the object in tree view
        (callback)"""
        icon = QIcon(os.path.join(WBDIR, "icons", "Render.svg"))
        action1 = QAction(icon, "Render", menu)
        QObject.connect(action1, SIGNAL("triggered()"), self.render)
        menu.addAction(action1)

    def claimChildren(self):  # pylint: disable=no-self-use
        """Deliver the children belonging to this object (callback)"""
        try:
            return self.object.Group
        except AttributeError:
            pass

    def render(self):
        """Render project (call proxy render)"""
        try:
            self.object.Proxy.render()
        except AttributeError as err:
            msg = translate("Render", "[Render] Cannot render: {}\n")
            App.Console.PrintError(msg.format(err))


class View:
    """A rendering view of a FreeCAD object"""

    # Related FeaturePython object has to be stored in a class variable,
    # (not in an instance variable...), otherwise it causes trouble in
    # serialization...
    _fpos = dict()

    def __init__(self, obj):
        obj.Proxy = self
        self.set_properties(obj)

    @property
    def fpo(self):
        """Underlying FeaturePython object getter"""
        return self._fpos[id(self)]

    @fpo.setter
    def fpo(self, new_fpo):
        """Underlying FeaturePython object setter"""
        self._fpos[id(self)] = new_fpo

    def set_properties(self, obj):
        """Set underlying FeaturePython object's properties

        Parameters
        ----------
        obj: FeaturePython Object related to this project
        """
        self.fpo = obj

        obj.addProperty("App::PropertyLink",
                        "Source",
                        "Render",
                        QT_TRANSLATE_NOOP("App::Property",
                                          "The source object of this view"))
        obj.addProperty("App::PropertyLink",
                        "Material",
                        "Render",
                        QT_TRANSLATE_NOOP("App::Property",
                                          "The material of this view"))
        obj.addProperty("App::PropertyString",
                        "ViewResult",
                        "Render",
                        QT_TRANSLATE_NOOP("App::Property",
                                          "The rendering output of this view"))

    def onDocumentRestored(self, obj):  # pylint: disable=no-self-use
        """Code to be executed when document is restored (callback)"""
        self.set_properties(obj)

    def execute(self, obj):  # pylint: disable=no-self-use
        """Code to be executed on document recomputation
        (callback, mandatory)

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
        renderer = RendererHandler(proj.Renderer)
        obj.ViewResult = renderer.get_rendering_string(obj)

    @staticmethod
    def view_label(obj, proj):
        """Give a standard view label for an object

        obj -- object for which the view is build
        proj -- project in which the view will be inserted

        Both obj and proj should have valid Label attribute"""
        obj_label = str(obj.Label)
        proj_label = str(proj.Label)

        proj_label2 = proj_label.replace(" ", "")
        res = "{o}@{p}".format(o=obj_label, p=proj_label2)
        return res

    @staticmethod
    def create(fcd_obj, project):
        """Factory method to create a new rendering object in a given project.

        This method creates a new rendering object in a given rendering
        project, for a given FreeCAD object (of any type: Mesh, Part...).
        Please note that providing a Project is mandatory: no rendering
        view should be created "off-ground". Moreover, project's document
        and FreeCAD object document should be the same.
        The method also creates the FeaturePython and the ViewProviderView
        objects related to the new rendering view.

        Params:
        fcdobj:     the FreeCAD object for which the rendering view is to be
                    created
        project:    the rendering project in which the view is to be created

        Returns:    the newly created View, the related FeaturePython object
                    and the related ViewProviderView object
        """
        doc = project.Document
        assert doc == fcd_obj.Document,\
            "Unable to create View: Project and Object not in same document"
        fpo = doc.addObject("App::FeaturePython", "%sView" % fcd_obj.Name)
        fpo.Label = View.view_label(fcd_obj, project)
        view = View(fpo)
        fpo.Source = fcd_obj
        project.addObject(fpo)
        viewp = ViewProviderView(fpo.ViewObject)
        return view, fpo, viewp

    def get_freecad_material(self):
        """Get the freecad material that can be associated with a view

        Steps are the following (stop when a valid material is found):
        1. Look into the view object
        2. Look into the source object
        Returns None if no material is found
        """
        view = self.fpo

        for obj in (view, view.Source):
            try:
                res = obj.Material
                assert res
            except (AttributeError, AssertionError):
                continue
            else:
                return res
        return None  # Negative search

    def get_shape_color(self):
        """Get the RGBA color for a FreeCAD object as seen in viewport

        If the object does not hold any color data, a default
        RGBA(1.0, 1.0, 1.0, 1.0) is returned (white opaque).

        Returns:
        The RGBA color, as a (named) tuple
        """
        source = self.fpo.Source
        # Get RGB
        try:
            shape_color = source.ViewObject.ShapeColor[:3]
        except (AttributeError, IndexError):
            shape_color = (1.0, 1.0, 1.0)

        # Get alpha
        try:
            assert 0 <= source.ViewObject.Transparency <= 100
            shape_alpha = 1.0 - source.ViewObject.Transparency / 100
        except (AttributeError, IndexError, AssertionError):
            shape_alpha = 1.0
        RGBA = collections.namedtuple("RGBA", "r g b a")
        return RGBA(*shape_color, shape_alpha)


class ViewProviderView:
    """ViewProvider of rendering view object"""

    def __init__(self, vobj):
        vobj.Proxy = self
        self.object = None

    def attach(self, vobj):  # pylint: disable=no-self-use
        """Code to be executed when object is created/restored (callback)"""
        self.object = vobj.Object

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def getDisplayModes(self, vobj):  # pylint: disable=no-self-use
        """Return a list of display modes (callback)"""
        return ["Default"]

    def getDefaultDisplayMode(self):  # pylint: disable=no-self-use
        """Return the name of the default display mode (callback).
        This display mode  must be defined in getDisplayModes.
        """
        return "Default"

    def setDisplayMode(self, mode):  # pylint: disable=no-self-use
        """Map the display mode defined in attach with those defined in
        getDisplayModes (callback).

        Since they have the same names nothing needs to be done. This method
        is optional
        """
        return mode

    def isShow(self):  # pylint: disable=no-self-use
        """Define the visibility of the object in the tree view (callback)"""
        return True

    def getIcon(self):  # pylint: disable=no-self-use
        """Return the icon which will appear in the tree view (callback)."""
        return os.path.join(WBDIR, "icons", "RenderViewTree.svg")


# ===========================================================================
#                            Renderer Handler
# ===========================================================================


class RendererHandler:
    """This class provides simplified access to external renderers modules.

    This class implements a simplified interface to external renderer module
    (façade design pattern).
    It requires a valid external renderer name for initialization, and
    provides:
    - a method to run the external renderer on a renderer-format file
    - a method to get a rendering string from an object's View, taking care of
      selecting the right method in renderer module according to
    view object's type.
    """
    def __init__(self, rdrname):
        self.renderer_name = str(rdrname)

        try:
            self.renderer_module = import_module("renderers." + rdrname)
        except ModuleNotFoundError:
            msg = translate(
                "Render",
                "[Render] Import Error: Renderer '%s' not found\n") % rdrname
            App.Console.PrintError(msg)
            raise

    def render(self, project, prefix, external, output, width, height):
        """Run the external renderer

        This method merely calls external renderer's 'render' method

        Params:
        - project:  the project to render
        - prefix:   a prefix string for call (will be inserted before path to
                    renderer)
        - external: a boolean indicating whether to call UI (true) or console
                    (false) version of renderer
        - width:    rendered image width, in pixels
        - height:   rendered image height, in pixels

        Return:     path to image file generated, or None if no image has been
                    issued by external renderer
        """
        return self.renderer_module.render(project,
                                           prefix,
                                           external,
                                           output,
                                           width,
                                           height)

    @staticmethod
    def is_renderable(obj):
        """Determine if an object is renderable

        This is a weak test: we just check if the object belongs to a
        class we would know how to handle - no further verification
        is made on the consistency of the object data against
        get_rendering_string requirements"""

        try:
            res = (obj.isDerivedFrom("Part::Feature") or
                   obj.isDerivedFrom("App::Link") or
                   obj.isDerivedFrom("Mesh::Feature") or
                   (obj.isDerivedFrom("App::FeaturePython") and
                    getproxyattr(obj, "type", "") in ["PointLight",
                                                      "Camera",
                                                      "AreaLight",
                                                      "SunskyLight",
                                                      "ImageLight"]))
        except AttributeError:
            res = False

        return res

    @staticmethod
    def is_project(obj):
        """Determine if an object is a rendering project

        This is a weak test: we just check if the object looks like
        something we could know how to handle - no further verification
        is made on the consistency of the object data against
        render requirements"""

        try:
            res = (obj.isDerivedFrom("App::FeaturePython") and
                   "Renderer" in obj.PropertiesList)
        except AttributeError:
            res = False

        return res

    def get_rendering_string(self, view):
        """Provide a rendering string for the view of an object

        This method selects the specialized rendering method adapted for
        'view', according to its source object type, and calls it.

        Parameters:
        view -- the view of the object to render

        Returns: a rendering string in the format of the external renderer
        for the supplied 'view'
        """

        try:
            source = view.Source

            objtype = getproxyattr(source, "type", "Object")

            name = str(source.Name)

            switcher = {
                "Object": RendererHandler._render_object,
                "PointLight": RendererHandler._render_pointlight,
                "Camera": RendererHandler._render_camera,
                "AreaLight": RendererHandler._render_arealight,
                "SunskyLight": RendererHandler._render_sunskylight,
                "ImageLight": RendererHandler._render_imagelight,
                }

            res = switcher[objtype](self, name, view)

        except (AttributeError, TypeError, AssertionError) as err:
            msg = translate(
                "Render",
                "[Render] Cannot render view '{0}': {1} (file {2}, "
                "line {3} in {4}). Skipping...\n")
            _, _, exc_traceback = sys.exc_info()
            framestack = traceback.extract_tb(exc_traceback)[-1]
            App.Console.PrintWarning(msg.format(
                getattr(view, "Label", "<No label>"),
                err,
                framestack.filename,
                framestack.lineno,
                framestack.name))
            return ""

        else:
            return res

    def _render_object(self, name, view):
        """Get a rendering string for a generic FreeCAD object

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...)

        Parameters:
        name -- the name of the object
        view -- a view of the object to render

        Returns: a rendering string, obtained from the renderer module
        """

        Renderable = collections.namedtuple("Renderable", "name mesh material")

        def get_renderables(obj, name, material):
            """Get the renderables from an object

            A renderable is a tuple (name, mesh, material). There can be
            several renderables for one object, for instance if the object is a
            compound of subobjects, so the result is a **list** of renderables.
            If this function does not know how to extract renderables from the
            given object, a TypeError is raised

            Parameters:
            obj -- the FreeCAD object from which to extract the renderables
            name -- the name of the object
            material -- the FreeCAD material associated with the object

            Notes about material:
            - the freecad material (material) may be a multimaterial
            - the subobjects may have their own materials, in which case the
              submaterials will override the material parameter

            Returns:
            A list of renderables
            """
            # TODO Apply scale in Links and PathArray
            # TODO material should be upper_material (the material from upper level) and we should have an upper_defaultcolor too
            # TODO Handle deflection
            # TODO Handle obj_is_applink and obj.ElementCount > 0
            # TODO Handle other Array types
            # TODO Test with 0.18
            meshfromshape = functools.partial(MeshPart.meshFromShape,
                                              LinearDeflection=0.1,
                                              AngularDeflection=0.523599,
                                              Relative=False)

            obj_is_group = hasattr(obj, "Group")
            obj_is_applink = obj.isDerivedFrom("App::Link")
            obj_is_partfeature = obj.isDerivedFrom("Part::Feature")
            obj_is_meshfeature = obj.isDerivedFrom("Mesh::Feature")
            obj_type = getproxyattr(obj, "Type", "")

            # Group
            if obj_is_group:
                debug("Object", label, "'Group' detected")
                shps = [o.Shape for o in Draft.getGroupContents(obj)
                        if hasattr(o, "Shape")]
                mesh = meshfromshape(Shape=Part.makeCompound(shps))
                renderables = [Renderable(name, mesh, material)]

            # Link (plain)
            elif obj_is_applink and not obj.ElementCount:
                debug("Object", label, "'Link (plain)' detected")
                base_rends = get_renderables(obj.LinkedObject, name, material)
                renderables = []
                link_plc_mat = obj.LinkPlacement.toMatrix()
                for rend in base_rends:
                    new_name = "%s_%s" % (name, rend.name)
                    new_mesh = rend.mesh.copy()
                    if not obj.LinkTransform:
                        new_mesh.transform(link_plc_mat)
                    new_rend = Renderable(new_name, new_mesh, rend.material)
                    renderables.append(new_rend)

            # Window
            elif obj_is_partfeature and obj_type == "Window":
                debug("Object", label, "'Window' detected")

                # Subobjects names
                subnames = obj.WindowParts[0::5]  # Names every 5th item...
                names = ("%s_%s" % (name, s) for s in subnames)

                # Subobjects meshes
                meshes = (meshfromshape(Shape=s)
                          for s in obj.Shape.childShapes())

                # Subobjects materials
                # 'material' should be a multimaterial or None
                if material is not None:
                    assert (material.isDerivedFrom("App::FeaturePython")
                            and material.Proxy.Type == "MultiMaterial"),\
                           "Not a multimaterial"
                    mats_dict = dict(zip(material.Names, material.Materials))
                    mats = (mats_dict[s] for s in subnames)
                else:
                    mats = [None] * len(subnames)

                # Build renderables
                renderables = \
                    [Renderable(*r) for r in zip(names, meshes, mats)]

            # Array, PathArray
            elif obj_is_partfeature and obj_type in ("Array", "PathArray"):
                debug("Object", label, "'%s' detected" % obj_type)
                material = (obj.Base.Material if obj.Base.Material is not None
                            else material)  # We may override view material...

                renderables = []
                if not obj.ExpandArray:
                    base_rends = get_renderables(obj.Base, obj.Base.Name, material)
                    base_plc = obj.Placement
                    placements = itertools.compress(obj.PlacementList, obj.VisibilityList)
                    for counter, plc in enumerate(placements):
                        # Apply placement to base renderables
                        for old_rend in base_rends:
                            mesh = old_rend.mesh.copy()
                            mesh.transform(plc.toMatrix())
                            mesh.transform(base_plc.toMatrix())
                            subname = "%s_%s_%s" % (name, old_rend.name, counter)
                            new_rend = Renderable(subname, mesh, old_rend.material)
                            renderables.append(new_rend)
                else:
                    base_plc = obj.Placement.toMatrix()
                    elements = itertools.compress(obj.ElementList, obj.VisibilityList)
                    for element in elements:
                        # element should be a App::LinkElement...
                        assert element.isDerivedFrom("App::LinkElement")
                        base_rends = get_renderables(element.LinkedObject, element.Name, material)
                        for old_rend in base_rends:
                            new_mesh = old_rend.mesh.copy()
                            new_mesh.transform(base_plc)
                            new_mesh.transform(element.Placement.toMatrix())
                            new_rend = Renderable(old_rend.name, new_mesh, old_rend.material)
                            renderables.append(new_rend)

            # Plain part
            elif obj_is_partfeature:
                debug("Object", label, "'Part::Feature' detected")
                mesh = meshfromshape(Shape=obj.Shape)
                renderables = [Renderable(name, mesh, material)]

            # Mesh
            elif obj_is_meshfeature:
                debug("Object", label, "'Mesh::Feature' detected")
                mesh = obj.Mesh
                renderables = [Renderable(name, mesh, material)]

            # Unhandled
            else:
                renderables = []
                msg = translate("Render", "Unhandled object type")
                raise TypeError(msg)

            return renderables

        def check_renderables(renderables):
            """Assert compliance of a list of renderables"""
            assert renderables,\
                translate("Render", "Nothing to render")
            for renderable in renderables:
                mesh = renderable.mesh
                assert mesh,\
                    translate("Render", "Cannot find mesh data")
                assert mesh.Topology[0] and mesh.Topology[1],\
                    translate("Render", "Mesh topology is empty")
                assert mesh.getPointNormals(),\
                    translate("Render", "Mesh topology has no normals")

        # Starts here
        source = view.Source
        label = getattr(source, "Label", name)
        debug("Object", label, "Processing")

        # Build renderables list from object
        # A renderable is a tuple (name, mesh, material)
        material = view.Proxy.get_freecad_material()
        renderables = get_renderables(source, name, material)

        # Check renderables
        check_renderables(renderables)

        # Call renderer on renderables, concatenate and return
        write_object = functools.partial(RendererHandler._call_renderer,
                                         self,
                                         "write_object")
        get_mat = functools.partial(materials.get_rendering_material,
                                    renderer=self.renderer_name,
                                    default_color=view.Proxy.get_shape_color())
        res = [write_object(r.name, r.mesh, get_mat(r.material))
               for r in renderables]
        return ''.join(res)

    def _render_camera(self, name, view):
        """Provide a rendering string for a camera.

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...)

        Parameters:
        name -- the name of the camera
        view -- a view of the camera to render

        Returns: a rendering string, obtained from the renderer module
        """
        source = view.Source
        a_ratio = float(source.AspectRatio)
        pos = App.Base.Placement(source.Placement)
        target = pos.Base.add(
            pos.Rotation.multVec(App.Vector(0, 0, -1)).multiply(a_ratio))
        updir = pos.Rotation.multVec(App.Vector(0, 1, 0))
        return self._call_renderer("write_camera",
                                   name,
                                   pos,
                                   updir,
                                   target)

    def _render_pointlight(self, name, view):
        """Gets a rendering string for a point light object

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...)

        Parameters:
        name -- the name of the point light
        view -- the view of the point light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """

        debug("PointLight", name, "Processing")

        source = view.Source

        # get location, color
        location = App.Base.Vector(source.Location)
        color = source.Color

        # we accept missing Power (default value: 60)...
        power = getattr(source, "Power", 60)

        # send everything to renderer module
        return self._call_renderer("write_pointlight",
                                   name,
                                   location,
                                   color,
                                   power)

    def _render_arealight(self, name, view):
        """Gets a rendering string for an area light object

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...)

        Parameters:
        name -- the name of the area light
        view -- the view of the area light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """

        debug("AreaLight", name, "Processing")

        # Get properties
        source = view.Source
        placement = App.Base.Placement(source.Placement)
        color = source.Color
        power = float(source.Power)
        size_u = float(source.SizeU)
        size_v = float(source.SizeV)

        # Send everything to renderer module
        return self._call_renderer("write_arealight",
                                   name,
                                   placement,
                                   size_u,
                                   size_v,
                                   color,
                                   power)

    def _render_sunskylight(self, name, view):
        """Gets a rendering string for a sunsky light object

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...)

        Parameters:
        name -- the name of the sunsky light
        view -- the view of the sunsky light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """
        debug("SunskyLight", name, "Processing")
        src = view.Source
        direction = App.Vector(src.SunDirection)
        turbidity = float(src.Turbidity)
        # Distance from the sun:
        distance = App.Units.parseQuantity("151000000 km").Value

        assert turbidity >= 0,\
            translate("Render", "Negative turbidity")

        assert direction.Length,\
            translate("Render", "Sun direction is null")

        return self._call_renderer("write_sunskylight",
                                   name,
                                   direction,
                                   distance,
                                   turbidity)

    def _render_imagelight(self, name, view):
        """Gets a rendering string for an image light object

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...)

        Parameters:
        name -- the name of the image light
        view -- the view of the image light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """
        debug("ImageLight", name, "Processing")
        src = view.Source
        image = src.ImageFile

        return self._call_renderer("write_imagelight",
                                   name,
                                   image)

    def _call_renderer(self, method, *args):
        """Calls a render method of the renderer module

        Parameters:
        -----------
        method: the method to call (as a string)
        args: the arguments to pass to the method

        Returns: a rendering string, obtained from the renderer module
        """
        renderer_method = getattr(self.renderer_module, method)
        return renderer_method(*args)


# ===========================================================================
#                               GUI Commands
# ===========================================================================


class RenderProjectCommand:
    """"Creates a rendering project.
    The renderer parameter must be a valid rendering module name
    """

    def __init__(self, renderer: str):
        # renderer must be a valid rendering module name (string)
        self.renderer = str(renderer)

    def GetResources(self):
        """Command's resources (callback)"""
        rdr = self.renderer
        return {
            "Pixmap": os.path.join(WBDIR, "icons", rdr + ".svg"),
            "MenuText": QT_TRANSLATE_NOOP("Render", "%s Project") % rdr,
            "ToolTip": QT_TRANSLATE_NOOP("Render", "Creates a %s "
                                                   "project") % rdr
            }

    def Activated(self):
        """Code to be executed when command is run (callback)
        Creates a new rendering project into active document
        """
        assert self.renderer, "Error: no renderer in command"

        # Get rendering template
        templates_folder = os.path.join(WBDIR, "templates")
        template_path = QFileDialog.getOpenFileName(
            Gui.getMainWindow(), "Select template", templates_folder, "*.*")
        template = template_path[0] if template_path else ""
        if not template:
            return

        # Create project
        Project.create(App.ActiveDocument, self.renderer, template)

        App.ActiveDocument.recompute()


class RenderViewCommand:
    """Creates a Raytracing view of the selected object(s) in the selected
    project or the default project
    """

    def GetResources(self):  # pylint: disable=no-self-use
        """Command's resources (callback)"""
        return {
            "Pixmap": os.path.join(WBDIR, "icons", "RenderView.svg"),
            "MenuText": QT_TRANSLATE_NOOP("Render", "Create View"),
            "ToolTip": QT_TRANSLATE_NOOP("Render",
                                         "Creates a Render view of the "
                                         "selected object(s) in the selected "
                                         "project or the default project")
            }

    def Activated(self):  # pylint: disable=no-self-use
        """Code to be executed when command is run (callback)"""

        # First, split selection into objects and projects
        selection = Gui.Selection.getSelection()
        objs, projs = [], []
        for item in selection:
            (projs if RendererHandler.is_project(item) else objs).append(item)

        # Then, get target project.
        # We first look among projects in the selection
        # and, if none, we fall back on active document's projects
        activedoc_projects = filter(RendererHandler.is_project,
                                    App.ActiveDocument.Objects)
        try:
            target_project = next(itertools.chain(projs, activedoc_projects))
        except StopIteration:
            msg = translate(
                "Render",
                "[Render] Unable to find a valid project in selection "
                "or document\n")
            App.Console.PrintError(msg)
            return

        # Finally, add objects to target project and recompute
        target_project.Proxy.add_views(objs)

        App.ActiveDocument.recompute()


class RenderCommand:
    """Render a selected Render project"""

    def GetResources(self):  # pylint: disable=no-self-use
        """Command's resources (callback)"""
        return {"Pixmap": os.path.join(WBDIR, "icons", "Render.svg"),
                "MenuText": QT_TRANSLATE_NOOP("Render", "Render"),
                "ToolTip": QT_TRANSLATE_NOOP("Render",
                                             "Performs the render of a "
                                             "selected project or the default "
                                             "project")}

    def Activated(self):  # pylint: disable=no-self-use
        """Code to be executed when command is run (callback)"""
        # Find project
        project = None
        sel = Gui.Selection.getSelection()
        for obj in sel:
            if "Renderer" in obj.PropertiesList:
                project = obj
                break
        if not project:
            for obj in App.ActiveDocument.Objects:
                if "Renderer" in obj.PropertiesList:
                    return

        # Render (and display if required)
        project.Proxy.render()


class CameraCommand:
    """Create a Camera object"""

    def GetResources(self):  # pylint: disable=no-self-use
        """Command's resources (callback)"""

        return {"Pixmap": ":/icons/camera-photo.svg",
                "MenuText": QT_TRANSLATE_NOOP("Render", "Create Camera"),
                "ToolTip": QT_TRANSLATE_NOOP("Render",
                                             "Creates a Camera object from "
                                             "the current camera position")}

    def Activated(self):  # pylint: disable=no-self-use
        """Code to be executed when command is run (callback)"""
        camera.Camera.create()


class PointLightCommand:
    """Create a Point Light object"""

    def GetResources(self):  # pylint: disable=no-self-use
        """Command's resources (callback)"""

        return {"Pixmap": os.path.join(WBDIR, "icons", "PointLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("Render", "Create Point Light"),
                "ToolTip": QT_TRANSLATE_NOOP("Render",
                                             "Creates a Point Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Code to be executed when command is run (callback)"""
        lights.PointLight.create()


class AreaLightCommand:
    """Create an Area Light object"""

    def GetResources(self):  # pylint: disable=no-self-use
        """Command's resources (callback)"""

        return {"Pixmap": os.path.join(WBDIR, "icons", "AreaLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("Render", "Create Area Light"),
                "ToolTip": QT_TRANSLATE_NOOP("Render",
                                             "Creates an Area Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Code to be executed when command is run (callback)"""
        lights.AreaLight.create()


class SunskyLightCommand:
    """Create an Sunsky Light object"""

    def GetResources(self):  # pylint: disable=no-self-use
        """Command's resources (callback)"""

        return {"Pixmap": os.path.join(WBDIR, "icons", "SunskyLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("Render", "Create Sunsky Light"),
                "ToolTip": QT_TRANSLATE_NOOP("Render",
                                             "Creates a Sunsky Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Code to be executed when command is run (callback)"""
        lights.SunskyLight.create()


class ImageLightCommand:
    """Create an Image Light object"""

    def GetResources(self):  # pylint: disable=no-self-use
        """Command's resources (callback)"""

        return {"Pixmap": os.path.join(WBDIR, "icons", "ImageLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("Render", "Create Image Light"),
                "ToolTip": QT_TRANSLATE_NOOP("Render",
                                             "Creates an Image Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Code to be executed when command is run (callback)"""
        lights.ImageLight.create()


# ===========================================================================
#                            Module initialization
# ===========================================================================


# If Gui is up, create the FreeCAD commands
if App.GuiUp:
    # Add commands
    RENDER_COMMANDS = []
    for rend in RENDERERS:
        if rend in DEPRECATED_RENDERERS:
            continue
        Gui.addCommand('Render_' + rend, RenderProjectCommand(rend))
        RENDER_COMMANDS.append('Render_' + rend)
    RENDER_COMMANDS.append("Separator")
    for cmd in (("Camera", CameraCommand()),
                ("PointLight", PointLightCommand()),
                ("AreaLight", AreaLightCommand()),
                ("SunskyLight", SunskyLightCommand()),
                ("ImageLight", ImageLightCommand()),):
        Gui.addCommand(*cmd)
        RENDER_COMMANDS.append(cmd[0])
    RENDER_COMMANDS.append("Separator")
    # pylint: disable=protected-access
    Gui.addCommand("Material", ArchMaterial._CommandArchMaterial())
    # pylint: enable=protected-access
    RENDER_COMMANDS.append("Material")
    RENDER_COMMANDS.append("Separator")
    for cmd in (("View", RenderViewCommand()),
                ("Render", RenderCommand())):
        Gui.addCommand(*cmd)
        RENDER_COMMANDS.append(cmd[0])

# vim: foldmethod=indent
