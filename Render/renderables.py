# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
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
import os.path
import shutil


import FreeCAD as App

# Assembly3
try:
    if not App.GuiUp:
        # assembly3 needs Gui...
        raise ImportError()
    from freecad.asm3.assembly import (
        AsmBase,
        AsmConstraintGroup,
        AsmElementGroup,
    )
except (ImportError, ModuleNotFoundError):
    AsmBase = type(None)
    AsmConstraintGroup = type(None)
    AsmElementGroup = type(None)

# A2plus
try:
    from a2plib import isA2pPart
except (ImportError, ModuleNotFoundError):
    # pylint: disable=invalid-name
    def isA2pPart(_):
        """Default function in case a2plib is not available."""
        return False


from Render.utils import (
    translate,
    debug,
    message,
    warn,
    getproxyattr,
    RGB,
    WHITE,
    top_objects,
)
from Render.rendermaterial import is_multimat, is_valid_material
from Render.rdrexecutor import exec_in_mainthread


# ===========================================================================
#                                   Exports
# ===========================================================================


Renderable = collections.namedtuple(
    "Renderable", "name mesh material defcolor"
)


def get_renderables(obj, name, upper_material, mesher, **kwargs):
    """Get the renderables from a FreeCAD object.

    A renderable is a tuple (name, mesh, material). There can be
    several renderables for one object, for instance if the object is a
    compound of subobjects, so the result of this function is a **list**
    of renderables.
    If this function does not know how to extract renderables from the
    given object, a TypeError is raised.

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
        uvprojection -- a string giving the type of uv projection (cubic,
            spherical...). See View object and rdrhandler for valid values.

    Returns:
        A list of renderables
    """
    obj_is_applink = obj.isDerivedFrom("App::Link")
    obj_is_partfeature = obj.isDerivedFrom("Part::Feature")
    obj_is_meshfeature = obj.isDerivedFrom("Mesh::Feature")
    obj_is_app_part = obj.isDerivedFrom("App::Part")
    # obj_is_appfeature = obj.isDerivedFrom("App::Feature")
    obj_is_applinkgroup = obj.isDerivedFrom("App::LinkGroup")
    obj_is_docobjectgroup = obj.isDerivedFrom("App::DocumentObjectGroup")

    obj_type = getproxyattr(obj, "Type", "")
    try:  # Assembly 3 link
        lnkobj = obj.getLinkedObject()
        obj_is_asm3_lnk = isinstance(lnkobj.Proxy, AsmBase)
    except AttributeError:
        obj_is_asm3_lnk = False
    try:  # Assembly 3 plain
        obj_is_asm3 = isinstance(obj.Proxy, AsmBase)
    except AttributeError:
        obj_is_asm3 = False

    mat = (
        getattr(obj, "Material", None)
        if upper_material is None
        else upper_material
    )
    mat = mat if is_valid_material(mat) or is_multimat(mat) else None
    del upper_material  # Should not be used after this point...

    label = getattr(obj, "Label", name)
    ignore_unknown = bool(kwargs.get("ignore_unknown", False))
    transparency_boost = int(kwargs.get("transparency_boost", 0))

    # A2plus Part
    if isA2pPart(obj):
        debug("Object", label, "'A2plus Part detected'")
        renderables = _get_rends_from_a2plus(obj, name, mat, mesher, **kwargs)

    # Assembly3 link
    elif obj_is_asm3_lnk:
        debug("Object", label, "'Assembly3 link' detected")
        renderables = _get_rends_from_assembly3(
            obj, name, mat, mesher, **kwargs
        )

    # Assembly3
    elif obj_is_asm3:
        debug("Object", label, "'Assembly3' detected")
        renderables = _get_rends_from_assembly3(
            obj, name, mat, mesher, **kwargs
        )

    # DocumentObjectGroup
    elif obj_is_docobjectgroup:
        debug("Object", label, "'DocumentObjectGroup' detected")
        renderables = []  # TODO

    # Link (plain)
    elif obj_is_applink and not obj.ElementCount:
        debug("Object", label, "'Link (plain)' detected")
        renderables = _get_rends_from_plainapplink(
            obj, name, mat, mesher, **kwargs
        )

    # Link (array)
    elif obj_is_applink and obj.ElementCount:
        debug("Object", label, "'Link (array)' detected")
        renderables = _get_rends_from_elementlist(
            obj, name, mat, mesher, **kwargs
        )

    # LinkGroup
    elif obj_is_applinkgroup:
        debug("Object", label, "'LinkGroup' detected")
        renderables = _get_rends_from_elementlist(
            obj, name, mat, mesher, **kwargs
        )

    # Array, PathArray
    elif obj_is_partfeature and obj_type in (
        "Array",
        "PathArray",
        "PathTwistedArray",
    ):
        debug("Object", label, f"'{obj_type}' detected")
        expand_array = getattr(obj, "ExpandArray", False)
        renderables = (
            _get_rends_from_array(obj, name, mat, mesher, **kwargs)
            if not expand_array
            else _get_rends_from_elementlist(obj, name, mat, mesher, **kwargs)
        )

    # Window
    elif obj_is_partfeature and obj_type == "Window":
        debug("Object", label, "'Window' detected")
        renderables = _get_rends_from_window(obj, name, mat, mesher, **kwargs)

    # Wall
    elif obj_is_partfeature and obj_type == "Wall":
        debug("Object", label, "'Wall' detected")
        renderables = _get_rends_from_wall(obj, name, mat, mesher, **kwargs)

    # App part
    elif obj_is_app_part:
        debug("Object", label, "'App::Part' detected")
        renderables = _get_rends_from_part(obj, name, mat, mesher, **kwargs)

    # Plain part feature (including PartDesign::Body)
    elif obj_is_partfeature:
        debug("Object", label, "'Part::Feature' detected")
        renderables = _get_rends_from_partfeature(
            obj, name, mat, mesher, **kwargs
        )

    # Mesh
    elif obj_is_meshfeature:
        debug("Object", label, "'Mesh::Feature' detected")
        color = _get_shapecolor(obj, transparency_boost)
        kwargs["meshcolor"] = color
        renderables = _get_rends_from_meshfeature(
            obj, name, mat, mesher, **kwargs
        )

    # Unhandled
    else:
        renderables = []
        if not ignore_unknown:
            ascendants = ", ".join(obj.getAllDerivedFrom())
            name = getattr(obj, "FullName", "<no name>")
            msg = translate(
                "Render", f"Unhandled object type ('{name}': {ascendants})"
            )
            raise RenderableError(msg)
        debug("Object", label, "Not renderable")

    return renderables


