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

A Renderable is a tuple (name, mesh, material, default color). It is a
convenient object to send to renderers.
Each object in FreeCAD should be splittable into a list of Renderables. This
module provides the function to convert a FreeCAD object into a collection of
Renderables
"""


# ===========================================================================
#                                   Imports
# ===========================================================================


import itertools
import collections
import math

from renderutils import translate, debug, warn, getproxyattr, RGBA
from rendermaterials import is_multimat, is_valid_material


# ===========================================================================
#                                   Exports
# ===========================================================================


Renderable = collections.namedtuple("Renderable",
                                    "name mesh material defcolor")


def get_renderables(obj, name, upper_material, mesher, **kwargs):
    """Get the renderables from a FreeCAD object.

    A renderable is a tuple (name, mesh, material). There can be
    several renderables for one object, for instance if the object is a
    compound of subobjects, so the result of this function is a **list**
    of renderables.
    If this function does not know how to extract renderables from the
    given object, a TypeError is raised

    Parameters:
        obj -- the FreeCAD object from which to extract the renderables
        name -- the name of the object
        upper_material -- the FreeCAD material inherited from the upper
            level
        mesher -- a callable which can convert a shape into a mesh

    Keywords arguments:
        ignore_unknown -- a flag to prevent exception raising if 'obj' is
            of no renderable type
        transparency_boost -- a factor (positive integer) to boost
            transparency in shape color

    Returns:
        A list of renderables
    """
    obj_is_applink = obj.isDerivedFrom("App::Link")
    obj_is_partfeature = obj.isDerivedFrom("Part::Feature")
    obj_is_meshfeature = obj.isDerivedFrom("Mesh::Feature")
    obj_is_app_part = obj.isDerivedFrom("App::Part")
    obj_type = getproxyattr(obj, "Type", "")

    mat = (getattr(obj, "Material", None) if upper_material is None
           else upper_material)
    mat = mat if is_valid_material(mat) or is_multimat(mat) else None
    del upper_material  # Should not be used after this point...

    label = getattr(obj, "Label", name)
    ignore_unknown = bool(kwargs.get("ignore_unknown", False))
    transparency_boost = int(kwargs.get("transparency_boost", 0))

    # Link (plain)
    if obj_is_applink and not obj.ElementCount:
        debug("Object", label, "'Link (plain)' detected")
        renderables = \
            _get_rends_from_plainapplink(obj, name, mat, mesher, **kwargs)

    # Link (array)
    elif obj_is_applink and obj.ElementCount:
        debug("Object", label, "'Link (array)' detected")
        renderables = \
            _get_rends_from_elementlist(obj, name, mat, mesher, **kwargs)

    # Array, PathArray
    elif obj_is_partfeature and obj_type in ("Array", "PathArray"):
        debug("Object", label, "'%s' detected" % obj_type)
        expand_array = getattr(obj, "ExpandArray", False)
        renderables = (
            _get_rends_from_array(obj, name, mat, mesher, **kwargs)
            if not expand_array else
            _get_rends_from_elementlist(obj, name, mat, mesher, **kwargs))

    # Window
    elif obj_is_partfeature and obj_type == "Window":
        debug("Object", label, "'Window' detected")
        renderables = _get_rends_from_window(obj, name, mat, mesher, **kwargs)

    # App part
    elif obj_is_app_part:
        debug("Object", label, "'App::Part' detected")
        renderables = _get_rends_from_part(obj, name, mat, mesher, **kwargs)

    # Plain part feature
    elif obj_is_partfeature:
        debug("Object", label, "'Part::Feature' detected")
        color = _get_shapecolor(obj, transparency_boost)
        renderables = [Renderable(name, mesher(obj.Shape), mat, color)]

    # Mesh
    elif obj_is_meshfeature:
        debug("Object", label, "'Mesh::Feature' detected")
        color = _get_shapecolor(obj, transparency_boost)
        renderables = [Renderable(name, obj.Mesh, mat, color)]

    # Unhandled
    else:
        renderables = []
        if not ignore_unknown:
            ascendants = ", ".join(obj.getAllDerivedFrom())
            msg = translate("Render",
                            "Unhandled object type (%s)" % ascendants)
            raise TypeError(msg)
        debug("Object", label, "Not renderable")

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


def _get_rends_from_elementlist(obj, name, material, mesher, **kwargs):
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
                                     mesher,
                                     **kwargs)
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
            new_color = base_rend.defcolor
            new_rend = Renderable(new_name, new_mesh, new_mat, new_color)
            renderables.append(new_rend)

    return renderables


def _get_rends_from_plainapplink(obj, name, material, mesher, **kwargs):
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
    base_rends = get_renderables(linkedobj, name, material, mesher, **kwargs)
    link_plc_matrix = obj.LinkPlacement.toMatrix()
    linkedobj_plc_inverse_matrix = linkedobj.Placement.inverse().toMatrix()

    def new_rend(base_rend):
        new_name = "%s_%s" % (name, base_rend.name)
        new_mesh = base_rend.mesh.copy()
        new_mat = _get_material(base_rend, material)
        new_color = base_rend.defcolor
        if not obj.LinkTransform:
            new_mesh.transform(linkedobj_plc_inverse_matrix)
        new_mesh.transform(link_plc_matrix)
        return Renderable(new_name, new_mesh, new_mat, new_color)

    return [new_rend(r) for r in base_rends]


def _get_rends_from_array(obj, name, material, mesher, **kwargs):
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
        color = obj.ViewObject.ShapeColor
        return [Renderable(name, mesher(obj.Shape), material, color)]

    base_rends = get_renderables(base, base.Name, material, mesher, **kwargs)
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
        new_color = base_rend.defcolor
        return Renderable(subname, new_mesh, new_mat, new_color)

    rends = itertools.product(enumerate(placements), base_rends)

    return [new_rend(*r) for r in rends]


def _get_rends_from_window(obj, name, material, mesher, **kwargs):
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

    # Subobjects colors
    transparency_boost = kwargs.get("transparency_boost", 0)
    faces_len = [len(s.Faces) for s in obj.Shape.Solids]
    colors = [_boost_tp(obj.ViewObject.DiffuseColor[i], transparency_boost)
              for i in itertools.accumulate([0] + faces_len[:-1])]

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
    return [Renderable(*r) for r in zip(names, meshes, mats, colors)]


def _get_rends_from_part(obj, name, material, mesher, **kwargs):
    """Get renderables from a Part object.

    Parameters:
        obj -- the Part object (App::Part)
        name -- the name assigned to the Part object for rendering
        material -- the material for the Part object
        mesher -- a callable object which converts a shape into a mesh

    Returns:
        A list of renderables for the Part object
    """
    def _adjust(rend, origin, upper_material):
        """Reposition to origin and set material of the given renderable."""
        origin_matrix = origin.toMatrix()
        new_mesh = rend.mesh.copy()
        new_mesh.transform(origin_matrix)
        new_mat = _get_material(rend, upper_material)
        new_color = rend.defcolor
        return Renderable(rend.name, new_mesh, new_mat, new_color)

    origin = obj.Placement

    rends = []
    for subobj in obj.Group:
        subname = "{}_{}".format(name, subobj.Name)
        if getattr(subobj, "Visibility", True):  # Add subobj only if visible
            kwargs["ignore_unknown"] = True  # Force ignore unknown materials
            rends += \
                get_renderables(subobj, subname, material, mesher, **kwargs)

    rends = [_adjust(r, origin, material) for r in rends if r.mesh.Topology[0]]

    return rends


def _get_material(base_renderable, upper_material):
    """Get material from a base renderable and an upper material."""
    upper_mat_is_multimat = is_multimat(upper_material)

    return (base_renderable.material
            if (upper_material is None or upper_mat_is_multimat)
            else upper_material)


def _get_shapecolor(obj, transparency_boost):
    """Get shape color (including transparency) from an object."""
    vobj = obj.ViewObject
    color = (RGBA(vobj.ShapeColor[0],
                  vobj.ShapeColor[1],
                  vobj.ShapeColor[2],
                  vobj.Transparency / 100)
             if vobj is not None else
             RGBA(0.8, 0.8, 0.8, 0.0))

    return _boost_tp(color, transparency_boost)


def _boost_tp(color, boost_factor):
    """Get a color with boosted transparency."""
    transparency = math.pow(color[3], 1 / (boost_factor + 1))
    return RGBA(color[0], color[1], color[2], transparency)
