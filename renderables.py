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

"""This module implements the Renderable object, an atomic rendering entity.

A Renderable is a tuple (name, mesh, material). It is a convenient object
to send to renderers.
Each object in FreeCAD should be splittable into a list of Renderables. This
module provides the function to convert FreeCAD objects into collection of
Renderables
"""


# ===========================================================================
#                                   Imports
# ===========================================================================


import itertools
import collections

from renderutils import translate, debug, warn, getproxyattr
from rendermaterials import is_multimat


# ===========================================================================
#                                   Exports
# ===========================================================================


Renderable = collections.namedtuple("Renderable", "name mesh material")


def get_renderables(obj, name, upper_material, mesher):
    """Get the renderables from a FreeCAD object.

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
    mesher -- a callable which can convert a shape into a mesh

    Returns:
    A list of renderables
    """
    obj_is_applink = obj.isDerivedFrom("App::Link")
    obj_is_partfeature = obj.isDerivedFrom("Part::Feature")
    obj_is_meshfeature = obj.isDerivedFrom("Mesh::Feature")
    obj_type = getproxyattr(obj, "Type", "")

    mat = (getattr(obj, "Material", None)
           if upper_material is None else upper_material)
    del upper_material  # Should not be used after this point...

    label = getattr(obj, "Label", name)

    # Link (plain)
    if obj_is_applink and not obj.ElementCount:
        debug("Object", label, "'Link (plain)' detected")
        renderables = _get_rends_from_plainapplink(obj, name, mat, mesher)

    # Link (array)
    elif obj_is_applink and obj.ElementCount:
        debug("Object", label, "'Link (array)' detected")
        renderables = _get_rends_from_elementlist(obj, name, mat, mesher)

    # Array, PathArray
    elif obj_is_partfeature and obj_type in ("Array", "PathArray"):
        debug("Object", label, "'%s' detected" % obj_type)
        expand_array = getattr(obj, "ExpandArray", False)
        renderables = (_get_rends_from_array(obj, name, mat, mesher)
                       if not expand_array else
                       _get_rends_from_elementlist(obj, name, mat, mesher))

    # Window
    elif obj_is_partfeature and obj_type == "Window":
        debug("Object", label, "'Window' detected")
        renderables = _get_rends_from_window(obj, name, mat, mesher)

    # Plain part
    elif obj_is_partfeature:
        debug("Object", label, "'Part::Feature' detected")
        renderables = [Renderable(name, mesher(obj.Shape), mat)]

    # Mesh
    elif obj_is_meshfeature:
        debug("Object", label, "'Mesh::Feature' detected")
        renderables = [Renderable(name, obj.Mesh, mat)]

    # Unhandled
    else:
        renderables = []
        msg = translate("Render", "Unhandled object type")
        raise TypeError(msg)

    return renderables


def check_renderables(renderables):
    """Assert compliance of a list of renderables."""
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


# ===========================================================================
#                              Locals (helpers)
# ===========================================================================


def _get_rends_from_elementlist(obj, name, material, mesher):
    """Get renderables from an object containing a list of elements.

    The list of elements must be in the ElementList property of the
    object.
    This function is useful for Link Arrays and expanded Arrays

    Parameters:
    obj -- the container object
    name -- the name assigned to the container object for rendering
    material -- the material for the container object
    mesher -- a callable object which converts a shape into a mesh

    Returns:
    A list of renderables for the array object
    """
    renderables = []
    base_plc_matrix = obj.Placement.toMatrix()
    elements = itertools.compress(obj.ElementList, obj.VisibilityList)

    for element in elements:
        assert element.isDerivedFrom("App::LinkElement")
        elem_name = "%s_%s" % (name, element.Name)
        base_rends = get_renderables(element.LinkedObject,
                                     elem_name,
                                     material,
                                     mesher)
        element_plc_matrix = element.LinkPlacement.toMatrix()
        linkedobject_plc_inverse_matrix = \
            element.LinkedObject.Placement.inverse().toMatrix()
        for base_rend in base_rends:
            new_mesh = base_rend.mesh.copy()
            if not obj.LinkTransform:
                new_mesh.transform(linkedobject_plc_inverse_matrix)
            new_mesh.transform(base_plc_matrix)
            new_mesh.transform(element_plc_matrix)
            new_mat = _get_material(base_rend, material)
            new_name = base_rend.name
            new_rend = Renderable(new_name, new_mesh, new_mat)
            renderables.append(new_rend)

    return renderables


