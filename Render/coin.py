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
        self.transform = self.switch.addChild(coin.SoTransform())
        self.switch.addChild(self.transform)

        # Display group (starting point for shape or light nodes)
        self.display_group = coin.SoGroup()
        self.switch.addChild(self.display_group)

    def set_visibility(self, visible):
        """Set object visibility.

        Args:
            visible -- flag for object visibility (boolean)
        """
        visible = bool(visible)
        self.switch.whichChild(
            coin.SO_SWITCH_ALL if visible else coin.SO_SWITCH_NONE
        )

    def set_position(self, placement):
        """Set object position (translation only, no rotation).

        Args:
            placement -- placement to position object to (FreeCAD.Placement)
        """
        location = placement.Base[:3]
        self.transform.translation.setValue(location)

    def set_rotation(self, placement):
        """Set object rotation (rotation only, no translation).

        Args:
            placement -- placement to rotate object with (FreeCAD.Placement)
        """
        angle = float(placement.Rotation.Angle)
        axis = coin.SbVec3f(placement.Rotation.Axis)
        self.transform.rotation.setValue(axis, angle)

    def set_placement(self, placement):
        """Set object placement (translation and rotation).

        Args:
            placement -- placement (FreeCAD.Placement)
        """
        self.set_rotation(placement)
        self.set_position(placement)


class ShapeCoinNode(DisplayableCoinNode):
    """A class to display a Coin Shape object."""

    def __init__(self, points, vertices, **kwargs):
        """Initialize object.

        Args:
            points -- points for the shape (iterable of 3-uples)
            vertices -- vertices for the shape (iterable)

        Keyword args:
            drawstyle -- a Coin drawstyle object to describe draw style
                (optional)
        """
        super().__init__()
        # Drawstyle
        default_drawstyle = coin.SoDrawStyle()
        default_drawstyle.style = coin.SoDrawStyle.FILLED
        self.drawstyle = kwargs.get("drawstyle", default_drawstyle)
        self.display_group.addChild(self.drawstyle)

        # Coordinates
        self.coords = coin.SoCoordinate3()
        self.coords.point.setValues(0, len(points), points)
        self.display_group.addChild(self.coords)

        # Shape (faceset)
        self.faceset = coin.SoFaceSet()
        self.faceset.numVertices.setValues(0, len(vertices), vertices)
        self.display_group.addChild(self.faceset)
