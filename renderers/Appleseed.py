from __future__ import print_function
#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

# Appleseed renderer for FreeCAD

# This file can also be used as a template to add more rendering engines.
# You will need to make sure your file is named with a same name (case sensitive)
# That you will use everywhere to describe your renderer, ex: Appleseed or Povray


# A render engine module must contain the following functions:
#
#    writeCamera(por,rot,up,target): returns a string containing an openInventor camera string in renderer format
#    writeObject(name,mesh,material): returns a string containing a RaytracingView object in renderer format
#    render(project,prefix,external,output,width,height): renders the given project, external means
#                                                         if the user wishes to open the render file
#                                                         in an external application/editor or not. If this
#                                                         is not supported by your renderer, you can simply
#                                                         ignore it
#
# Additionally, you might need/want to add:
#
#    Preference page items, that can be used in your functions below
#    An icon under the name Renderer.svg (where Renderer is the name of your Renderer


# NOTE: The coordinate system in appleseed uses a different coordinate system.
# Y and Z are switched and Z is inverted

import tempfile
import FreeCAD
import os
import math
import re


def writeCamera(pos,rot,up,target):

    # this is where you create a piece of text in the format of
    # your renderer, that represents the camera.

    target = str(target.x)+" "+str(target.z)+" "+str(-target.y)
    up = str(up.x)+" "+str(up.z)+" "+str(-up.y)
    pos = str(pos.x)+" "+str(pos.z)+" "+str(-pos.y)

    cam = """
        <camera name="camera" model="thinlens_camera">
            <parameter name="film_width" value="0.032" />
            <parameter name="aspect_ratio" value="1.7" />
            <parameter name="horizontal_fov" value="80" />
            <parameter name="shutter_open_time" value="0" />
            <parameter name="shutter_close_time" value="1" />
            <transform>
                <look_at origin="%s" target="%s" up="%s" />
            </transform>
        </camera>""" % (pos, target, up)

    return cam

def writeTexture(name, filename, linear = True):
    if filename is not None:
        texdef = """
            <texture name="%s" model="disk_texture_2d">
                <parameter name="color_space" value="%s" />
                <parameter name="filename" value="%s" />
            </texture>
            <texture_instance name="%s" texture="%s">
            </texture_instance>""" % (name, "linear_rgb" if linear else "srgb", filename, name + "_inst", name)
        return texdef
    return ""

#almost any parameter can be overriden by a texture
#This function writes the info in two parts one that needs to be prepended
#the other one will be written as the parameter in the material
def processFloatParameter(name, material, altfn, paramName):
    texdef = ""
    paramdef = None
    filename = material.getFilename(paramName + "_Texture")
    if filename is not None:
        texname = name + "_" + paramName
        texdef = writeTexture(texname, filename)
        paramdef = texname + "_inst"
    else:
        paramdef = altfn(paramName)
    return (texdef, paramdef)

def processColorParameter(name, material, paramName, alpha = "1.0"):
    texdef = ""
    paramdef = None
    filename = material.getFilename(paramName + "_Texture")
    if filename is not None:
        texname = name + "_" + paramName
        texdef = writeTexture(texname, filename)
        paramdef = texname + "_inst"
    else:
        colorName = name + "_" + paramName
        texdef = writeColor(colorName, material.getColorsSpace(paramName), alpha)
        if texdef != "":
            paramdef = colorName
    return (texdef, paramdef)

def writeColor(name, color, alpha):
    coldef = ""
    if color is not None and alpha is not None:
        coldef = """
                <color name="%s">
                    <parameter name="color_space" value="linear_rgb" />
                    <parameter name="multiplier" value="1.0" />
                    <parameter name="wavelength_range" value="400.0 700.0" />
                    <values>
                        %s
                    </values>
                    <alpha>
                        %s
                    </alpha>
                </color>\n""" % (name, color, alpha)
    return coldef

def writeParameter(name, param):
    if param is not None:
        return '                <parameter name="%s" value="%s" />\n' % (name, param)
    else:
        return ""

def writeLambertianMaterial(name, material):
    colorname = name + "_color"
    bsdfname = name + "_bsdf"

    reflectance = processColorParameter(name, material, "DiffuseColor", material.getPercentFloatInverted("Transparency"))

    matdef = reflectance[0]
    matdef += """
            <bsdf name="%s" model="lambertian_brdf">
                <parameter name="reflectance" value="%s" />
            </bsdf>
            <material name="%s" model="generic_material">
                <parameter name="bsdf" value="%s" />
                <parameter name="bump_amplitude" value="1.0" />
                <parameter name="bump_offset" value="2.0" />
                <parameter name="displacement_method" value="bump" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="shade_alpha_cutouts" value="false" />
            </material>""" % (bsdfname, reflectance[1], name, bsdfname)
    return matdef

