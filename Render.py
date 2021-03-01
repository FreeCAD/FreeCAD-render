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

On initialization, this module will retrieve all renderer modules and create
the necessary UI controls.
"""


# ===========================================================================
#                                   Imports
# ===========================================================================


import sys
import os
import re
import math
import itertools as it
from tempfile import mkstemp
from types import SimpleNamespace
from operator import attrgetter

from PySide.QtGui import (QAction, QIcon, QFileDialog, QLineEdit,
                          QDoubleValidator, QPushButton, QColorDialog, QPixmap,
                          QColor, QFormLayout, QComboBox, QLayout, QListWidget,
                          QListWidgetItem, QListView, QPlainTextEdit,
                          QMessageBox)
from PySide.QtCore import (QT_TRANSLATE_NOOP, QObject, SIGNAL, Qt, QLocale,
                           QSize)
import FreeCAD as App
import FreeCADGui as Gui
import Part
import ArchMaterial
try:
    import ImageGui
except ImportError:
    pass

from renderutils import translate, str2rgb, clamp
from rendererhandler import RendererHandler
import camera
import lights
import rendermaterials


# ===========================================================================
#                                 Constants
# ===========================================================================


# Paths to GUI resources
# This is for InitGui.py because it cannot import os
WBDIR = os.path.dirname(__file__)  # Workbench root directory
RDRDIR = os.path.join(WBDIR, "renderers")
ICONDIR = os.path.join(WBDIR, "icons")
TRANSDIR = os.path.join(WBDIR, "translations")
PREFPAGE = os.path.join(WBDIR, "ui", "RenderSettings.ui")
TASKPAGE = os.path.join(WBDIR, "ui", "RenderMaterial.ui")
# Renderers list
RENDERERS = {x.group(1)
             for x in map(lambda x: re.match(r"^([A-Z].*)\.py$", x),
                          os.listdir(RDRDIR))
             if x}
DEPRECATED_RENDERERS = {"Luxrender"}
VALID_RENDERERS = sorted(RENDERERS - DEPRECATED_RENDERERS)
FCDVERSION = App.Version()[0], App.Version()[1]  # FreeCAD version


# ===========================================================================
#                     Core rendering objects (Project and View)
# ===========================================================================


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
                    "Overweight transparency in rendering "
                    "(0=None (default), 10=Very high)."
                    "When this parameter is set, low transparency ratios will "
                    "be rendered more transparent. NB: This parameter affects "
                    "only implicit materials (generated via shape "
                    "Appearance), not explicit materials (defined via Material"
                    " parameter)."))
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
        result = ""
        doc = self.fpo.Document
        zpos = self.fpo.GroundPlaneZ
        color = self.fpo.GroundPlaneColor
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
            verts2d = ((bbox.XMin - margin, bbox.YMin - margin),
                       (bbox.XMax + margin, bbox.YMin - margin),
                       (bbox.XMax + margin, bbox.YMax + margin),
                       (bbox.XMin - margin, bbox.YMax + margin))
            vertices = [App.Vector(clamp(v[0]), clamp(v[1]), zpos)
                        for v in verts2d]
            vertices.append(vertices[0])  # Close the polyline...
            dummy1 = doc.addObject("Part::Feature", "dummygroundplane1")
            dummy1.Shape = Part.Face(Part.makePolygon(vertices))
            if App.GuiUp:
                dummy1.ViewObject.ShapeColor = color
            dummy2 = doc.addObject("App::FeaturePython", "dummygroundplane2")
            View(dummy2)
            dummy2.Source = dummy1

            result = renderer.get_rendering_string(dummy2)

            # Remove temp objects
            doc.removeObject(dummy2.Name)
            doc.removeObject(dummy1.Name)
            doc.recompute()

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
                        "'{}': unhandled object type") + '\n'
                    App.Console.PrintWarning(msg.format(obj.Label))

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

    def attach(self, vobj):  # pylint: disable=no-self-use
        """Respond to created/restored object event (callback)."""
        self.object = vobj.Object
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
        return os.path.join(WBDIR, "icons", "RenderProject.svg")

    def setupContextMenu(self, vobj, menu):  # pylint: disable=no-self-use
        """Set up the object's context menu in GUI (callback)."""
        icon = QIcon(os.path.join(WBDIR, "icons", "Render.svg"))
        action1 = QAction(icon, "Render", menu)
        QObject.connect(action1, SIGNAL("triggered()"), self.render)
        menu.addAction(action1)

    def claimChildren(self):  # pylint: disable=no-self-use
        """Deliver the children belonging to this object (callback)."""
        try:
            return self.object.Group
        except AttributeError:
            pass

    def render(self):
        """Render project.

        This method calls call proxy's 'render' method.
        """
        try:
            self.object.Proxy.render()
        except AttributeError as err:
            msg = translate("Render", "[Render] Cannot render: {}") + '\n'
            App.Console.PrintError(msg.format(err))


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
        self.object = None
        self._create_usematerialcolor(vobj)

    def attach(self, vobj):  # pylint: disable=no-self-use
        """Respond to created/restored object event (callback)."""
        self.object = vobj.Object
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
        return os.path.join(WBDIR, "icons", "RenderViewTree.svg")

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


