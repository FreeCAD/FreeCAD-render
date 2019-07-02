from __future__ import print_function
#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2019 Yorik van Havre <yorik@uncreated.net>              *
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

# Cycles renderer for FreeCAD

# This file can also be used as a template to add more rendering engines.
# You will need to make sure your file is named with a same name (case sensitive)
# That you will use everywhere to describe your renderer, ex: Appleseed or Povray


# A render engine module must contain the following functions:
#
#    writeCamera(camdata): returns a string containing an openInventor camera string in renderer format
#    writeObject(view): returns a string containing a RaytracingView object in renderer format
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


import tempfile
import FreeCAD
import os
import math
import re


def writeCamera(camdata):


    # this is where you create a piece of text in the format of
    # your renderer, that represents the camera.
    # camdata contains a string in OpenInventor format
    # ex:
    # #Inventor V2.1 ascii
    #
    #
    # PerspectiveCamera {
    #  viewportMapping ADJUST_CAMERA
    #  position 0 -1.3207401 0.82241058
    #  orientation 0.99999666 0 0  0.26732138
    #  nearDistance 1.6108983
    #  farDistance 6611.4492
    #  aspectRatio 1
    #  focalDistance 5
    #  heightAngle 0.78539819
    #
    # }
    #
    # or (ortho camera):
    #
    # #Inventor V2.1 ascii
    #
    #
    # OrthographicCamera {
    #  viewportMapping ADJUST_CAMERA
    #  position 0 0 1
    #  orientation 0 0 1  0
    #  nearDistance 0.99900001
    #  farDistance 1.001
    #  aspectRatio 1
    #  focalDistance 5
    #  height 4.1421356
    #
    # }

    if not camdata:
        return ""
    camdata = camdata.split("\n")
    pos = [float(p) for p in camdata[5].split()[-3:]]
    pos = FreeCAD.Vector(pos)
    rot = [float(p) for p in camdata[6].split()[-4:]]
    rot = FreeCAD.Rotation(FreeCAD.Vector(rot[0],rot[1],rot[2]),math.degrees(rot[3]))
    pos = str(pos.x)+" "+str(pos.y)+" "+str(pos.z)
    rot = str(math.degrees(rot.Angle))+" "+str(rot.Axis.x)+" "+str(rot.Axis.y)+" "+str(rot.Axis.z)
    #print("cam:",pos," : ",rot)
    # cam rotation is angle(deg) axisx axisy axisz
    # scale needs to have z inverted to behave like a decent camera. No idea what they have been doing at blender :)
    cam = """    <transform rotate="%s" translate="%s" scale="1 1 -1">
        <camera type="perspective" />
    </transform>""" % (rot, pos)

    return cam


def writeObject(viewobj):


    # This is where you write your object/view in the format of your
    # renderer. "obj" is the real 3D object handled by this project, not
    # the project itself. This is your only opportunity
    # to write all the data needed by your object (geometry, materials, etc)
    # so make sure you include everything that is needed

    if not viewobj.Source:
        return ""
    obj = viewobj.Source
    objname = viewobj.Name
    color = None
    alpha = None
    mat = None
    objdata = ""

    # shader

    if viewobj.Material:
        mat = viewobj.Material
    else:
        if "Material" in obj.PropertiesList:
            if obj.Material:
                mat = obj.Material
    if mat:
        if "Material" in mat.PropertiesList:
            if "DiffuseColor" in mat.Material:
                color = mat.Material["DiffuseColor"].strip("(").strip(")").split(",")
                color = str(color[0])+", "+str(color[1])+", "+str(color[2])
            if "Transparency" in mat.Material:
                if float(mat.Material["Transparency"]) > 0:
                    alpha = 1.0-float(mat.Material["Transparency"])
                else:
                    alpha = 1.0
    if obj.ViewObject:
        if not color:
            if hasattr(obj.ViewObject,"ShapeColor"):
                color = obj.ViewObject.ShapeColor[:3]
                color = str(color[0])+", "+str(color[1])+", "+str(color[2])
        if not alpha:
            if hasattr(obj.ViewObject,"Transparency"):
                if obj.ViewObject.Transparency > 0:
                    alpha = 1.0-(float(obj.ViewObject.Transparency)/100.0)
    if not color:
        color = "1.0, 1.0, 1.0"
    if not alpha:
        alpha = 1.0
    bsdfname = objname + "_bsdf"
    matname = objname + "_mat"
    print(matname,alpha)
    objdata += "    <shader name=\""+matname+"\">\n"
    objdata += "        <diffuse_bsdf name=\""+bsdfname+"\" color=\""+color+"\" />\n"
    if alpha < 1:
        objdata += "        <transparent_bsdf name=\""+bsdfname+"_trans\" color=\"1.0, 1.0, 1.0\" />\n"
        objdata += "        <mix_closure name=\""+bsdfname+"_mix\" fac=\""+str(alpha)+"\" />\n"
        objdata += "        <connect from=\""+bsdfname+"_trans bsdf\" to=\""+bsdfname+"_mix closure1\" />\n"
        objdata += "        <connect from=\""+bsdfname+" bsdf\" to=\""+bsdfname+"_mix closure2\" />\n"
        objdata += "        <connect from=\""+bsdfname+"_mix closure\" to=\"output surface\" />\n"
    else:
        objdata += "        <connect from=\""+bsdfname+" bsdf\" to=\"output surface\" />\n"
    objdata += "    </shader>\n\n"
    
    # mesh

    m = None
    if hasattr(obj,"Group"):
        import Draft,Part,MeshPart
        shps = [o.Shape for o in Draft.getGroupContents(obj) if hasattr(o,"Shape")]
        m = MeshPart.meshFromShape(Shape=Part.makeCompound(shps), 
                                   LinearDeflection=0.1, 
                                   AngularDeflection=0.523599, 
                                   Relative=False)
    elif obj.isDerivedFrom("Part::Feature"):
        import MeshPart
        m = MeshPart.meshFromShape(Shape=obj.Shape, 
                                   LinearDeflection=0.1, 
                                   AngularDeflection=0.523599, 
                                   Relative=False)
    elif obj.isDerivedFrom("Mesh::Feature"):
        m = obj.Mesh
    if not m:
        return ""
    P = ""
    nverts = ""
    verts = ""
    for v in m.Topology[0]:
        P += str(v.x) + " " + str(v.y) + " " + str(v.z) + "  "
    for f in m.Topology[1]:
        nverts += "3 "
        verts += str(f[0]) + " " + str(f[1]) + " " + str(f[2]) + "  "
    P = P.strip()
    nverts = nverts.strip()
    verts = verts.strip()
    objdata += "    <state shader=\""+matname+"\">\n"
    objdata += "        <mesh P=\""+P+"\" nverts=\""+nverts+"\" verts=\""+verts+"\" />\n"
    objdata += "    </state>\n\\n"

    return objdata


def render(project,prefix,external,output,width,height):


    # here you trigger a render by firing the renderer
    # executable and pasing it the needed arguments, and
    # the file it needs to render

    p = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    prefix = p.GetString("Prefix","")
    if prefix:
        prefix += " "
    rpath = p.GetString("CyclesPath","")
    args = p.GetString("CyclesParameters","")
    args += " --output "+output
    if not external: 
        args += " --background"
    if not rpath:
        FreeCAD.Console.PrintError("Unable to locate renderer executable. Please set the correct path in Edit -> Preferences -> Render")
        return
    args += " --width "+str(width)
    args += " --height "+str(height)
    os.system(prefix+rpath+" "+args+" "+project.PageResult)
    return output


