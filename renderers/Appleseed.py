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
#    writeCamera(camdata): returns a string containing an openInventor camera string in renderer format
#    writeObject(view): returns a string containing a RaytracingView object in renderer format
#    render(project,external=True): renders the given project, external means if the user wishes to open
#                                   the render file in an external application/editor or not. If this
#                                   is not supported by your renderer, you can simply ignore it
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
    # your renderer, that represents the camera. You can use the contents
    # of obj.Camera, which contain a string in OpenInventor format
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
    tpos = pos.add(rot.multVec(FreeCAD.Vector(0,0,-1)))
    tpos = str(tpos.x)+" "+str(tpos.y)+" "+str(tpos.z)
    up = rot.multVec(FreeCAD.Vector(0,1,0))
    up = str(up.x)+" "+str(up.y)+" "+str(up.z)
    pos = str(pos.x)+" "+str(pos.y)+" "+str(pos.z)
    #print("cam:",pos," : ",tpos," : ",up)
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
        </camera>""" % (pos, tpos, up)

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
    colorname = objname + "_color"
    color = None
    alpha = None
    mat = None
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
                color = str(color[0])+" "+str(color[1])+" "+str(color[2])
            if "Transparency" in mat.Material:
                if float(mat.Material["Transparency"]) > 0:
                    alpha = str(1.0/float(mat.Material["Transparency"]))
                else:
                    alpha = "1.0"
    if obj.ViewObject:
        if not color:
            if hasattr(obj.ViewObject,"ShapeColor"):
                color = obj.ViewObject.ShapeColor[:3]
                color = str(color[0])+" "+str(color[1])+" "+str(color[2])
        if not alpha:
            if hasattr(obj.ViewObject,"Transparency"):
                if obj.ViewObject.Transparency > 0:
                    alpha = str(1.0/(float(obj.ViewObject.Transparency)/100.0))
    if not color:
        color = "1.0 1.0 1.0"
    if not alpha:
        alpha = "1.0"
    bsdfname = objname + "_bsdf"
    matname = objname + "_mat"
    meshfile = tempfile.mkstemp(suffix=".obj")[1]
    objfile = os.path.splitext(os.path.basename(meshfile))[0]
    m = None
    if obj.isDerivedFrom("Part::Feature"):
        import MeshPart
        m = MeshPart.meshFromShape(Shape=obj.Shape, 
                                   LinearDeflection=0.1, 
                                   AngularDeflection=0.523599, 
                                   Relative=False)
    elif obj.isDerivedFrom("Mesh::Feature"):
        m = obj.Mesh
    if not m:
        return ""
    m.write(meshfile)
    # fix for missing object name (mandatory in Appleseed)
    f = open(meshfile, "r")
    contents = f.readlines()
    f.close()
    n = []
    found = False
    for l in contents:
        if (not found) and l.startswith("f "):
            found = True
            n.append("o "+objname+"\n")
        n.append(l)
    f = open(meshfile, "w")
    contents = "".join(n)
    f.write(contents)
    f.close()
    objdef = """
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
            </color>
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
            </material>
            <object name="%s" model="mesh_object">
                <parameter name="filename" value="%s" />
            </object>
            <object_instance name="%s.instance" object="%s">
                <assign_material slot="default" side="front" material="%s" />
                <assign_material slot="default" side="back" material="%s" />
            </object_instance>""" % (colorname, color, alpha, 
                                    bsdfname, colorname, 
                                    matname, bsdfname, 
                                    objfile, meshfile, 
                                    objfile+"."+objname, objfile+"."+objname, matname, matname)

    return objdef


def render(project,external=False):


    if not project.PageResult:
        return
        
    if hasattr(project,"RenderWidth") and hasattr(project,"RenderHeight"):
        # change image size in template
        f = open(project.PageResult,"r")
        t = f.read()
        f.close()
        res = re.findall("<parameter name=\"resolution.*?\/>",t)
        if res:
            t = t.replace(res[0],"<parameter name=\"resolution\" value=\""+str(project.RenderWidth)+" "+str(project.RenderHeight)+"\" />")
            fp = tempfile.mkstemp(prefix=project.Name,suffix=os.path.splitext(project.Template)[-1])[1]
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
    if not rpath:
        FreeCAD.Console.PrintError("Unable to locate Appleseed executable. Please set the correct path in Edit -> Preferences -> Render")
        return
    if args:
        args += " "
    os.system(rpath+" "+args+project.PageResult)
    return


