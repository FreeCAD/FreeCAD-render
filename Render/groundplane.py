# ***************************************************************************
# *                                                                         *
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

"""This module implements a ground plane, as a ducktyping view."""

from types import SimpleNamespace

import FreeCAD as App
import Mesh

from Render.rdrhandler import RenderingTypes
from Render.utils import clamp


def create_groundplane_view(project):
    """Create a (ducktyping) view on a (ducktyping) ground plane object."""
    result = SimpleNamespace()
    result.Source = _GroundPlane(project)
    result.AutoSmooth = False
    result.AutoSmoothAngle = 0.0
    result.Material = None
    return result


class _GroundPlane:
    """A ducktyping object that will be rendered as a ground plane."""

    # pylint: disable=too-few-public-methods
    def __init__(self, project):
        """Initialize.

        Args:
            project: a Render.Project (for the bounding box and other
                parameters)
        """
        # pylint: disable=invalid-name
        self.Name = "__ground_plane__"
        self.FullName = "__ground_plane__"
        self.Label = "__ground_plane__"

        self.Mesh = Mesh.Mesh()
        bbox = project.get_bounding_box()
        self.Document = project.fpo.Document

        if bbox.isValid():
            zpos = project.fpo.GroundPlaneZ
            color = project.fpo.GroundPlaneColor  # Keep it in FCD format
            sizefactor = project.fpo.GroundPlaneSizeFactor

            margin = bbox.DiagonalLength / 2 * sizefactor
            verts2d = (
                (bbox.XMin - margin, bbox.YMin - margin),
                (bbox.XMax + margin, bbox.YMin - margin),
                (bbox.XMax + margin, bbox.YMax + margin),
                (bbox.XMin - margin, bbox.YMax + margin),
            )
            vertices = [
                App.Vector(clamp(v[0]), clamp(v[1]), zpos) for v in verts2d
            ]  # Clamp to avoid huge dimensions...
            self.Mesh.addFacet(vertices[0], vertices[1], vertices[2])
            self.Mesh.addFacet(vertices[0], vertices[2], vertices[3])

        self.ViewObject = SimpleNamespace()
        self.ViewObject.Visibility = True
        self.ViewObject.ShapeColor = color
        self.ViewObject.Transparency = 0.0

        self.Proxy = SimpleNamespace()
        self.Proxy.RENDERING_TYPE = RenderingTypes.OBJECT

    # pylint: disable=invalid-name
    @staticmethod
    def isDerivedFrom(classname):
        """Mimic a Mesh::Feature."""
        return classname == "Mesh::Feature"
