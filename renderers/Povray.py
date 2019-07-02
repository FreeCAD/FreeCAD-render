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

# Povray renderer for FreeCAD

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


import FreeCAD
import math
import re


def writeCamera(pos,rot,up,target):

    # this is where you create a piece of text in the format of
    # your renderer, that represents the camera.

    pos = str(pos.x) + "," + str(pos.z) + "," + str(pos.y)
    target = str(target.x) + "," + str(target.z) +"," + str(target.y)
    up = str(up.x) + ","  + str(up.z) + "," + str(up.y)

    cam =  "// declares position and view direction\n"
    cam += "// Generated by FreeCAD (http://www.freecadweb.org/)\n"
    cam += "#declare cam_location =  <" + pos + ">;\n"
    cam += "#declare cam_look_at  = <" + target + ">;\n"
    cam += "#declare cam_sky      = <" + up + ">;\n"
    cam += "#declare cam_angle    = 45;\n"
    cam += "camera {\n"
    cam += "  location  cam_location\n"
    cam += "  look_at   cam_look_at\n"
    cam += "  sky       cam_sky\n"
    cam += "  angle     cam_angle\n"
    cam += "  right x*800/600\n"
    cam += "}\n"

    return cam


def writeObject(viewobj,mesh,color,alpha):

    # This is where you write your object/view in the format of your
    # renderer. "obj" is the real 3D object handled by this project, not
    # the project itself. This is your only opportunity
    # to write all the data needed by your object (geometry, materials, etc)
    # so make sure you include everything that is needed

    objname = viewobj.Name
    
    color = str(color[0])+","+str(color[1])+","+str(color[2])

    objdef = ""
    objdef += "#declare " + objname + " = mesh2{\n"
    objdef += "  vertex_vectors {\n"
    objdef += "    " + str(len(mesh.Topology[0])) + ",\n"
    for p in mesh.Topology[0]:
        objdef += "    <" + str(p.x) + "," + str(p.z) + "," + str(p.y) + ">,\n"
    objdef += "  }\n"
    objdef += "  normal_vectors {\n"
    objdef += "    " + str(len(mesh.Topology[0])) + ",\n"
    for p in mesh.getPointNormals():
        objdef += "    <" + str(p.x) + "," + str(p.z) + "," + str(p.y) + ">,\n"
    objdef += "  }\n"
    objdef += "  face_indices {\n"
    objdef += "    " + str(len(mesh.Topology[1])) + ",\n"
    for t in mesh.Topology[1]:
        objdef += "    <" + str(t[0]) + "," + str(t[1]) + "," + str(t[2]) + ">,\n"
    objdef += "  }\n"
    objdef += "}\n"
    
    objdef += "// instance to render\n"
    objdef += "object {" + objname + "\n"
    objdef += "  texture {\n"
    objdef += "    pigment {\n"
    objdef += "      color rgb <" + color + ">\n"
    objdef += "    }\n"
    objdef += "    finish {StdFinish }\n"
    objdef += "  }\n"
    objdef += "}\n"

    return objdef


def render(project,prefix,external,output,width,height):

    # here you trigger a render by firing the renderer
    # executable and pasing it the needed arguments, and
    # the file it needs to render

    p = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    prefix = p.GetString("Prefix","")
    if prefix:
        prefix += " "
    rpath = p.GetString("PovRayPath","")
    args = p.GetString("PovRayParameters","")
    if not rpath:
        FreeCAD.Console.PrintError("Unable to locate renderer executable. Please set the correct path in Edit -> Preferences -> Render")
        return
    if args:
        args += " "
    if "+W" in args:
        args = re.sub("\+W[0-9]+","+W"+str(width),args)
    else:
        args = args + "+W"+str(width)+" "
    if "+H" in args:
        args = re.sub("\+H[0-9]+","+H"+str(height),args)
    else:
        args = args + "+H"+str(height)+" "
    import os
    os.system(prefix+rpath+" "+args+project.PageResult)
    imgname = os.path.splitext(project.PageResult)[0]+".png"
    
    return imgname