class RenderableError(Exception):
    """An error in renderable."""

    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


def check_renderables(renderables):
    """Assert compliance of a list of renderables.

    Filter malformed meshes and return the list of "good" ones.
    """
    if not renderables:
        raise RenderableError(translate("Render", "Nothing to render"))
    result = []
    for renderable in renderables:
        mesh = renderable.mesh
        if not mesh.skip_meshing:
            if not mesh:
                warn(
                    "Export",
                    renderable.name,
                    translate("Render", "Cannot find mesh data"),
                )
                continue
            if not mesh.count_points or not mesh.count_facets:
                warn(
                    "Export",
                    renderable.name,
                    translate("Render", "Mesh topology is empty"),
                )
                continue
        result.append(renderable)
    return result


# ===========================================================================
#                           Renderable getters
# ===========================================================================

a2p_subdocs = set()


def _get_rends_from_a2plus(obj, name, material, mesher, **kwargs):
    """Get renderables from an A2plus object.

    Parameters:
    obj -- the container object
    name -- the name assigned to the container object for rendering
    material -- the material for the container object
    mesher -- a callable object which converts a shape into a mesh

    Returns:
    A list of renderables for this object
    """

    def open_subdoc(*args):
        path, *_ = args
        try:
            doc = App.openDocument(path, hidden=True)
        except OSError:
            doc = None
        return doc

    objdir = os.path.dirname(obj.Document.FileName)
    subdoc_path = os.path.normpath(os.path.join(objdir, obj.sourceFile))

    if not (subdoc := exec_in_mainthread(open_subdoc, (subdoc_path,))):
        warn(
            "Object",
            name,
            (
                f"A2P - file '{subdoc_path}' not found"
                "- Downgrading to part::feature"
            ),
        )
        return _get_rends_from_partfeature(
            obj, name, material, mesher, **kwargs
        )

    debug("Object", name, f"A2P - Processing '{subdoc.Name}'")
    message("Object", name, f"A2P - Opening '{subdoc_path}'")

    a2p_subdocs.add(subdoc.Name)

    rends = []

    # Objects to render
    if not (source_part := getattr(obj, "sourcePart", "")):
        objects_to_render = top_objects(subdoc)  # All top objects
    else:
        objects_to_render = subdoc.getObjectsByLabel(source_part)

    if not objects_to_render:
        warn(
            "Object",
            name,
            (
                f"A2P - file '{subdoc_path}' - no object to render"
                "- Downgrading to part::feature"
            ),
        )
        return _get_rends_from_partfeature(
            obj, name, material, mesher, **kwargs
        )

    # Compute renderables
    for subobj in objects_to_render:
        subname = subobj.Name
        kwargs["ignore_unknown"] = True
        base_rends = get_renderables(
            subobj, subname, material, mesher, **kwargs
        )

        # Apply placement and set name
        for base_rend in base_rends:
            new_mesh = base_rend.mesh.copy()
            new_mesh.transformation.apply_placement(obj.Placement, left=True)
            new_mat = _get_material(base_rend, material)
            new_name = f"{name}_{base_rend.name}"
            new_color = base_rend.defcolor
            new_rend = Renderable(new_name, new_mesh, new_mat, new_color)
            rends.append(new_rend)

            # Copy texture files if needed
            if new_mat and new_mat.Proxy.has_textures():
                image_paths = (
                    t.getPropertyByName(i.image)
                    for t in new_mat.Proxy.get_textures()
                    for i in t.Proxy.get_images()
                )
                for org_path in image_paths:
                    dst_path = os.path.normpath(
                        os.path.join(
                            obj.Document.TransientDir,
                            os.path.basename(org_path),
                        )
                    )
                    debug(
                        "Object",
                        name,
                        f"A2P - Copying texture '{org_path}' -> '{dst_path}'",
                    )
                    # Copy to main doc transient dir (NB: replace if exists)
                    try:
                        shutil.copyfile(org_path, dst_path)
                    except shutil.SameFileError:
                        pass

    debug("Object", name, f"A2P - Leaving '{subdoc.Name}'")
    return [r for r in rends if r.mesh.count_facets]


