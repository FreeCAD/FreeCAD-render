# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements a Camera object for Render workbench.

Camera object allows to take a snapshot of Coin Camera settings and to use them
later for rendering.
"""

from math import degrees, radians
from types import SimpleNamespace
import shlex

from pivy import coin
from PySide.QtCore import QT_TRANSLATE_NOOP
import FreeCAD as App
import FreeCADGui as Gui

from Render.base import (
    BaseFeature,
    Prop,
    BaseViewProvider,
    CtxMenuItem,
    PointableFeatureMixin,
    PointableViewProviderMixin,
)
from Render.coin import ShapeCoinNode


# Enumeration of allowed values for ViewportMapping parameter (see Coin
# documentation)
# Nota: Keep following tuple in original order, as relationship between
# values and indexes order matters and is used for reverse transcoding
VIEWPORTMAPPINGENUM = (
    "CROP_VIEWPORT_FILL_FRAME",
    "CROP_VIEWPORT_LINE_FRAME",
    "CROP_VIEWPORT_NO_FRAME",
    "ADJUST_CAMERA",
    "LEAVE_ALONE",
)


# ===========================================================================


class Camera(PointableFeatureMixin, BaseFeature):
    """A camera for rendering.

    This object allows to record camera settings from the Coin camera, and to
    reuse them for rendering.

    Camera Orientation is defined by a Rotation Axis and a Rotation Angle,
    applied to 'default camera'.
    Default camera looks from (0,0,1) towards the origin (target is (0,0,-1),
    and the up direction is (0,1,0).

    For more information, see Coin documentation, Camera section.
    <https://developer.openinventor.com/UserGuides/Oiv9/Inventor_Mentor/Cameras_and_Lights/Cameras.html>
    """

    VIEWPROVIDER = "ViewProviderCamera"

    PROPERTIES = {
        "Projection": Prop(
            "App::PropertyEnumeration",
            "Camera",
            QT_TRANSLATE_NOOP(
                "Render", "Type of projection: Perspective/Orthographic"
            ),
            ("Perspective", "Orthographic"),
        ),
        "ViewportMapping": Prop(
            "App::PropertyEnumeration",
            "Camera",
            QT_TRANSLATE_NOOP("Render", "(See Coin documentation)"),
            VIEWPORTMAPPINGENUM,
        ),
        "AspectRatio": Prop(
            "App::PropertyFloat",
            "Camera",
            QT_TRANSLATE_NOOP("Render", "Ratio width/height of the camera."),
            1.0,
        ),
        "NearDistance": Prop(
            "App::PropertyDistance",
            "Camera",
            QT_TRANSLATE_NOOP("Render", "Near distance, for clipping"),
            0.0,
        ),
        "FarDistance": Prop(
            "App::PropertyDistance",
            "Camera",
            QT_TRANSLATE_NOOP("Render", "Far distance, for clipping"),
            200.0,
        ),
        "FocalDistance": Prop(
            "App::PropertyDistance",
            "Camera",
            QT_TRANSLATE_NOOP("Render", "Focal distance"),
            100.0,
        ),
        "Height": Prop(
            "App::PropertyLength",
            "Camera",
            QT_TRANSLATE_NOOP("Render", "Height, for orthographic camera"),
            5.0,
        ),
        "HeightAngle": Prop(
            "App::PropertyAngle",
            "Camera",
            QT_TRANSLATE_NOOP(
                "Render",
                "Height angle, for perspective camera, in "
                "degrees. Important: This value will be sent as "
                "'Field of View' to the renderers.",
            ),
            60,
        ),
    }

    def on_create_cb(self, fpo, viewp, **kwargs):
        """Complete 'create' (callback)."""
        if App.GuiUp:
            viewp.set_camera_from_gui()
        else:
            set_cam_from_coin_string(fpo, DEFAULT_CAMERA_STRING)


# ===========================================================================


class ViewProviderCamera(PointableViewProviderMixin, BaseViewProvider):
    """View Provider of Camera class."""

    ICON = ":/icons/camera-photo.svg"
    CONTEXT_MENU = [
        CtxMenuItem(
            QT_TRANSLATE_NOOP("Render", "Set GUI to this camera"),
            "set_gui_from_camera",
        ),
        CtxMenuItem(
            QT_TRANSLATE_NOOP("Render", "Set this camera to GUI"),
            "set_camera_from_gui",
        ),
    ]
    DISPLAY_MODES = ["Shaded"]  # TODO For mixin
    ON_CHANGED = {"Visibility": "_change_visibility"}

    def on_attach_cb(self, vobj):
        """Respond to created/restored object event (callback).

        Args:
            vobj -- Related ViewProviderDocumentObject
        """

        # Here we create a coin representation
        # pylint: disable=attribute-defined-outside-init
        self.coin = SimpleNamespace()

        size = 5
        height = 10
        points = [
                (-size * 2, +size, 0),  # Front rectangle
                (+size * 2, +size, 0),  # Front rectangle
                (+size * 2, -size, 0),  # Front rectangle
                (-size * 2, -size, 0),  # Front rectangle
                (-size * 2, +size, 0),  # Front rectangle
                (-size * 2, +size, 0),  # Left triangle
                (0, 0, height * 2),  # Left triangle
                (-size * 2, -size, 0),  # Left triangle
                (+size * 2, +size, 0),  # Right triangle
                (0, 0, height * 2),  # Right triangle
                (+size * 2, -size, 0),  # Right triangle
                (-size * 1.8, 1.2 * +size, 0),  # Up triangle (arrow)
                (0, 1.4 * +size, 0),  # Up triangle (arrow)
                (+size * 1.8, 1.2 * +size, 0),  # Up triangle (arrow)
                (-size * 1.8, 1.2 * +size, 0),  # Up triangle (arrow)
            ]
        vertices = [5, 3, 3, 4]

        self.coin.shape = ShapeCoinNode(points, vertices, wireframe=True)
        self.coin.shape.add_display_mode(vobj, "Shaded")
        self.coin.shape.add_display_mode(vobj, "Wireframe")

        # Update coin elements with actual object properties
        self.update_all(self.fpo)

    # TODO Move into mixin class
    def _update_placement(self, fpo):
        """Update object placement."""
        try:
            coin_attr = self.coin.shape
        except AttributeError:
            return  # No coin representation
        location = fpo.Placement.Base[:3]
        coin_attr.transform.translation.setValue(location)
        angle = float(fpo.Placement.Rotation.Angle)
        axis = coin.SbVec3f(fpo.Placement.Rotation.Axis)
        coin_attr.transform.rotation.setValue(axis, angle)

    def onDelete(self, feature, subelements):
        """Respond to delete object event (callback)."""
        # Delete coin representation
        scene = Gui.ActiveDocument.ActiveView.getSceneGraph()
        self.coin.shape.remove_from_scene(scene)
        return True  # If False, the object wouldn't be deleted

    def _change_visibility(self, vpdo):
        """Respond to Visibility change."""
        self.coin.shape.set_visibility(vpdo.Visibility)

    def set_camera_from_gui(self):
        """Set this camera from GUI camera."""
        assert App.GuiUp, "Cannot set camera from GUI: GUI is down"
        fpo = self.fpo
        node = Gui.ActiveDocument.ActiveView.getCameraNode()
        typ = node.getTypeId()
        if typ == coin.SoPerspectiveCamera.getClassTypeId():
            fpo.Projection = "Perspective"
            fpo.HeightAngle = degrees(float(node.heightAngle.getValue()))
        elif typ == coin.SoOrthographicCamera.getClassTypeId():
            fpo.Projection = "Orthographic"
            fpo.Height = float(node.height.getValue())
        else:
            raise ValueError("Unknown camera type")

        pos = App.Vector(node.position.getValue())
        rot = App.Rotation(*node.orientation.getValue().getValue())
        fpo.Placement = App.Placement(pos, rot)

        fpo.NearDistance = float(node.nearDistance.getValue())
        fpo.FarDistance = float(node.farDistance.getValue())
        fpo.FocalDistance = float(node.focalDistance.getValue())
        fpo.AspectRatio = float(node.aspectRatio.getValue())
        index = node.viewportMapping.getValue()
        fpo.ViewportMapping = VIEWPORTMAPPINGENUM[index]

    def set_gui_from_camera(self):
        """Set GUI camera to this camera."""
        assert App.GuiUp, "Cannot set GUI from camera: GUI is down"

        fpo = self.fpo

        Gui.ActiveDocument.ActiveView.setCameraType(fpo.Projection)

        node = Gui.ActiveDocument.ActiveView.getCameraNode()

        node.position.setValue(fpo.Placement.Base)
        rot = fpo.Placement.Rotation
        axis = coin.SbVec3f(rot.Axis.x, rot.Axis.y, rot.Axis.z)
        node.orientation.setValue(axis, rot.Angle)

        node.nearDistance.setValue(float(fpo.NearDistance))
        node.farDistance.setValue(float(fpo.FarDistance))
        node.focalDistance.setValue(float(fpo.FocalDistance))
        node.aspectRatio.setValue(float(fpo.AspectRatio))
        node.viewportMapping.setValue(getattr(node, fpo.ViewportMapping))

        if fpo.Projection == "Orthographic":
            node.height.setValue(float(fpo.Height))
        elif fpo.Projection == "Perspective":
            node.heightAngle.setValue(radians(float(fpo.HeightAngle)))


# ===========================================================================


def set_cam_from_coin_string(cam, camstr):
    """Set a Camera object from a Coin camera string.

    Args:
        cam -- The Camera to set (as a Camera FeaturePython object)
        camstr -- The Coin-formatted camera string

    camstr should contain a string in Coin/OpenInventor format, for instance:
    #Inventor V2.1 ascii


    PerspectiveCamera {
     viewportMapping ADJUST_CAMERA
     position 0 -1.3207401 0.82241058
     orientation 0.99999666 0 0  0.26732138
     nearDistance 1.6108983
     farDistance 6611.4492
     aspectRatio 1
     focalDistance 5
     heightAngle 0.78539819

    }

    or (ortho camera):
    #Inventor V2.1 ascii


    OrthographicCamera {
     viewportMapping ADJUST_CAMERA
     position 0 0 1
     orientation 0 0 1  0
     nearDistance 0.99900001
     farDistance 1.001
     aspectRatio 1
     focalDistance 5
     height 4.1421356

    }
    """
    # Split, clean and tokenize
    camdata = [
        y
        for y in [shlex.split(x, comments=True) for x in camstr.split("\n")]
        if y
    ]
    camdict = {y[0]: y[1:] for y in camdata}

    cam.Projection = camdata[0][0][0:-6]  # Data should start with Cam Type...
    assert cam.Projection in (
        "Perspective",
        "Orthographic",
    ), "Invalid camera header in camera string"
    try:
        pos = App.Vector(camdict["position"][0:3])
        rot = App.Rotation(
            App.Vector(camdict["orientation"][0:3]),
            degrees(float(camdict["orientation"][3])),
        )
        cam.Placement = App.Placement(pos, rot)
        cam.FocalDistance = float(camdict["focalDistance"][0])
    except KeyError as err:
        raise ValueError(
            "Missing field in camera string: {}".format(err)
        ) from err

    # It may happen that aspect ratio and viewport mapping are not set in
    # camstr...
    try:
        cam.AspectRatio = float(camdict["aspectRatio"][0])
    except KeyError:
        cam.AspectRatio = 1.0
    try:
        cam.ViewportMapping = str(camdict["viewportMapping"][0])
    except KeyError:
        cam.ViewportMapping = "ADJUST_CAMERA"

    # It may also happen that near & far distances are not set in camstr...
    try:
        cam.NearDistance = float(camdict["nearDistance"][0])
    except KeyError:
        pass
    try:
        cam.FarDistance = float(camdict["farDistance"][0])
    except KeyError:
        pass

    if cam.Projection == "Orthographic":
        cam.Height = float(camdict["height"][0])
    elif cam.Projection == "Perspective":
        cam.HeightAngle = degrees(float(camdict["heightAngle"][0]))


def get_coin_string_from_cam(cam):
    """Return camera data in Coin string format.

    Args:
        cam -- The Camera object to generate Coin string from.
    """

    def check_enum(field):
        """Check whether the enum field value is valid."""
        assert getattr(cam, field) in Camera.PROPERTIES[field].Default, (
            "Invalid %s value" % field
        )

    check_enum("Projection")
    check_enum("ViewportMapping")

    res = list()
    res.append("#Inventor V2.1 ascii\n\n\n")
    res.append("{}Camera {{".format(cam.Projection))
    res.append(" viewportMapping {}".format(cam.ViewportMapping))
    res.append(" position {} {} {}".format(*cam.Placement.Base))
    res.append(
        " orientation {} {} {} {}".format(
            *cam.Placement.Rotation.Axis, cam.Placement.Rotation.Angle
        )
    )
    res.append(" nearDistance {}".format(float(cam.NearDistance)))
    res.append(" farDistance {}".format(float(cam.FarDistance)))
    res.append(" aspectRatio {}".format(float(cam.AspectRatio)))
    res.append(" focalDistance {}".format(float(cam.FocalDistance)))
    if cam.Projection == "Orthographic":
        res.append(" height {}".format(float(cam.Height)))
    elif cam.Projection == "Perspective":
        res.append(" heightAngle {}".format(radians(cam.HeightAngle)))
    res.append("}\n")
    return "\n".join(res)


def retrieve_legacy_camera(project):
    """Transform legacy camera project attribute into Camera object.

    This function is provided for backward compatibility (when camera
    information was stored as a string in a project's property).
    The resulting Camera object is created in the current project.

    Args:
        project -- The Rendering Project where to find legacy camera
            information
    """
    assert isinstance(
        project.Camera, str
    ), "Project's Camera property should be a string"
    _, fpo, _ = Camera.create()
    set_cam_from_coin_string(fpo, project.Camera)


# A default camera...
DEFAULT_CAMERA_STRING = """\
#Inventor V2.1 ascii

OrthographicCamera {
  viewportMapping ADJUST_CAMERA
  position -0 -0 100
  orientation 0 0 1  0
  aspectRatio 1
  focalDistance 100
  height 100
}
"""