# ===========================================================================
#                               GUI Commands
# ===========================================================================


class RenderProjectCommand:
    """GUI command to create a rendering project."""

    def __init__(self, renderer):
        """Initialize command.

        Args:
            renderer (str) -- a rendering module name
        """
        # renderer must be a valid rendering module name (string)
        self.renderer = str(renderer)

    def GetResources(self):
        """Get command's resources (callback)."""
        rdr = self.renderer
        return {
            "Pixmap": os.path.join(WBDIR, "icons", rdr + ".svg"),
            "MenuText": QT_TRANSLATE_NOOP("RenderProjectCommand",
                                          "%s Project") % rdr,
            "ToolTip": QT_TRANSLATE_NOOP("RenderProjectCommand",
                                         "Create a %s project") % rdr
            }

    def Activated(self):
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
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
    """GUI command to create a rendering view of an object in a project.

    The command operates on the selected object(s) and the selected project,
    or the default project.
    """

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {
            "Pixmap": os.path.join(WBDIR, "icons", "RenderView.svg"),
            "MenuText": QT_TRANSLATE_NOOP("RenderViewCommand",
                                          "Rendering View"),
            "ToolTip": QT_TRANSLATE_NOOP("RenderViewCommand",
                                         "Create a Rendering View of the "
                                         "selected object(s) in the selected "
                                         "project or the default project")
            }

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
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
            target_project = next(it.chain(projs, activedoc_projects))
        except StopIteration:
            msg = translate(
                "Render",
                "[Render] Unable to find a valid project in selection "
                "or document") + '\n'
            App.Console.PrintError(msg)
            return

        # Finally, add objects to target project and recompute
        target_project.Proxy.add_views(objs)

        App.ActiveDocument.recompute()


class RenderCommand:
    """GUI command to render a selected Render project."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(WBDIR, "icons", "Render.svg"),
                "MenuText": QT_TRANSLATE_NOOP("RenderCommand", "Render"),
                "ToolTip": QT_TRANSLATE_NOOP("RenderCommand",
                                             "Perform the rendering of a "
                                             "selected project or the default "
                                             "project")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
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
    """GUI command to create a Camera object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": ":/icons/camera-photo.svg",
                "MenuText": QT_TRANSLATE_NOOP("CameraCommand",
                                              "Camera"),
                "ToolTip": QT_TRANSLATE_NOOP("CameraCommand",
                                             "Create a Camera object from "
                                             "the current camera position")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        camera.Camera.create()