def _get_rends_from_assembly3(obj, _, material, mesher, **kwargs):
    """Get renderables from an assembly3 object.

    Parameters:
    obj -- the container object
    name -- the name assigned to the container object for rendering
    material -- the material for the container object
    mesher -- a callable object which converts a shape into a mesh

    Returns:
    A list of renderables for this object
    """
    try:
        lnk, obj = obj, obj.LinkedObject
    except AttributeError:
        is_link = False
        prefix_name = obj.Name
    else:
        is_link = True
        prefix_name = f"{lnk.Name}_{obj.Name}"

    asm3_type = obj.Proxy
    if isinstance(asm3_type, (AsmConstraintGroup, AsmElementGroup)):
        debug("Object", obj.Label, "Skipping (element or constraint group)")
        return []

    elements = list(itertools.compress(obj.Group, obj.VisibilityList))
    renderables = []
    for element in elements:
        # Get children renderables
        base_rends = get_renderables(
            element, element.Name, material, mesher, **kwargs
        )
        if not base_rends:
            # Element is not renderable...
            continue

        # Apply object placement
        for base_rend in base_rends:
            new_mesh = base_rend.mesh.copy()
            new_mesh.transformation.apply_placement(obj.Placement, left=True)
            if is_link:
                new_mesh.transformation.apply_placement(
                    lnk.Placement, left=True
                )
            new_mat = _get_material(base_rend, material)
            new_name = f"{prefix_name}_{base_rend.name}"
            new_color = base_rend.defcolor
            new_rend = Renderable(new_name, new_mesh, new_mat, new_color)
            renderables.append(new_rend)

    return [r for r in renderables if r.mesh.count_facets]


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
    base_plc = obj.Placement
    elements = itertools.compress(obj.ElementList, obj.VisibilityList)

    for element in elements:
        if element.isDerivedFrom("App::LinkElement"):
            elem_object = element.LinkedObject
            elem_plc = element.LinkPlacement
        else:
            elem_object = element
            elem_plc = element.Placement
        elem_name = f"{name}_{element.Name}"

        # Compute rends and placements
        base_rends = get_renderables(
            elem_object, elem_name, material, mesher, **kwargs
        )
        linkedobject_plc_inverse = elem_object.Placement.inverse()
        for base_rend in base_rends:
            new_mesh = base_rend.mesh.copy()
            if not getattr(obj, "LinkTransform", False):
                new_mesh.transformation.apply_placement(
                    linkedobject_plc_inverse
                )
            new_mesh.transformation.apply_placement(base_plc)
            new_mesh.transformation.apply_placement(elem_plc)
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
    name -- the name assigned to the Link object for rendering
    material -- the material for the Link object
    mesher -- a callable object which converts a shape into a mesh

    Returns:
    A list of renderables for the object
    """
    linkedobj = obj.LinkedObject
    base_rends = get_renderables(linkedobj, name, material, mesher, **kwargs)
    link_plc = obj.LinkPlacement
    linkedobj_plc_inverse = linkedobj.Placement.inverse()

    def new_rend(base_rend):
        new_name = f"{name}_{base_rend.name}"
        new_mesh = base_rend.mesh.copy()
        new_mat = _get_material(base_rend, material)
        new_color = _get_shapecolor(
            obj, kwargs.get("transparency_boost", 0), base_rend.defcolor
        )
        if not obj.LinkTransform:
            new_mesh.transformation.apply_placement(
                linkedobj_plc_inverse, left=True
            )
        new_mesh.transformation.apply_placement(link_plc, left=True)
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
        color = _get_shapecolor(obj, kwargs.get("transparency_boost", 0))
        uvprojection = kwargs.get("uvprojection")
        return [
            Renderable(
                name,
                mesher(
                    shape=obj.Shape,
                    compute_uvmap=_needs_uvmap(material),
                    uvmap_projection=uvprojection,
                    name=name,
                    label=obj.Label,
                ),
                material,
                color,
            )
        ]

    base_rends = get_renderables(base, base.Name, material, mesher, **kwargs)
    obj_plc_matrix = obj.Placement.toMatrix()
    base_inv_plc_matrix = base.Placement.inverse().toMatrix()
    placements = (
        itertools.compress(placement_list, visibility_list)
        if visibility_list
        else obj.PlacementList
    )

    def new_rend(enum_plc, base_rend):
        counter, plc = enum_plc
        new_mesh = base_rend.mesh.copy()
        if not obj.LinkTransform:
            new_mesh.transformation.apply_placement(base_inv_plc_matrix)
        new_mesh.transformation.apply_placement(plc.toMatrix())
        new_mesh.transformation.apply_placement(obj_plc_matrix)
        subname = f"{name}_{base_rend.name}_{counter}"
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

    # There are 2 types of Arch Windows:
    # - WindowParts-based
    # - Type-base
    # See _ViewProviderWindow.colorize in ArchWindow.py

    if window_parts:
        # WindowParts-based window
        subnames = window_parts[0::5]  # Names every 5th item...
        names = [f"{name}_{s.replace(' ', '_')}" for s in subnames]
        labels = [f"{obj.Label}_{s.replace(' ', '_')}" for s in subnames]

        # Subobjects colors
        transparency_boost = kwargs.get("transparency_boost", 0)
        faces_len = [len(s.Faces) for s in obj.Shape.Solids]
        if obj.ViewObject is not None:  # Gui is up
            colors = [
                _boost_tp(
                    RGB.from_fcd_rgba(obj.ViewObject.DiffuseColor[i]),
                    transparency_boost,
                )
                for i in itertools.accumulate([0] + faces_len[:-1])
            ]
        else:
            colors = [WHITE] * len(subnames)

        # Subobjects materials
        if material is not None and is_multimat(material):
            mats_dict = dict(zip(material.Names, material.Materials))
            mats = [mats_dict.get(s) for s in subnames]
            needs_uvmap = [_needs_uvmap(m) for m in mats]
            if [m for m in mats if not m]:
                msg = translate(
                    "Render", "Incomplete multimaterial (missing {m})"
                )
                missing_mats = ", ".join(set(subnames) - mats_dict.keys())
                warn("Window", obj.Label, msg.format(m=missing_mats))
        else:
            mats = [material] * len(subnames)
            needs_uvmap = [False] * len(subnames)

        # Subobjects meshes
        uvprojection = kwargs.get("uvprojection")
        meshes = [
            mesher(
                shape=s,
                compute_uvmap=n,
                uvmap_projection=uvprojection,
                name=n2,
                label=l,
            )
            for s, n, n2, l in zip(
                obj.Shape.childShapes(), needs_uvmap, names, labels
            )
        ]

        # Build renderables (WindowParts-based)
        return [Renderable(*r) for r in zip(names, meshes, mats, colors)]

    # Type-based
    # Components are given by obj.Base (which should be an App::Part)
    rends = get_renderables(obj.Base, name, material, mesher, **kwargs)

    # Adjust placements
    def _adjust(rend, origin, upper_material):
        """Reposition renderable to origin and set its material."""
        origin_matrix = origin.toMatrix()
        new_mesh = rend.mesh.copy()
        new_mesh.transformation.apply_placement(origin_matrix, left=True)
        new_mat = _get_material(rend, upper_material)
        new_color = rend.defcolor
        return Renderable(rend.name, new_mesh, new_mat, new_color)

    origin = obj.Placement
    rends = [_adjust(r, origin, material) for r in rends]

    # Adjust colors
    transparency_boost = kwargs.get("transparency_boost", 0)
    faces_len = [len(s.Faces) for s in obj.Shape.Solids]
    if obj.ViewObject is not None:  # Gui is up
        colors = [
            _boost_tp(
                RGB.from_fcd_rgba(obj.ViewObject.DiffuseColor[i]),
                transparency_boost,
            )
            for i in itertools.accumulate([0] + faces_len[:-1])
        ]
    else:
        colors = [WHITE] * len(rends)

    for i, rend in enumerate(rends):
        rends[i] = Renderable(rend.name, rend.mesh, rend.material, colors[i])

    return rends


def _get_rends_from_wall(obj, name, material, mesher, **kwargs):
    """Get renderables from a Wall object (from Arch workbench).

    Parameters:
        obj -- the Wall object
        name -- the name assigned to the Wall object for rendering
        material -- the material for the Wall object (should be a
                    multimaterial)
        mesher -- a callable which converts a shape into a mesh

    Returns:
        A list of renderables for the Wall object
    """
    if material is None or not is_multimat(material):
        # No multimaterial: handle wall as a plain Part::Feature
        rends = _get_rends_from_partfeature(
            obj, name, material, mesher, **kwargs
        )
    else:
        # Multimaterial case...

        shapes = obj.Shape.childShapes()

        # Subobjects names
        names = [f"{name}_{i}" for i in range(len(shapes))]
        labels = [f"{obj.Label}_{i}" for i in range(len(shapes))]

        # Subobjects materials
        materials = material.Materials
        needs_uvmap = [_needs_uvmap(m) for m in materials]

        # Subobjects meshes
        uvprojection = kwargs.get("uvprojection")
        meshes = [
            mesher(
                shape=s,
                compute_uvmap=n,
                uvmap_projection=uvprojection,
                name=n2,
                label=l,
            )
            for s, n, n2, l in zip(shapes, needs_uvmap, names, labels)
        ]

        # Subobjects colors
        tp_boost = kwargs.get("transparency_boost", 0)
        colors = [
            _boost_tp(RGB([*m.Color[0:3], 1.0 - m.Transparency]), tp_boost)
            for m in materials
        ]

        # Build renderables
        rends = [Renderable(*r) for r in zip(names, meshes, materials, colors)]

    # Process Components if any
    components = {
        o
        for o in obj.InListRecursive
        if hasattr(o, "Hosts") and obj in o.Hosts
    }
    if components:
        # This code is copy/paste from 'part' and there should be
        # a merge, one day...
        def _adjust(rend, origin, upper_material):
            """Reposition renderable to origin and set its material."""
            origin_matrix = origin.toMatrix()
            new_mesh = rend.mesh.copy()
            new_mesh.transformation.apply_placement(origin_matrix, left=True)
            new_mat = _get_material(rend, upper_material)
            new_color = rend.defcolor
            return Renderable(rend.name, new_mesh, new_mat, new_color)

        origin = obj.Placement

        component_rends = []
        for order, subobj in enumerate(components):
            subname = f"{name}#{subobj.Name}_{order}"
            if getattr(
                subobj, "Visibility", True
            ):  # Add subobj only if visible
                kwargs["ignore_unknown"] = (
                    True  # Force ignore unknown materials
                )
                component_rends += get_renderables(
                    subobj, subname, material, mesher, **kwargs
                )

        component_rends = [
            _adjust(r, origin, material) for r in component_rends
        ]

        rends += component_rends

    return rends


def _get_rends_from_part(obj, name, material, mesher, **kwargs):
    """Get renderables from an App::Part object.

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
        new_mesh.transformation.apply_placement(origin_matrix, left=True)
        new_mat = _get_material(rend, upper_material)
        new_color = rend.defcolor
        return Renderable(rend.name, new_mesh, new_mat, new_color)

    origin = obj.Placement

    rends = []
    for subobj in obj.Group:
        subname = f"{name}#{subobj.Name}"
        if getattr(subobj, "Visibility", True):  # Add subobj only if visible
            kwargs["ignore_unknown"] = True  # Force ignore unknown materials
            rends += get_renderables(
                subobj, subname, material, mesher, **kwargs
            )

    rends = [_adjust(r, origin, material) for r in rends]

    return rends


