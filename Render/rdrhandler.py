# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020-2022 Howetuft <howetuft@gmail.com>                 *
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

"""This module implements RendererHandler class.

RendererHandler is a simplified and unified accessor to renderers plugins.

Among important things, RendererHandler:
- allows to get a rendering string for a given object
- allows to run a renderer onto a scene

Caveat about units:
1. Please note that RendererHandler converts distance units from FreeCAD
internals (millimeters) to standard (meters) before sending objects to
renderers, as usual renderers expects meters as base unit.
2. FreeCAD internal colors are in srgb colorspace, whereas renderers expect
input colors in linear colorspace. A conversion is made.
"""


# ===========================================================================
#                                   Imports
# ===========================================================================

import sys
import functools
import traceback
import enum
from importlib import import_module
from types import SimpleNamespace
import time

import FreeCAD as App
import MeshPart
import Mesh

import Render.rendermesh
from Render.utils import translate, debug, message, getproxyattr, RGB
from Render.constants import PARAMS
from Render import renderables
from Render import rendermaterial


# ===========================================================================
#                                  Constants
# ===========================================================================

# Scale from FreeCAD internal distance unit (mm) to renderers ones (m)
SCALE = 0.001


@enum.unique
class RenderingTypes(enum.IntEnum):
    """Enumeration of handled rendering types."""

    OBJECT = 0
    CAMERA = 1
    POINTLIGHT = 2
    AREALIGHT = 3
    SUNSKYLIGHT = 4
    IMAGELIGHT = 5
    DISTANTLIGHT = 6


# ===========================================================================
#                            Renderer Handler
# ===========================================================================