def _get_rends_from_plainapplink(obj, name, material, mesher):
    """Get renderables from an App::Link where Count==0.

    Parameters:
    obj -- the App::Link object
    name -- the name assigned to the Link Array object for rendering
    material -- the material for the Link Array object
    mesher -- a callable object which converts a shape into a mesh

    Returns:
    A list of renderables for the object
    """
    linkedobj = obj.LinkedObject
    base_rends = get_renderables(linkedobj, name, material, mesher)
    link_plc_matrix = obj.LinkPlacement.toMatrix()
    linkedobj_plc_inverse_matrix = linkedobj.Placement.inverse().toMatrix()

    def new_rend(base_rend):
        new_name = "%s_%s" % (name, base_rend.name)
        new_mesh = base_rend.mesh.copy()
        new_mat = _get_material(base_rend, material)
        if not obj.LinkTransform:
            new_mesh.transform(linkedobj_plc_inverse_matrix)
        new_mesh.transform(link_plc_matrix)
        return Renderable(new_name, new_mesh, new_mat)

    return [new_rend(r) for r in base_rends]


def _get_rends_from_array(obj, name, material, mesher):
    """Get renderables from an array.

    The array should not be expanded into an element list (ExpandArray flag),
    otherwise _get_rends_from_elementlist should be called instead.
    If the array does not use links, it is rendered as a single shape. However,
    in this case, only one material will be applied to the whole shape.


    Parameters:
    obj -- the Array object
    name -- the name assigned to the Array object for rendering
    material -- the material for the Array object
    mesher -- a callable object which converts a shape into a mesh

    Returns:
    A list of renderables for the Array object
    """
    base = obj.Base

    try:
        visibility_list = obj.VisibilityList
        placement_list = obj.PlacementList
    except AttributeError:
        # Array does not use link...
        material = material if material else getattr(base, "Material", None)
        return [Renderable(name, mesher(obj.Shape), material)]

    base_rends = get_renderables(base, base.Name, material, mesher)
    obj_plc_matrix = obj.Placement.toMatrix()
    base_inv_plc_matrix = base.Placement.inverse().toMatrix()
    placements = (itertools.compress(placement_list, visibility_list)
                  if visibility_list
                  else obj.PlacementList)

    def new_rend(enum_plc, base_rend):
        counter, plc = enum_plc
        new_mesh = base_rend.mesh.copy()
        if not obj.LinkTransform:
            new_mesh.transform(base_inv_plc_matrix)
        new_mesh.transform(plc.toMatrix())
        new_mesh.transform(obj_plc_matrix)
        subname = "%s_%s_%s" % (name, base_rend.name, counter)
        new_mat = _get_material(base_rend, material)
        return Renderable(subname, new_mesh, new_mat)

    rends = itertools.product(enumerate(placements), base_rends)

    return [new_rend(*r) for r in rends]


def _get_rends_from_window(obj, name, material, mesher):
    """Get renderables from an Window object (from Arch workbench).

    Parameters:
    obj -- the Window object
    name -- the name assigned to the Window object for rendering
    material -- the material for the Window object (should be a
                multimaterial)
    mesher -- a callable object which converts a shape into a mesh

    Returns:
    A list of renderables for the Window object
    """
    # Subobjects names
    window_parts = obj.WindowParts
    if not window_parts and hasattr(obj, "CloneOf") and obj.CloneOf:
        # Workaround: if obj is a window Clone, WindowsParts is unfortunately
        # not replicated (must be a bug...). Therefore we look at base's
        # WindowsParts
        window_parts = obj.CloneOf.WindowParts

    subnames = window_parts[0::5]  # Names every 5th item...
    names = ["%s_%s" % (name, s.replace(' ', '_')) for s in subnames]

    # Subobjects meshes
    meshes = [mesher(s) for s in obj.Shape.childShapes()]

    # Subobjects materials
    if material is not None:
        assert is_multimat(material), "Multimaterial expected"
        mats_dict = dict(zip(material.Names, material.Materials))
        mats = [mats_dict.get(s) for s in subnames]
        if [m for m in mats if not m]:
            msg = translate("Render", "Incomplete multimaterial (missing {})")
            missing_mats = ', '.join(set(subnames) - mats_dict.keys())
            warn("Window", obj.Label, msg.format(missing_mats))
    else:
        mats = [None] * len(subnames)

    # Build renderables
    return [Renderable(*r) for r in zip(names, meshes, mats)]


def _get_material(base_renderable, upper_material):
    """Get material from a base renderable and an upper material."""
    upper_mat_is_multimat = is_multimat(upper_material)

    return (base_renderable.material
            if (upper_material is None or upper_mat_is_multimat)
            else upper_material)