def _get_rends_from_partfeature(obj, name, material, mesher, **kwargs):
    """Get renderables from a Part::Feature object.

    Parameters:
        obj -- the Part::Feature object
        name -- the name assigned to the object for rendering
        material -- the material for the object
        mesher -- a callable object which converts a shape into a mesh

    Returns:
        A list of renderables for the Part object
    """
    try:
        colors = obj.ViewObject.DiffuseColor
    except AttributeError:
        colors = []

    uvprojection = kwargs.get("uvprojection")

    # Handle multimaterial
    if is_multimat(material):
        # Try to find a matching material
        mats_dict = dict(zip(material.Names, material.Materials))
        try:
            mat = mats_dict[obj.Label]
        except KeyError:
            pass
        else:
            material = mat
            print("Found", material.Label)

    if len(colors) <= 1:
        # Monocolor: Treat shape as a whole
        transparency_boost = int(kwargs.get("transparency_boost", 0))
        color = _get_shapecolor(obj, transparency_boost)
        renderables = [
            Renderable(
                name,
                mesher(
                    shape=obj.Shape,
                    compute_uvmap=_needs_uvmap(material),
                    uvmap_projection=uvprojection,
                    name=name,
                    label=obj.Label,
                ),
                material,
                color,
            )
        ]
    else:
        # Multicolor: Process face by face
        faces = obj.Shape.Faces
        nfaces = len(faces)
        names = [f"{name}_face{i}" for i in range(nfaces)]
        labels = [f"{obj.Label}_face{i}" for i in range(nfaces)]
        meshes = [
            mesher(
                shape=f,
                compute_uvmap=_needs_uvmap(material),
                uvmap_projection=uvprojection,
                name=n,
                label=l,
            )
            for f, n, l in zip(faces, names, labels)
        ]
        materials = [material] * nfaces
        colors = map(RGB.from_fcd_rgba, colors)
        renderables = [
            Renderable(*i) for i in zip(names, meshes, materials, colors)
        ]

    return renderables


