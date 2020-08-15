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

"""This module implements the Renderable object, an atomic entity for
rendering.

A Renderable is a tuple (name, mesh, material). It is a convenient object
to send to renderers.
Each object in FreeCAD should be splittable into a list of Renderables. This
module also provides the function to convert FreeCAD objects into collection of
Renderables
"""


# ===========================================================================
#                                   Imports
# ===========================================================================

import itertools as it
import collections
import functools

import MeshPart
import Draft
import Part

from renderutils import translate, debug, getproxyattr


Renderable = collections.namedtuple("Renderable", "name mesh material")


def get_renderables(obj, name, upper_material):
    """Get the renderables from a FreeCAD object

    A renderable is a tuple (name, mesh, material). There can be
    several renderables for one object, for instance if the object is a
    compound of subobjects, so the result is a **list** of renderables.
    If this function does not know how to extract renderables from the
    given object, a TypeError is raised

    Parameters:
    obj -- the FreeCAD object from which to extract the renderables
    name -- the name of the object
    upper_material -- the FreeCAD material inherited from the upper
                      level

    Notes about material:
    - the freecad material (material) can be a multimaterial
    - the subobjects may have their own materials, in which case the
      submaterials will override the material parameter

    Returns:
    A list of renderables
    """
    # TODO Apply scale in Links and PathArray
    meshfromshape = functools.partial(MeshPart.meshFromShape,
                                      LinearDeflection=0.1,
                                      AngularDeflection=0.523599,
                                      Relative=False)

    def is_multimat(material):
        """Check if a material is a multimaterial"""
        return (material is not None and
                material.isDerivedFrom("App::FeaturePython") and
                material.Proxy.Type == "MultiMaterial")

    def get_material(base_renderable, upper_material):
        """Get material from a base renderable and an upper material"""
        upper_mat_is_multimat = is_multimat(upper_material)

        return (base_renderable.material
                if (upper_material is None or upper_mat_is_multimat)
                else upper_material)

    def get_rends_from_elementlist(obj, upper_material):
        """Get renderables from an object containing a list of elements

        The list of elements must be in the ElementList property of the
        object.
        This function is useful for Link arrays and expanded Arrays
        """
        renderables = []
        base_plc_matrix = obj.Placement.toMatrix()
        elements = it.compress(obj.ElementList, obj.VisibilityList)

        for element in elements:
            assert element.isDerivedFrom("App::LinkElement")
            base_rends = get_renderables(element.LinkedObject,
                                         element.Name,
                                         upper_material)
            element_plc_matrix = element.LinkPlacement.toMatrix()
            linkedobject_plc_inverse_matrix = \
                element.LinkedObject.Placement.inverse().toMatrix()
            for base_rend in base_rends:
                new_mesh = base_rend.mesh.copy()
                if not obj.LinkTransform:
                    new_mesh.transform(linkedobject_plc_inverse_matrix)
                new_mesh.transform(base_plc_matrix)
                new_mesh.transform(element_plc_matrix)
                new_mat = get_material(base_rend, base_mat)
                new_name = base_rend.name
                new_rend = Renderable(new_name, new_mesh, new_mat)
                renderables.append(new_rend)

        return renderables

    obj_is_group = hasattr(obj, "Group")
    obj_is_applink = obj.isDerivedFrom("App::Link")
    obj_is_partfeature = obj.isDerivedFrom("Part::Feature")
    obj_is_meshfeature = obj.isDerivedFrom("Mesh::Feature")
    obj_type = getproxyattr(obj, "Type", "")

    base_mat = (getattr(obj, "Material", None)
                if upper_material is None else upper_material)
    del upper_material  # Should not be used after this point...

    label = getattr(obj, "Label", name)

    # Group
    if obj_is_group:
        debug("Object", label, "'Group' detected")
        shps = [o.Shape for o in Draft.getGroupContents(obj)
                if hasattr(o, "Shape")]
        mesh = meshfromshape(Shape=Part.makeCompound(shps))
        renderables = [Renderable(name, mesh, base_mat)]

    # Link (plain)
    elif obj_is_applink and not obj.ElementCount:
        debug("Object", label, "'Link (plain)' detected")
        base_rends = get_renderables(obj.LinkedObject, name, base_mat)
        renderables = []
        link_plc_matrix = obj.LinkPlacement.toMatrix()
        linkedobject_plc_inverse_matrix = \
            obj.LinkedObject.Placement.inverse().toMatrix()
        for base_rend in base_rends:
            new_name = "%s_%s" % (name, base_rend.name)
            new_mesh = base_rend.mesh.copy()
            new_mat = get_material(base_rend, base_mat)
            if not obj.LinkTransform:
                new_mesh.transform(linkedobject_plc_inverse_matrix)
            new_mesh.transform(link_plc_matrix)
            new_rend = Renderable(new_name, new_mesh, new_mat)
            renderables.append(new_rend)

    # Link (array)
    elif obj_is_applink and obj.ElementCount:
        debug("Object", label, "'Link (array)' detected")
        renderables = get_rends_from_elementlist(obj, base_mat)

    # Array, PathArray
    elif obj_is_partfeature and obj_type in ("Array", "PathArray"):
        debug("Object", label, "'%s' detected" % obj_type)
        renderables = []

        if not obj.ExpandArray:
            base_rends = get_renderables(obj.Base,
                                         obj.Base.Name,
                                         base_mat)
            base_plc = obj.Placement
            base_inv_plc_matrix = \
                obj.Base.Placement.inverse().toMatrix()
            placements = (
                it.compress(obj.PlacementList, obj.VisibilityList)
                if obj.VisibilityList
                else obj.PlacementList)
            for counter, plc in enumerate(placements):
                # Apply placement to base renderables
                for base_rend in base_rends:
                    new_mesh = base_rend.mesh.copy()
                    if not obj.LinkTransform:
                        new_mesh.transform(base_inv_plc_matrix)
                    new_mesh.transform(plc.toMatrix())
                    new_mesh.transform(base_plc.toMatrix())
                    subname = "%s_%s_%s" % \
                        (name, base_rend.name, counter)
                    new_mat = get_material(base_rend, base_mat)
                    new_rend = Renderable(subname, new_mesh, new_mat)
                    renderables.append(new_rend)
        else:
            renderables = get_rends_from_elementlist(obj, base_mat)

    # Window
    elif obj_is_partfeature and obj_type == "Window":
        debug("Object", label, "'Window' detected")

        # Subobjects names
        subnames = obj.WindowParts[0::5]  # Names every 5th item...
        names = ["%s_%s" % (name, s) for s in subnames]

        # Subobjects meshes
        meshes = [meshfromshape(Shape=s)
                  for s in obj.Shape.childShapes()]

        # Subobjects materials
        # 'base_mat' should be a multimaterial or None
        if base_mat is not None:
            assert is_multimat(base_mat), "Multimaterial expected"
            mats_dict = dict(zip(base_mat.Names, base_mat.Materials))
            mats = [mats_dict[s] for s in subnames]
        else:
            mats = [None] * len(subnames)
        # Build renderables
        renderables = \
            [Renderable(*r) for r in zip(names, meshes, mats)]

    # Plain part
    elif obj_is_partfeature:
        debug("Object", label, "'Part::Feature' detected")
        mesh = meshfromshape(Shape=obj.Shape)
        renderables = [Renderable(name, mesh, base_mat)]

    # Mesh
    elif obj_is_meshfeature:
        debug("Object", label, "'Mesh::Feature' detected")
        mesh = obj.Mesh
        renderables = [Renderable(name, mesh, base_mat)]

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