class PointLightCommand:
    """GUI command to create a Point Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(WBDIR, "icons", "PointLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("PointLightCommand",
                                              "Point Light"),
                "ToolTip": QT_TRANSLATE_NOOP("PointLightCommand",
                                             "Create a Point Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        lights.PointLight.create()


class AreaLightCommand:
    """GUI command to create an Area Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(WBDIR, "icons", "AreaLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("AreaLightCommand",
                                              "Area Light"),
                "ToolTip": QT_TRANSLATE_NOOP("AreaLightCommand",
                                             "Create an Area Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        lights.AreaLight.create()


class SunskyLightCommand:
    """GUI command to create an Sunsky Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(WBDIR, "icons", "SunskyLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("SunskyLightCommand",
                                              "Sunsky Light"),
                "ToolTip": QT_TRANSLATE_NOOP("SunskyLightCommand",
                                             "Create a Sunsky Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        lights.SunskyLight.create()


class ImageLightCommand:
    """GUI command to create an Image Light object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(WBDIR, "icons", "ImageLight.svg"),
                "MenuText": QT_TRANSLATE_NOOP("ImageLightCommand",
                                              "Image Light"),
                "ToolTip": QT_TRANSLATE_NOOP("ImageLightCommand",
                                             "Create an Image Light object")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        lights.ImageLight.create()


class MaterialSettingsCommand:
    """GUI command to set render settings of a material object."""

    def GetResources(self):  # pylint: disable=no-self-use
        """Get command's resources (callback)."""
        return {"Pixmap": os.path.join(WBDIR, "icons", "MaterialSettings.svg"),
                "MenuText": QT_TRANSLATE_NOOP("MaterialSettingsCommand",
                                              "Material Render Settings"),
                "ToolTip": QT_TRANSLATE_NOOP("MaterialSettingsCommand",
                                             "Set rendering parameters of "
                                             "the selected Material")}

    def Activated(self):  # pylint: disable=no-self-use
        """Respond to Activated event (callback).

        This code is executed when the command is run in FreeCAD.
        It creates a new rendering project into the active document.
        """
        # App.setActiveTransaction("MaterialSettings")
        App.ActiveDocument.openTransaction("MaterialSettings")
        task = MaterialSettingsTaskPanel()
        Gui.Control.showDialog(task)
        # App.closeActiveTransaction()
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()


class ColorPicker(QPushButton):
    """A color picker widget.

    This widget provides a button, with a colored square icon, which triggers
    a color dialog when it is pressed.
    """

    def __init__(self, color=QColor(127, 127, 127)):
        """Initialize ColorPicker.

        Args:
            color -- The default color of the picker
        """
        super().__init__()
        self.color = QColor(color)
        self._set_icon(self.color)
        QObject.connect(self, SIGNAL("clicked()"), self.on_button_clicked)

    def on_button_clicked(self):
        """Respond to button clicked event (callback)."""
        color = QColorDialog.getColor(initial=self.color)
        if color.isValid():
            self.color = color
            self._set_icon(color)

    def _set_icon(self, color):
        """Set the colored square icon."""
        colorpix = QPixmap(16, 16)
        colorpix.fill(color)
        self.setIcon(QIcon(colorpix))

    def set_color(self, color):
        """Set widget color value."""
        self.color = QColor(color)
        self._set_icon(self.color)

    def get_color_text(self):
        """Get widget color value, in text format."""
        color = self.color
        return "({},{},{})".format(color.redF(), color.greenF(), color.blueF())


class MaterialSettingsTaskPanel():
    """Task panel to edit Material render settings."""

    NONE_MATERIAL_TYPE = QT_TRANSLATE_NOOP("MaterialSettingsTaskPanel",
                                           "<None>")

    def __init__(self, obj=None):
        """Initialize task panel."""
        self.form = Gui.PySideUic.loadUi(TASKPAGE)
        self.tabs = self.form.RenderTabs
        self.tabs.setCurrentIndex(0)
        self.layout = self.tabs.findChild(QFormLayout, "FieldsLayout")
        self.material_type_combo = \
            self.form.findChild(QComboBox, "MaterialType")

        # Initialize material name combo
        self.material_combo = self.form.MaterialNameLayout.itemAt(0).widget()
        self.existing_materials = {obj.Label: obj
                                   for obj in App.ActiveDocument.Objects
                                   if rendermaterials.is_valid_material(obj)}
        self.material_combo.addItems(list(self.existing_materials.keys()))
        self.material_combo.currentTextChanged.connect(
            self.on_material_name_changed)

        # Initialize material type combo
        # Note: itemAt(0) is label, itemAt(1) is combo
        self.material_type_combo = \
            self.form.findChild(QComboBox, "MaterialType")
        material_type_set = [MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE] \
            + list(rendermaterials.STD_MATERIALS)
        self.material_type_combo.addItems(material_type_set)
        self.material_type_combo.currentTextChanged.connect(
            self.on_material_type_changed)
        self._set_layout_visible("FieldsLayout", False)
        self.fields = []

        # Initialize Father layout
        self._set_layout_visible("FatherLayout", False)
        self.father_field = self.form.FatherLayout.itemAt(1).widget()

        # Initialize Passthru Renderers selector
        rdrwidget = self.form.findChild(QListWidget, "Renderers")
        for rdr in VALID_RENDERERS:
            item = QListWidgetItem()
            item.setText(rdr)
            item.setIcon(QIcon(os.path.join(WBDIR, "icons", "%s.svg" % rdr)))
            rdrwidget.addItem(item)
        rdrwidget.setViewMode(QListView.IconMode)
        rdrwidget.setIconSize(QSize(48, 48))
        rdrwidget.setMaximumWidth(96)
        rdrwidget.setSpacing(6)
        rdrwidget.setMovement(QListView.Static)
        rdrwidget.currentTextChanged.connect(
            self.on_passthrough_renderer_changed)
        self.passthru_rdr = rdrwidget
        self.passthru = self.form.findChild(QPlainTextEdit, "PassthroughEdit")
        self.passthru.textChanged.connect(self.on_passthrough_text_changed)
        self.passthru_cache = {}
        self._set_layout_visible("PassthruLayout", False)

        # Get selected material and initialize material type combo with it
        selection = {obj.Label for obj in Gui.Selection.getSelection()}
        selected_materials = selection & self.existing_materials.keys()
        try:
            selected_material = selected_materials.pop()
        except KeyError:
            pass
        else:
            self.material_combo.setCurrentText(selected_material)

    def on_material_name_changed(self, material_name):
        """Respond to material name changed event."""
        # Clear passthrough cache
        self.passthru_cache = {}

        # Find material
        try:
            material = self.existing_materials[material_name]
        except KeyError:
            # Unknown material: disable everything
            self._set_layout_visible("FieldsLayout", False)
            self._set_layout_visible("FatherLayout", False)
            self._set_layout_visible("PassthruLayout", False)
            return

        # Retrieve material type
        self._set_layout_visible("FieldsLayout", True)
        material_type_combo = self.form.findChild(QComboBox, "MaterialType")
        try:
            material_type = material.Material["Render.Type"]
        except KeyError:
            material_type_combo.setCurrentIndex(0)
        else:
            if not material_type:
                material_type = MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE
            material_type_combo.setCurrentText(material_type)

        # Retrieve passthrough
        self._set_layout_visible("PassthruLayout", True)
        try:
            renderer = self.passthru_rdr.currentItem().text()
        except AttributeError:
            renderer = None
        self._populate_passthru(renderer, material)

        # Retrieve material father
        self._set_layout_visible("FatherLayout", True)
        try:
            father = material.Material["Father"]
        except KeyError:
            father = ""
        finally:
            self.father_field.setText(father)

    def on_material_type_changed(self, material_type):
        """Respond to material type changed event."""
        # Get parameters list
        try:
            params = rendermaterials.STD_MATERIALS_PARAMETERS[material_type]
        except KeyError:
            self._delete_fields()
        else:
            self._delete_fields()
            mat_name = self.material_combo.currentText()
            for param in params:
                value = self.existing_materials[mat_name].Material.get(
                    "Render.{}.{}".format(material_type, param.name))
                self._add_field(param, value)

    def on_passthrough_renderer_changed(self, renderer):
        """Respond to passthrough renderer changed event."""
        mat_name = self.material_combo.currentText()
        material = self.existing_materials[mat_name]
        self._populate_passthru(renderer, material)

    def on_passthrough_text_changed(self):
        """Respond to passthrough renderer changed event."""
        rdr = self.passthru_rdr.currentItem()
        if not rdr:
            return
        text = self.passthru.toPlainText()
        self.passthru_cache[rdr.text()] = text

    PASSTHROUGH_KEYS = {r: rendermaterials.passthrough_keys(r)
                        for r in VALID_RENDERERS}

    def _populate_passthru(self, renderer, material):
        """Populate passthrough edit field."""
        # If no renderer or no material provided, disable field and quit
        if not renderer or not material:
            self.passthru.setPlainText("")
            self.passthru.setEnabled(False)
            return

        self.passthru.setEnabled(True)

        # If renderer passthrough is already in cache (and possibly modified),
        # use the cache; otherwise, retrieve it from 'material'.
        try:
            text = self.passthru_cache[renderer]
        except KeyError:
            keys = self.PASSTHROUGH_KEYS[renderer]
            common_keys = keys & material.Material.keys()
            lines = [material.Material[k] for k in sorted(common_keys)]
            text = '\n'.join(lines)

        self.passthru.setPlainText(text)

    def _set_layout_visible(self, layout_name, flag):
        """Make a layout visible/invisible, according to flag."""
        layout = self.form.findChild(QLayout, layout_name)
        for index in range(layout.count()):
            item = layout.itemAt(index)
            item.widget().setVisible(flag)

    def _add_field(self, param, value):
        """Add a field to the task panel."""
        name = param.name
        if param.type == "float":
            widget = QLineEdit()
            widget.setAlignment(Qt.AlignRight)
            widget.setValidator(QDoubleValidator())
            try:
                value = QLocale().toString(float(value))
            except (ValueError, TypeError):
                value = None
            widget.setText(value)
            self.fields.append(
                (name, lambda: QLocale().toDouble(widget.text())[0]))
        elif param.type == "RGB":
            if value:
                qcolor = QColor.fromRgbF(*str2rgb(value))
                widget = ColorPicker(qcolor)
            else:
                widget = ColorPicker()
            self.fields.append((name, widget.get_color_text))
        else:
            widget = QLineEdit()
            self.fields.append((name, widget.text))
        widget.setToolTip(param.desc)
        layout = self.form.findChild(QLayout, "FieldsLayout")
        layout.addRow("%s:" % param.name, widget)

    def _delete_fields(self):
        """Delete all fields, except the first one (MaterialType selector)."""
        layout = self.form.findChild(QLayout, "FieldsLayout")
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget.objectName() not in ("MaterialType",
                                           "MaterialTypeLabel"):
                widget.setParent(None)
        self.fields = []

    def _write_fields(self):
        """Write task panel fields to FreeCAD material."""
        # Find material
        mat_name = self.material_combo.currentText()
        try:
            material = self.existing_materials[mat_name]
        except KeyError:
            return
        tmp_mat = material.Material.copy()

        # Set render type and associated fields
        if self.material_type_combo.currentIndex():
            render_type = self.material_type_combo.currentText()
            if render_type == MaterialSettingsTaskPanel.NONE_MATERIAL_TYPE:
                render_type = ""
            tmp_mat["Render.Type"] = str(render_type)

            # Set fields
            for field in self.fields:
                field_name, get_value = field
                param_name = "Render.{}.{}".format(render_type, field_name)
                tmp_mat[param_name] = str(get_value())

        # Set passthru
        pthr_keys = self.PASSTHROUGH_KEYS
        for rdr, text in self.passthru_cache.items():
            lines = dict(zip(sorted(pthr_keys[rdr]), text.splitlines()))
            tmp_mat.update(lines)

        # Set father
        father = self.father_field.text()
        if father:
            tmp_mat["Father"] = str(father)

        # Write to material
        material.Material = tmp_mat

    def accept(self):
        """Respond to user acceptation (OK button).

        Write all task panel fields to material
        """
        self._write_fields()
        Gui.ActiveDocument.resetEdit()
        Gui.Control.closeDialog()
        App.ActiveDocument.recompute()
        return True


# ===========================================================================
#                            Commands initialization
# ===========================================================================


class CommandGroup:
    """Group of commands for GUI (toolbar, menu...)."""
    def __init__(self, cmdlist, menu, tooltip=None):
        """Initialize group of commands."""
        self.cmdlist = cmdlist
        self.menu = menu
        self.tooltip = tooltip if tooltip is not None else menu

    def GetCommands(self):
        """Get command group's commands (callback)."""
        return tuple("Render_%s" % name for name, _ in self.cmdlist)

    def GetResources(self):
        """Get command group's resources (callback)."""
        return {'MenuText': self.menu, 'ToolTip': self.tooltip}


# pylint: disable=protected-access
MaterialCommand = ArchMaterial._CommandArchMaterial
# pylint: enable=protected-access


def _init_gui_commands():
    """Initialize GUI commands for Render Workbench.

    Initialization will happen only if Gui is up.
    Please note this function has side-effects, as it calls Gui.addCommand

    Returns:
        List of commands initialized ([] if Gui is down)
    """
    def add_command(name, action):
        """Add a command to GUI (helper).

        The command name is decorated before being added.

        Params:
            name -- Name of the command to add
            action -- Action of the command to add
        """
        decorated_name = "Render_%s" % name
        Gui.addCommand(decorated_name, action)
        return decorated_name

    if not App.GuiUp:
        return []

    separator = ("Separator", None)

    projects_cmd = [(r, RenderProjectCommand(r)) for r in VALID_RENDERERS]
    projects_group = CommandGroup(projects_cmd,
                                  "Projects",
                                  "Create a Rendering Project")

    lights_cmd = [("PointLight", PointLightCommand()),
                  ("AreaLight", AreaLightCommand()),
                  ("SunskyLight", SunskyLightCommand()),
                  ("ImageLight", ImageLightCommand())]
    lights_group = CommandGroup(lights_cmd, "Lights", "Create a Light")

    materials = [("Material", MaterialCommand()),
                 ("MaterialRenderSettings", MaterialSettingsCommand())]
    materials_group = CommandGroup(materials, "Materials", "Manage Materials")

    render_commands = [("Projects", projects_group),
                       separator,
                       ("Camera", CameraCommand()),
                       ("Lights", lights_group),
                       ("View", RenderViewCommand()),
                       ("Materials", materials_group),
                       separator,
                       ("Render", RenderCommand())]

    result = []

    for cmdname, cmdobj in render_commands:
        if cmdobj:
            try:
                grpcmd = cmdobj.cmdlist  # Command group
            except AttributeError:
                pass
            else:
                for cmd in grpcmd:
                    add_command(*cmd)
            fullname = add_command(cmdname, cmdobj)  # Normal command
            result.append(fullname)
        else:
            result.append(cmdname)  # Separator

    return result


# If Gui is up, create the FreeCAD commands
RENDER_COMMANDS = _init_gui_commands()