def _get_rends_from_meshfeature(obj, name, material, mesher, **kwargs):
    """Get renderables from a Mesh::Feature object.

    Parameters:
        obj -- the Mesh::Feature object
        name -- the name assigned to the object for rendering
        material -- the material for the object
        mesher -- a callable object which converts a shape into a mesh

    Returns:
        A list of renderables for the Mesh::Feature object
    """
    compute_uvmap = material and material.Proxy.has_textures()
    uvprojection = kwargs.get("uvprojection", None)
    mesh = mesher(
        shape=obj,
        compute_uvmap=compute_uvmap,
        uvmap_projection=uvprojection,
        is_already_a_mesh=True,
        name=name,
        label=obj.Label,
    )
    color = kwargs["meshcolor"]
    renderables = [Renderable(name, mesh, material, color)]
    return renderables


# ===========================================================================
#                           Helpers
# ===========================================================================


def _get_material(base_renderable, upper_material):
    """Get material from a base renderable and an upper material."""
    upper_mat_is_multimat = is_multimat(upper_material)

    return (
        base_renderable.material
        if (upper_material is None or upper_mat_is_multimat)
        else upper_material
    )


def _get_shapecolor(obj, transparency_boost, default_color=None):
    """Get shape color (including transparency) from an object."""
    default_color = default_color or WHITE

    # Is there a view object? (console mode, for instance)
    if (vobj := obj.ViewObject) is None:
        return default_color

    # Overridden color for faces?
    try:
        elem_colors = vobj.getElementColors()
        face_color = elem_colors["Face"]
    except (AttributeError, KeyError):
        # Shape color
        try:
            shapecolor = vobj.ShapeColor[0:3]  # Only rgb, not alpha
            transparency = vobj.Transparency  # Alpha is given by transparency
        except AttributeError:
            color = default_color
        else:
            color = RGB.from_fcd_rgba(shapecolor, transparency)
    else:
        # Face color
        color = RGB.from_fcd_rgba(face_color)

    result = _boost_tp(color, transparency_boost)
    return result


def _boost_tp(color, boost_factor):
    """Get a color with boosted transparency."""
    transparency = 1.0 - color.alpha
    transparency = math.pow(transparency, 1 / (boost_factor + 1))
    res = color
    res.alpha = 1.0 - transparency
    return res


def _needs_uvmap(material):
    """Check whether this material needs a UV map.

    NB: An UV map is needed if the material contains textures.
    """
    if material is None:
        return False

    proxy = material.Proxy
    try:
        return proxy.has_textures() or proxy.force_uvmap()
    except AttributeError:
        label = (
            "<No name>" if not hasattr(material, "Label") else material.Label
        )
        App.Console.PrintMessage(
            f"[Render][Objstrings] Material '{label}' ({proxy}) is not a "
            "Render Material and may not be used for rendering.\n"
        )
        return False


def clean_a2p():
    """Clean/close A2Plus intermediate objects."""

    def close_subdoc(*args):
        name, *_ = args
        try:
            App.closeDocument(name)
        except NameError:
            print(f"Unable to close '{name}'")

    while a2p_subdocs:
        name = a2p_subdocs.pop()
        exec_in_mainthread(close_subdoc, (name,))
