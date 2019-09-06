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
#    writeCamera(por,rot,up,target): returns a string containing an openInventor camera string in renderer format
#    writeObject(view,mesh,color,alpha): returns a string containing a RaytracingView object in renderer format
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


def writeCamera(pos,rot,up,target):

    # this is where you create a piece of text in the format of
    # your renderer, that represents the camera.

    pos = str(pos.x)+" "+str(pos.y)+" "+str(pos.z)
    rot = str(math.degrees(rot.Angle))+" "+str(rot.Axis.x)+" "+str(rot.Axis.y)+" "+str(rot.Axis.z)

    # cam rotation is angle(deg) axisx axisy axisz
    # scale needs to have z inverted to behave like a decent camera. No idea what they have been doing at blender :)
    cam = """    <transform rotate="%s" translate="%s" scale="1 1 -1">
        <camera type="perspective" />
    </transform>""" % (rot, pos)

    return cam


def writeObject(viewobj,mesh,color,alpha):

    # This is where you write your object/view in the format of your
    # renderer. "obj" is the real 3D object handled by this project, not
    # the project itself. This is your only opportunity
    # to write all the data needed by your object (geometry, materials, etc)
    # so make sure you include everything that is needed

    bsdfname = viewobj.Name + "_bsdf"
    matname = viewobj.Name + "_mat"
    transname = viewobj.Name + "_trans"
    mixname = viewobj.Name + "_mix"

    # format color data

    color = str(color[0])+", "+str(color[1])+", "+str(color[2])
    
    # write shader
    
    objdef =      "    <shader name=\""+matname+"\">\n"
    objdef +=     "        <diffuse_bsdf name=\""+bsdfname+"\" color=\""+color+"\" />\n"
    if alpha < 1:
        objdef += "        <transparent_bsdf name=\""+transname+"_trans\" color=\"1.0, 1.0, 1.0\" />\n"
        objdef += "        <mix_closure name=\""+mixname+"\" fac=\""+str(alpha)+"\" />\n"
        objdef += "        <connect from=\""+transname+" bsdf\" to=\""+mixname+" closure1\" />\n"
        objdef += "        <connect from=\""+bsdfname+" bsdf\" to=\""+mixname+" closure2\" />\n"
        objdef += "        <connect from=\""+mixname+" closure\" to=\"output surface\" />\n"
    else:
        objdef += "        <connect from=\""+bsdfname+" bsdf\" to=\"output surface\" />\n"
    objdef +=     "    </shader>\n\n"
    
    # write mesh

    P = ""
    nverts = ""
    verts = ""
    for v in mesh.Topology[0]:
        P += str(v.x) + " " + str(v.y) + " " + str(v.z) + "  "
    for f in mesh.Topology[1]:
        nverts += "3 "
        verts += str(f[0]) + " " + str(f[1]) + " " + str(f[2]) + "  "
    P = P.strip()
    nverts = nverts.strip()
    verts = verts.strip()
    objdef += "    <state shader=\""+matname+"\">\n"
    objdef += "        <mesh P=\""+P+"\" nverts=\""+nverts+"\" verts=\""+verts+"\" />\n"
    objdef += "    </state>\n\\n"

    return objdef


def render(project,prefix,external,output,width,height):

    # here you trigger a render by firing the renderer
    # executable and passing it the needed arguments, and
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
    os.system('"' + prefix+rpath+'" '+args+" "+project.PageResult)

    return output