def writePrincipledMaterial(name, material):
    colorname = name + "_color"
    bsdfname = name + "_bsdf"

    baseColor = processColorParameter(name, material, "DiffuseColor", material.getPercentFloatInverted("Transparency"))
    subsurface = processFloatParameter(name, material, material.getFloat, "Principled_Subsurface")
    metallic = processFloatParameter(name, material, material.getFloat, "Principled_Metallic")
    specular = processFloatParameter(name, material, material.getFloat, "Principled_Specular")
    specular_tint = processFloatParameter(name, material, material.getFloat, "Principled_SpecularTint")
    anisotropic = processFloatParameter(name, material, material.getFloat, "Principled_Anisotropic")
    roughness = processFloatParameter(name, material, material.getFloat, "Principled_Roughness")
    sheen = processFloatParameter(name, material, material.getFloat, "Principled_Sheen")
    sheen_tint = processFloatParameter(name, material, material.getFloat, "Principled_SheenTint")
    clearcoat = processFloatParameter(name, material, material.getFloat, "Principled_Clearcoat")
    clearcoat_gloss = processFloatParameter(name, material, material.getFloatInverted, "Principled_ClearcoatRoughness")

    matdef = baseColor[0]
    matdef += subsurface[0]
    matdef += metallic[0]
    matdef += specular[0]
    matdef += specular_tint[0]
    matdef += anisotropic[0]
    matdef += roughness[0]
    matdef += sheen[0]
    matdef += sheen_tint[0]
    matdef += clearcoat[0]
    matdef += clearcoat_gloss[0]

    matdef += ('            <bsdf name="' + bsdfname +'" model="disney_brdf">\n'
               + writeParameter("base_color", baseColor[1])
               + writeParameter("subsurface", subsurface[1])
               + writeParameter("metallic", metallic[1])
               + writeParameter("specular", specular[1])
               + writeParameter("specular_tint", specular_tint[1])
               + writeParameter("anisotropic", anisotropic[1])
               + writeParameter("roughness", roughness[1])
               + writeParameter("sheen", sheen[1])
               + writeParameter("sheen_tint", sheen_tint[1])
               + writeParameter("clearcoat", clearcoat[1])
               + writeParameter("clearcoat_gloss", clearcoat_gloss[1])
               +'            </bsdf>\n')

    matdef += """            <material name="%s" model="generic_material">
                <parameter name="bsdf" value="%s" />
                <parameter name="bump_amplitude" value="1.0" />
                <parameter name="bump_offset" value="2.0" />
                <parameter name="displacement_method" value="bump" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="shade_alpha_cutouts" value="false" />
            </material>""" % (name, bsdfname)
    return matdef

def writeGlassMaterial(name, material):
    surfacetransmittance = name + "_surftrans"
    reflectiontint = name + "_reflecttint" if material.check("Appleseed_Glass_ReflectionTint") else None
    refractiontint = name + "_refracttint" if material.check("Appleseed_Glass_RefractionTint") else None
    voltransmittance = name + "_voltrans"if material.check("Appleseed_Glass_VolumeTransmittance") else None
    volabsorption = name + "_volabs" if material.check("Appleseed_Glass_VolumeAbsorption") else None

    volparam = material.getString("Appleseed_Glass_VolumeParameterization")
    if volparam is None:
        volparam = "transmittance"

    bsdfname = name + "_bsdf"

    surfacetransmittance = processColorParameter(name, material, "Appleseed_Glass_SurfaceTransmittance")
    reflectiontint = processColorParameter(name, material, "Appleseed_Glass_ReflectionTint")
    refractiontint = processColorParameter(name, material, "Appleseed_Glass_RefractionTint")
    voltransmittance = processColorParameter(name, material, "Appleseed_Glass_VolumeTransmittance")
    volabsorption = processColorParameter(name, material, "Appleseed_Glass_VolumeAbsorption")

    roughness = processFloatParameter(name, material, material.getFloat, "Appleseed_Glass_Roughness")
    anisotropy = processFloatParameter(name, material, material.getFloat, "Appleseed_Glass_Anisotropy")
    volume_transmittance_distance = processFloatParameter(name, material, material.getFloat, "Appleseed_Glass_VolumeTransmittanceDistance")

    matdef = surfacetransmittance[0]
    matdef += reflectiontint[0]
    matdef += refractiontint[0]
    matdef += voltransmittance[0]
    matdef += volabsorption[0]

    matdef += roughness[0]
    matdef += anisotropy[0]
    matdef += volume_transmittance_distance[0]

    matdef += ('            <bsdf name="' + bsdfname +'" model="glass_bsdf">\n'
            + writeParameter("mdf", "ggx")        #This is for older versions of appleseed
            + writeParameter("surface_transmittance", surfacetransmittance[1])
            + writeParameter("reflection_tint", reflectiontint[1])
            + writeParameter("refraction_tint", refractiontint[1])
            + writeParameter("volume_transmittance", voltransmittance[1])
            + writeParameter("volume_absorption", volabsorption[1])
            + writeParameter("ior", material.getFloat("Appleseed_Glass_IOR"))
            + writeParameter("roughness", roughness[1])
            + writeParameter("anisotropy", anisotropy[1])
            + writeParameter("volume_parameterization", volparam)
            + writeParameter("volume_transmittance_distance", volume_transmittance_distance[1])
            + writeParameter("volume_density", material.getFloat("Appleseed_Glass_VolumeDensity"))
            + writeParameter("volume_scale", material.getFloat("Appleseed_Glass_VolumeScale"))
            + writeParameter("energy_compensation", material.getFloat("Appleseed_Glass_EnergyCompensation"))
            +'            </bsdf>\n')

    matdef += """            <material name="%s" model="generic_material">
                <parameter name="bsdf" value="%s" />
                <parameter name="bump_amplitude" value="1.0" />
                <parameter name="bump_offset" value="2.0" />
                <parameter name="displacement_method" value="bump" />
                <parameter name="normal_map_up" value="z" />
                <parameter name="shade_alpha_cutouts" value="false" />
            </material>""" % (name, bsdfname)
    return matdef