class RendererHandler:
    """This class provides simplified access to external renderers modules.

    This class implements a façade design pattern to renderers plugins.
    It requires a valid external renderer name for initialization, and
    provides:
    - a method to run the external renderer on a renderer-format file
    - a method to get a rendering string from an object's View, taking care of
      selecting the right method in renderer module according to
    view object's type.

    Important: FreeCAD internal colors are in srgb colorspace, whereas
    renderers expect input colors in linear colorspace. A conversion is
    necessary.
    """

    def __init__(self, rdrname, **kwargs):
        """Initialize RendererHandler class.

        Args:
            rdrname -- renderer name (str). Must match a renderer plugin name.

        Keyword args:
            linear_deflection -- linear deflection (float) to be passed to
                mesher
            angular_deflection -- angular deflection (float) to be passed to
                mesher.
            transparency_boost -- an integer to augment transparency in
                implicit material computation
            project_directory -- the directory where the project is to be
                exported
            object_directory -- the directory where the objects are to be
                exported
            skip_meshing -- a flag to skip the meshing step
        """
        self.renderer_name = str(rdrname)
        self.linear_deflection = float(kwargs.get("linear_deflection", 0.1))
        self.angular_deflection = float(
            kwargs.get("angular_deflection", 0.524)
        )
        self.transparency_boost = float(kwargs.get("transparency_boost", 0))
        self.project_directory = kwargs.get("project_directory")
        self.object_directory = kwargs.get("object_directory")
        self.skip_meshing = bool(kwargs.get("skip_meshing", False))

        try:
            module_name = f"Render.renderers.{rdrname}"
            self.renderer_module = import_module(module_name)
        except ModuleNotFoundError:
            raise RendererNotFoundError(rdrname) from None

        self.switcher = {
            RenderingTypes.OBJECT: RendererHandler._render_object,
            RenderingTypes.CAMERA: RendererHandler._render_camera,
            RenderingTypes.POINTLIGHT: RendererHandler._render_pointlight,
            RenderingTypes.AREALIGHT: RendererHandler._render_arealight,
            RenderingTypes.SUNSKYLIGHT: RendererHandler._render_sunskylight,
            RenderingTypes.IMAGELIGHT: RendererHandler._render_imagelight,
            RenderingTypes.DISTANTLIGHT: RendererHandler._render_distantlight,
        }

    def test_cmdline(self, cli):
        """Get a test command line.

        This method is used in settings to test the correctness of the path
        provided.

        Args:
            cli -- if True, test the command-line flavour of the renderer
        """
        return self.renderer_module.test_cmdline(cli)

    def render(
        self,
        project,
        prefix,
        batch,
        input_file,
        output_file,
        width,
        height,
        spp,
        denoise,
    ):
        """Run the external renderer.

        This method merely calls external renderer's 'render' method, after
        having cleared rendermaterial's cache.

        Params:
        - project:     the project to render
        - prefix:      a prefix string for call (will be inserted before path
                       to renderer)
        - batch:       a boolean indicating whether to call console batch
                       (True) or UI interactive (False) version of renderer
        - input_file:  path to input file
        - output_file: path to output file
        - width:       rendered image width, in pixels
        - height:      rendered image height, in pixels
        - spp:         samples per pixel

        Return:     path to image file generated, or None if no image has been
                    issued by external renderer
        """
        rendermaterial.clear_cache()  # Clear rendermaterial's cache
        return self.renderer_module.render(
            project,
            prefix,
            batch,
            input_file,
            output_file,
            width,
            height,
            spp,
            denoise,
        )

    @staticmethod
    def is_renderable(obj):
        """Determine if an object is renderable.

        This is a weak test: we just check if the object belongs to a
        class we would know how to handle - no further verification
        is made on the consistency of the object data against
        get_rendering_string requirements.
        """
        try:
            res = (
                obj.isDerivedFrom("Part::Feature")
                or obj.isDerivedFrom("App::Link")
                or obj.isDerivedFrom("App::Part")
                or obj.isDerivedFrom("Mesh::Feature")
                or obj.isDerivedFrom("App::LinkGroup")
                or (
                    obj.isDerivedFrom("App::FeaturePython")
                    and getproxyattr(obj, "type", "")
                    in [
                        "PointLight",
                        "Camera",
                        "AreaLight",
                        "SunskyLight",
                        "ImageLight",
                        "DistantLight",
                    ]
                )
                or (
                    obj.isDerivedFrom("App::GeometryPython")
                    and getproxyattr(obj, "type", "")
                    in [
                        "PointLight",
                        "Camera",
                        "AreaLight",
                        "SunskyLight",
                        "ImageLight",
                    ]
                )
            )
        except AttributeError:
            res = False

        return res

    @staticmethod
    def clean():
        """Clean workspace after getting strings."""
        renderables.clean_a2p()

    @staticmethod
    def is_project(obj):
        """Determine if an object is a rendering project.

        This is a weak test: we just check if the object looks like
        something we could know how to handle - no further verification
        is made on the consistency of the object data against
        render requirements.
        """
        try:
            res = (
                obj.isDerivedFrom("App::FeaturePython")
                and "Renderer" in obj.PropertiesList
            )
        except AttributeError:
            res = False

        return res

    def get_template_file_filter(self):
        """Get file filter for templates of the renderer.

        Args:
            rdr -- renderer name (str)

        Returns:
            A string containing a file filter for renderer's templates.
        """
        return str(getattr(self.renderer_module, "TEMPLATE_FILTER", ""))

    def _get_renderer_specifics(self, view):
        """Get specific parameters of the renderer for a given view."""
        rdrname = self.renderer_name

        # Source properties
        src = view.Source
        try:
            properties = src.PropertiesList
        except AttributeError:
            res = {}
        else:
            res = {
                p[len(rdrname) :]: src.getPropertyByName(p)
                for p in properties
                if p.startswith(rdrname)
            }

        # View properties
        try:
            properties = view.PropertiesList
        except AttributeError:
            pass
        else:
            res.update(
                {
                    p[len(rdrname) :]: view.getPropertyByName(p)
                    for p in properties
                    if p.startswith(rdrname)
                }
            )
        return res

    def _get_general_data(self):
        """Get general data for keyword arguments."""
        return {
            "project_directory": self.project_directory,
            "object_directory": self.object_directory,
        }

    def get_rendering_string(self, view):
        """Provide a rendering string for the view of an object.

        This method selects the specialized rendering method adapted for
        'view', according to its source object type, and calls it.

        Parameters:
        view -- the view of the object to render

        Returns: a rendering string in the format of the external renderer
        for the supplied 'view'
        """
        # Alias parameters
        source = view.Source
        name = str(source.FullName)
        msg = translate("Render", "Exporting")

        # Render Workbench objects
        try:
            # If this is a renderable object of Render WB, it appoints a
            # rendering method
            rendering_type = view.Source.Proxy.RENDERING_TYPE
            rendering_type = RenderingTypes(rendering_type)
            method = self.switcher[rendering_type]
        except AttributeError:
            pass
        else:
            message("Objstrings", name, msg)
            return method(self, name, view)

        # ArchTexture PointLight (or everything that looks like)
        try:
            # Duck typing
            source.getPropertyByName("Location")
            source.getPropertyByName("Color")
            source.getPropertyByName("Power")
            # And type-checking...
            if source.Proxy.type != "PointLight":
                raise TypeError
        except (AttributeError, TypeError):
            pass
        else:
            message("Objstrings", name, msg)
            return RendererHandler._render_pointlight(self, name, view)

        # Fallback/default: render it as an 'object'
        message("Objstrings", name, msg)
        return RendererHandler._render_object(self, name, view)

    def get_camsource_string(self, camsource, project):
        """Get a rendering string from a camera in 'view.Source' format."""
        return self._render_camera(
            "Default_Camera",
            SimpleNamespace(Source=camsource, InListRecursive=[project]),
        )

    def _render_object(self, name, view):
        """Get a rendering string for a generic FreeCAD object.

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...).

        Parameters:
        name -- the name of the object
        view -- a view of the object to render

        Returns: a rendering string, obtained from the renderer module
        """
        autosmooth = getattr(view, "AutoSmooth", False)
        try:
            autosmooth_angle = float(view.AutoSmoothAngle.getValueAs("rad"))
        except AttributeError:
            autosmooth_angle = 0

        # Mesher
        def mesher(
            shape,
            compute_uvmap=True,
            uvmap_projection=None,
            is_already_a_mesh=False,
            name=None,
            label=None,
        ):
            """Mesh a shape.

            Args:
                compute_uvmap -- Determine if an uv map must be computed (bool)
                uvmap_projection -- Type of uv map to compute (string, see View
                    object and RenderMesh)
                is_already_a_mesh  -- Flag to indicate the shape is actually
                    already a mesh, so no meshing should be applied

            Returns a RenderMesh.
            """
            debug_flag = PARAMS.GetBool("Debug")
            name = name or view.Source.FullName
            label = label or view.Source.Label
            fullname = f"'{label}' ('{name}')"

            # Skip meshing?
            if self.skip_meshing:
                # We just need placement, and an empty mesh
                debug("Object", fullname, "Skip meshing")
                mesh = Mesh.Mesh()
                mesh.Placement = shape.Placement
                rendermesh = Render.rendermesh.create_rendermesh(
                    mesh,
                    project_directory=self.project_directory,
                    export_directory=self.object_directory,
                    relative_path=True,
                    skip_meshing=self.skip_meshing,
                    name=fullname,
                )
                return rendermesh

            # Log
            debug("Object", fullname, "Begin meshing")
            tm0 = time.time()

            # Standard case
            if is_already_a_mesh:
                mesh = shape.Mesh.copy()
            else:
                # Generate mesh
                # Nota: the shape placement is stored in the mesh placement...
                shape = shape.copy()
                shape_plc = shape.Placement
                shape.Placement = App.Base.Placement()
                if FCDVERSION >= (0, 22):
                    print("Release GIL")  # TODO
                    mesh = MeshPart.meshFromShape(
                        Shape=shape,
                        LinearDeflection=self.linear_deflection,
                        AngularDeflection=self.angular_deflection,
                        Relative=False,
                        ReleaseGIL=True,
                    )
                else:
                    mesh = MeshPart.meshFromShape(
                        Shape=shape,
                        LinearDeflection=self.linear_deflection,
                        AngularDeflection=self.angular_deflection,
                        Relative=False,
                    )

                mesh.Placement = shape_plc

            mesh = Render.rendermesh.create_rendermesh(
                mesh,
                autosmooth,
                autosmooth_angle,
                compute_uvmap,
                uvmap_projection,
                project_directory=self.project_directory,
                export_directory=self.object_directory,
                relative_path=True,
                skip_meshing=self.skip_meshing,
                name=fullname,
            )

            duration = time.time() - tm0
            msg = f"End meshing ({duration}s)"
            debug("Object", fullname, msg)
            if debug_flag:
                print(msg + "\n")

            return mesh
            # End mesher

        source = view.Source
        label = getattr(source, "Label", name)
        uvproj = getattr(view, "UvProjection", None)
        specifics = self._get_renderer_specifics(view)
        general_data = self._get_general_data()
        kwargs = {}
        kwargs.update(specifics)
        kwargs.update(general_data)
        debug("Object", label, "Processing")

        # Build a list of renderables from the object
        material = view.Material
        tpboost = self.transparency_boost
        try:
            rends = renderables.get_renderables(
                source,
                name,
                material,
                mesher,
                transparency_boost=tpboost,
                uvprojection=uvproj,
            )
            renderables.check_renderables(rends)
        except renderables.RenderableError as err:
            # 'get_renderables' will raise RenderableError if unable to render
            # In this case, we pass with a warning
            msg = (
                translate(
                    "Render",
                    "[Render] Cannot render view '{0}': {1} (file {2}, "
                    "line {3} in {4}). Skipping...",
                )
                + "\n"
            )
            _, _, exc_traceback = sys.exc_info()
            framestack = traceback.extract_tb(exc_traceback)[-1]
            App.Console.PrintWarning(
                msg.format(
                    getattr(view, "Label", "<No label>"),
                    err,
                    framestack.filename,
                    framestack.lineno,
                    framestack.name,
                )
            )
            return ""

        # Rescale to meters
        for rend in rends:
            rend.mesh.transformation.scale = SCALE

        # Call renderer on renderables, concatenate and return
        write_mesh = functools.partial(
            RendererHandler._call_renderer,
            self,
            "write_mesh",
            **kwargs,
        )

        get_mat = rendermaterial.get_rendering_material
        rdrname = self.renderer_name

        res = []
        for renderable in rends:
            material = get_mat(
                renderable.name,
                renderable.material,
                rdrname,
                renderable.defcolor,
            )
            try:
                objstring = write_mesh(
                    renderable.name,
                    renderable.mesh,
                    material,
                )
            except Render.rendermesh.SkipMeshingError as err:
                msg = (
                    f"[Render][Objstring] '{label}': File not found "
                    f"while attempting to reuse meshing ('{err.filename}').\n"
                )
                App.Console.PrintWarning(msg)
            else:
                res.append(objstring)

        return "".join(res)

    def _render_camera(self, name, view):
        """Provide a rendering string for a camera.

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...).

        Parameters:
        name -- the name of the camera
        view -- a view of the camera to render

        Returns: a rendering string, obtained from the renderer module
        """
        source = view.Source
        pos = App.Base.Placement(source.Placement)
        target = pos.Base.add(pos.Rotation.multVec(App.Vector(0, 0, -1)))
        updir = pos.Rotation.multVec(App.Vector(0, 1, 0))
        field_of_view = float(getattr(source, "HeightAngle", 60))
        specifics = self._get_renderer_specifics(view)
        general_data = self._get_general_data()
        kwargs = {}
        kwargs.update(specifics)
        kwargs.update(general_data)

        # Find rendering dimensions
        try:
            resolution = next(
                (p.RenderWidth, p.RenderHeight)
                for p in view.InListRecursive
                if hasattr(p, "RenderWidth") and hasattr(p, "RenderHeight")
            )
        except StopIteration as exc:
            # No corresponding project? Error...
            msg = (
                f"Cannot export camera '{name}': missing project data "
                "(rendering dimensions)"
            )
            raise RuntimeError(msg) from exc

        # Rescale
        pos.Base.multiply(SCALE)
        target.multiply(SCALE)
        updir.multiply(SCALE)

        return self._call_renderer(
            "write_camera",
            name,
            pos,
            updir,
            target,
            field_of_view,
            resolution,
            **kwargs,
        )

    def _render_pointlight(self, name, view):
        """Get a rendering string for a point light object.

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...).

        Parameters:
        name -- the name of the point light
        view -- the view of the point light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """
        debug("PointLight", name, "Processing")

        source = view.Source
        specifics = self._get_renderer_specifics(view)
        general_data = self._get_general_data()
        kwargs = {}
        kwargs.update(specifics)
        kwargs.update(general_data)

        # Get location, color
        location = App.Base.Vector(source.Location)
        color = RGB(source.Color)

        # Rescale
        location.multiply(SCALE)

        # We accept missing Power (default value: 60)...
        power = getattr(source, "Power", 60)

        # Send everything to renderer module
        return self._call_renderer(
            "write_pointlight",
            name,
            location,
            color,
            power,
            **kwargs,
        )

    def _render_arealight(self, name, view):
        """Get a rendering string for an area light object.

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
        placement.Base.multiply(SCALE)  # Rescale
        color = RGB(source.Color)
        power = float(source.Power)
        size_u = float(source.SizeU) * SCALE
        size_v = float(source.SizeV) * SCALE
        transparent = bool(source.Transparent)
        specifics = self._get_renderer_specifics(view)
        general_data = self._get_general_data()
        kwargs = {}
        kwargs.update(specifics)
        kwargs.update(general_data)

        # Send everything to renderer module
        return self._call_renderer(
            "write_arealight",
            name,
            placement,
            size_u,
            size_v,
            color,
            power,
            transparent,
            **kwargs,
        )

    def _render_sunskylight(self, name, view):
        """Get a rendering string for a sunsky light object.

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...).

        Parameters:
        name -- the name of the sunsky light
        view -- the view of the sunsky light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """
        debug("SunskyLight", name, "Processing")
        src = view.Source
        direction = App.Vector(src.SunDirection)
        turbidity = float(src.Turbidity)
        albedo = float(src.GroundAlbedo)
        sun_intensity = float(src.SunIntensity)
        sky_intensity = float(src.SkyIntensity)
        # Distance from the sun:
        distance = App.Units.parseQuantity("151000000 km").Value

        assert turbidity >= 0, "Negative turbidity"

        assert albedo >= 0, "Negative albedo"

        assert direction.Length, "Sun direction is null"

        specifics = self._get_renderer_specifics(view)
        general_data = self._get_general_data()
        kwargs = {}
        kwargs.update(specifics)
        kwargs.update(general_data)

        return self._call_renderer(
            "write_sunskylight",
            name,
            direction,
            distance,
            turbidity,
            albedo,
            sun_intensity,
            sky_intensity,
            **kwargs,
        )

    def _render_imagelight(self, name, view):
        """Get a rendering string for an image light object.

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...).

        Parameters:
        name -- the name of the image light
        view -- the view of the image light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """
        debug("ImageLight", name, "Processing")
        src = view.Source
        image = src.ImageFile
        specifics = self._get_renderer_specifics(view)
        general_data = self._get_general_data()
        kwargs = {}
        kwargs.update(specifics)
        kwargs.update(general_data)

        return self._call_renderer("write_imagelight", name, image, **kwargs)

    def _render_distantlight(self, name, view):
        """Get a rendering string for an distant light object.

        This method follows EAFP idiom and will raise exceptions if something
        goes wrong (missing attribute, inconsistent data...).

        Parameters:
        name -- the name of the image light
        view -- the view of the image light (contains the light data)

        Returns: a rendering string, obtained from the renderer module
        """
        debug("ImageLight", name, "Processing")
        src = view.Source

        color = RGB(src.Color)
        power = float(src.Power)
        direction = App.Vector(src.Direction)
        angle = src.Angle.getValueAs("°")

        specifics = self._get_renderer_specifics(view)
        general_data = self._get_general_data()
        kwargs = {}
        kwargs.update(specifics)
        kwargs.update(general_data)

        return self._call_renderer(
            "write_distantlight",
            name,
            color,
            power,
            direction,
            angle,
            **kwargs,
        )

    def _call_renderer(self, method, *args, **kwargs):
        """Call a render method of the renderer module.

        Parameters:
        -----------
        method -- the method to call (as a string)
        args -- the arguments to pass to the method

        Returns: a rendering string, obtained from the renderer module
        """
        renderer_method = getattr(self.renderer_module, method)
        return renderer_method(*args, **kwargs)


# ===========================================================================
#                          Renderer Handler Exceptions
# ===========================================================================


class RendererNotFoundError(Exception):
    """Exception raised when attempted an access to an unfoundable renderer.

    Attributes:
        renderer -- the unfound renderer (str)
    """

    def __init__(self, renderer):
        """Initialize exception."""
        super().__init__()
        self.renderer = str(renderer)

    def message(self):
        """Give error message."""
        msg = (
            translate("Render", "[Render] Error: Renderer '%s' not found")
            % self.renderer
        )
        return msg
