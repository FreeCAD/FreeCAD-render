# ***************************************************************************
# *                                                                         *
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

"""This module implements classes to deal with Coin3D display."""

from pivy import coin


class DisplayableCoinNode:
    """A displayable base for Coin objects.

    Implements visibility and placement primitives.
    """

    def __init__(self):
        """Initialize object."""
        # Root node
        self.node = coin.SoSeparator()

        # Switch (visibility)
        self.switch = coin.SoSwitch()
        self.node.addChild(self.switch)

        # Transform (placement)
        self.transform = coin.SoTransform()
        self.switch.addChild(self.transform)

        # Display group (starting point for shape or light nodes)
        self.display_group = coin.SoGroup()
        self.switch.addChild(self.display_group)

        self.set_visibility(True)  # TODO Where should it be?

    def set_visibility(self, visible):
        """Set object visibility.

        Args:
            visible -- flag for object visibility (boolean)
        """
        visible = bool(visible)
        self.switch.whichChild = (
            coin.SO_SWITCH_ALL if visible else coin.SO_SWITCH_NONE
        )

    def set_position(self, position):
        """Set object position (translation only, no rotation).

        Args:
            position -- a 3D vector to position object to
        """
        position = coin.SbVec3f(position)
        self.transform.translation.setValue(position)

    def set_rotation(self, axis, angle):
        """Set object rotation (rotation only, no translation).

        Args:
            axis -- rotation axis (3D vector)
            angle -- rotation angle (float)
        """
        angle = float(angle)
        axis = coin.SbVec3f(axis)
        self.transform.rotation.setValue(axis, angle)

    def set_placement(self, placement):
        """Set object placement (translation and rotation).

        Args:
            placement -- placement (FreeCAD.Placement)
        """
        self.set_rotation(placement.Rotation.Axis, placement.Rotation.Angle)
        self.set_position(placement.Base)

    def set_scale(self, scale):
        """Set object scale

        Args:
            scale -- the scale to set object to (vec3)
        """
        self.transform.scaleFactor.setValue(scale)

    def insert(self, subgraph, position=0):
        """Insert this object in subgraph at given position.

        Default insertion position is first position.

        Args:
            subgraph -- the subgraph, a Coin SoGroup object
            position -- position where to insert
        """
        subgraph.insertChild(self.node, position)

    def append(self, subgraph):
        """Append object to subgraph.

        Args:
            scene -- the scene, a Coin SoGroup object
        """
        subgraph.addChild(self.node)

    def add_display_mode(self, vobj, display_mode):
        """Add a display mode for root node in FreeCAD.

        Args:
            vobj -- a FreeCAD ViewProvider
            display_mode -- display mode name
        """
        display_mode = str(display_mode)
        vobj.addDisplayMode(self.node, display_mode)

    def add_display_modes(self, vobj, display_modes):
        """Add a list of display modes for root node in FreeCAD.

        Args:
            vobj -- a FreeCAD ViewProvider
            display_modes -- display mode names
        """
        display_modes = iter(display_modes)
        for display_mode in display_modes:
            self.add_display_mode(vobj, display_mode)

    def remove_from_scene(self, scene):
        """Remove object from coin scene.

        Args:
            scene -- coin scene to remove object from
        """
        scene.removeChild(self.node)


class ShapeCoinNode(DisplayableCoinNode):
    """A class to display a Coin Shape object."""

    def __init__(self, points, vertices, **kwargs):
        """Initialize object.

        Args:
            points -- points for the shape (iterable of 3-uples)
            vertices -- vertices for the shape (iterable)

        Keyword args:
            wireframe -- flag to draw a wireframe (SoLineSet) rather than a
                shaded object (SoFaceSet)
            drawstyle -- a Coin SoDrawStyle object to describe draw style
                (optional)
            material -- a Coin SoMaterial object to describe material
                (optional)
        """
        super().__init__()

        # Drawstyle
        try:
            self.drawstyle = kwargs["drawstyle"]
        except KeyError:
            self.drawstyle = coin.SoDrawStyle()
            self.drawstyle.lineWidth = 1
            self.drawstyle.linePattern = 0xAAAA
            self.drawstyle.style = coin.SoDrawStyle.FILLED
        finally:
            self.display_group.addChild(self.drawstyle)

        # Material
        try:
            self.material = kwargs["material"]
        except KeyError:
            self.material = coin.SoMaterial()
        finally:
            self.display_group.addChild(self.material)

        # Coordinates
        self.coords = coin.SoCoordinate3()
        self.coords.point.setValues(0, len(points), points)
        self.display_group.addChild(self.coords)

        # Shape (faceset or lineset)
        wireframe = kwargs.get("wireframe", False)
        self.shape = coin.SoLineSet() if wireframe else coin.SoFaceSet()
        self.shape.numVertices.setValues(0, len(vertices), vertices)
        self.display_group.addChild(self.shape)

    def set_color(self, **kwargs):
        """Set various color attributes.

        Keyword args:
            diffuse -- diffuse color
            emissive -- emissive color
            specular -- specular color
            ambient -- ambient color

        (see Coin SoMaterial documentation for more details)
        """
        for key, value in kwargs.items():
            color = coin.SbColor(value)
            if key == "diffuse":
                attribute = self.material.diffuseColor
            elif key == "emissive":
                attribute = self.material.emissiveColor
            elif key == "specular":
                attribute = self.material.specularColor
            elif key == "ambient":
                attribute = self.material.ambientColor
            else:
                raise KeyError("Unknown color attribute")
            attribute.setValue(color)


class LightCoinNode:
    """A class to display a Coin Light object."""

    def __init__(self, cls, **kwargs):
        """Initialize object.

        Args:
            cls -- A Coin light class (SoLight subclass)
        """
        self._light = cls(**kwargs)

    def set_color(self, color):
        """Set point light color."""
        color = coin.SbColor(color)
        self._light.color.setValue(color)

    def set_intensity(self, intensity):
        """Set point light intensity."""
        intensity = float(intensity)
        self._light.intensity.setValue(intensity)

    def set_visibility(self, visible):
        """Set light visibility.

        Args:
            visible -- flag for object visibility (boolean)
        """
        visible = bool(visible)
        self._light.on.setValue(visible)

    def add_to_scene(self, scene, position=0):
        """Insert the light in scene at given position.

        Default insertion position is first position.

        Args:
            scene -- the subgraph, a Coin SoGroup object
            position -- position where to insert
        """
        scene.insertChild(self._light, position)

    def remove_from_scene(self, scene):
        """Remove the light from coin scene.

        Args:
            scene -- coin scene to remove object from
        """
        scene.removeChild(self._light)


class PointlightCoinNode(LightCoinNode):
    """A class to display a Coin Pointlight object."""

    def __init__(self):
        """Initialize light."""
        super().__init__(coin.SoPointLight)

    def set_location(self, location):
        """Set point light location."""
        location = coin.SbVec3f(location)
        self._light.location.setValue(location)