def writeOBJFile(name, mesh, material):
    objdef = "# Created by FreeCAD <http://www.freecadweb.org>\n"
    
    objdef += "o "+name+"\n"

    #write positions
    for v in mesh.Topology[0]:
        objdef += "v " + str(v[0]) + " " + str(v[1]) + " " + str(v[2]) + "\n"

    for facet in mesh.Facets:
        objdef += "vn " + str(facet.Normal[0]) + " " + str(facet.Normal[1]) + " " + str(facet.Normal[2]) + "\n"

    uvpresent = hasattr(material, "uvcoordinates") and material.uvcoordinates is not None
    if uvpresent:
        for texcoor in material.uvcoordinates:
            objdef += "vt %f %f\n" % (texcoor[0], texcoor[1])


    #write faces
    for i, facet in enumerate(mesh.Topology[1]):
            objdef += "f "
            objdef += "%s/%s/%s " % (facet[0]+1, (material.uvindices[i][0]+1 if uvpresent else ""), i+1)
            objdef += "%s/%s/%s " % (facet[1]+1, (material.uvindices[i][1]+1 if uvpresent else ""), i+1)
            objdef += "%s/%s/%s\n" % (facet[2]+1, (material.uvindices[i][2]+1 if uvpresent else ""), i+1)
    return objdef

def writeObject(name,mesh,material):

    # This is where you write your object/view in the format of your
    # renderer. "obj" is the real 3D object handled by this project, not
    # the project itself. This is your only opportunity
    # to write all the data needed by your object (geometry, materials, etc)
    # so make sure you include everything that is needed

    objname = name
    matname = objname + "_mat"

    import math
    tmpmesh = mesh.copy()
    tmpmesh.rotate(-math.pi/2, 0, 0)

    # write the mesh as an obj tempfile
    fd, meshfile = tempfile.mkstemp(suffix=".obj", prefix="_")
    with os.fdopen(fd, "w") as f:
        f.write(writeOBJFile(objname, tmpmesh, material))

    objfile = os.path.splitext(os.path.basename(meshfile))[0]

    materialtype = material.getString("Appleseed_Material")
    if materialtype is not None:
        materialtype = materialtype.lower()
    if materialtype == "glass":
        objdef = writeGlassMaterial(matname, material)
    elif materialtype == "principled":
        objdef = writePrincipledMaterial(matname, material)
    else:
        objdef = writeLambertianMaterial(matname, material)

    objdef += """
            <object name="%s" model="mesh_object">
                <parameter name="filename" value="%s" />
            </object>
            <object_instance name="%s.instance" object="%s">
                <assign_material slot="default" side="front" material="%s" />
                <assign_material slot="default" side="back" material="%s" />
            </object_instance>""" % (objfile, meshfile,
                                    objfile+"."+objname,
                                    objfile+"."+objname,
                                    matname, matname)
    return objdef

def render(project,prefix,external,output,width,height):

    # here you trigger a render by firing the renderer
    # executable and passing it the needed arguments, and
    # the file it needs to render

    # change image size in template
    f = open(project.PageResult,"r")
    t = f.read()
    f.close()
    res = re.findall("<parameter name=\"resolution.*?\/>",t)
    if res:
        t = t.replace(res[0],"<parameter name=\"resolution\" value=\""+str(width)+" "+str(height)+"\" />")
        fd, fp = tempfile.mkstemp(prefix=project.Name,suffix=os.path.splitext(project.Template)[-1])
        os.close(fd)
        f = open(fp,"w")
        f.write(t)
        f.close()
        project.PageResult = fp
        os.remove(fp)
        FreeCAD.ActiveDocument.recompute()

    p = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    if external:
        rpath = p.GetString("AppleseedStudioPath","")
        args = ""
    else:
        rpath = p.GetString("AppleseedCliPath","")
        args = p.GetString("AppleseedParameters","")
        if args:
            args += " "
        args += "--output "+output
    if not rpath:
        FreeCAD.Console.PrintError("Unable to locate renderer executable. Please set the correct path in Edit -> Preferences -> Render")
        return
    if args:
        args += " "
    os.system(prefix+rpath+" "+args+project.PageResult)
    return


