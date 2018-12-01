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

# This module handles all the external renderers implemented as Python modules.
# It will add all renderer modules specified below at FreeCAD launch, and
# create the necessary UI controls.

import sys,os,re,tempfile,FreeCAD,importlib

if FreeCAD.GuiUp:
    from PySide import QtCore, QtGui
    def translate(context, text):
        if sys.version_info.major >= 3:
            return QtGui.QApplication.translate(context, text, None, QtGui.QApplication.UnicodeUTF8)
        else:
            return QtGui.QApplication.translate(context, text, None, QtGui.QApplication.UnicodeUTF8).encode("utf8")
else:
    def translate(context,txt):
        return txt
def QT_TRANSLATE_NOOP(scope, text):
    return text


class RenderProjectCommand:


    "Creates a rendering project. The renderer parameter must be a valid rendering module"

    def __init__(self,renderer):
        self.renderer = renderer

    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons",self.renderer+".svg"),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Render", "%s Project") % self.renderer,
                'ToolTip' : QtCore.QT_TRANSLATE_NOOP("Render", "Creates a %s project") % self.renderer}

    def Activated(self):
        if self.renderer:
            project = FreeCAD.ActiveDocument.addObject("App::FeaturePython",self.renderer+"Project")
            Project(project)
            project.Label = self.renderer + " Project"
            project.Renderer = self.renderer
            ViewProviderProject(project.ViewObject)
            filename = QtGui.QFileDialog.getOpenFileName(QtGui.qApp.activeWindow(),'Select template','*.*')
            if filename:
                project.Template = filename[0]
            project.ViewObject.Proxy.setCamera()
            FreeCAD.ActiveDocument.recompute()



class RenderViewCommand:


    "Creates a Raytracing view of the selected object(s) in the selected project or the default project"

    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons","RenderView.svg"),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Render", "Create View"),
                'ToolTip' : QtCore.QT_TRANSLATE_NOOP("Render", "Creates a Render view of the selected object(s) in the selected project or the default project")}

    def Activated(self):
        import FreeCADGui
        project = None
        objs = []
        sel = FreeCADGui.Selection.getSelection()
        for o in sel:
            if "Renderer" in o.PropertiesList:
                project = o
            else:
                if o.isDerivedFrom("Part::Feature") or o.isDerivedFrom("Mesh::Feature"):
                    objs.append(o)
        if not project:
            for o in FreeCAD.ActiveDocument.Objects:
                if "Renderer" in o.PropertiesList:
                    project = o
                    break
        if not project:
            FreeCAD.Console.PrintError(translate("Render","Unable to find a valid project in selection or document"))
            return
        for obj in objs:
            view = FreeCAD.ActiveDocument.addObject("App::FeaturePython",obj.Name+"View")
            view.Label = "View of "+ obj.Name
            View(view)
            view.Source = obj
            project.addObject(view)
            ViewProviderView(view.ViewObject)
        FreeCAD.ActiveDocument.recompute()



class RenderCommand:


    "Renders a selected Render project"


    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons","Render.svg"),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Render", "Render"),
                'ToolTip' : QtCore.QT_TRANSLATE_NOOP("Render", "Performs the render of a selected project or the default project")}

    def Activated(self):
        import FreeCADGui
        project = None
        sel = FreeCADGui.Selection.getSelection()
        for o in sel:
            if "Renderer" in o.PropertiesList:
                project = o
                break
        if not project:
            for o in FreeCAD.ActiveDocument.Objects:
                if "Renderer" in o.PropertiesList:
                    project = o
                    break
        if not project:
            FreeCAD.Console.PrintError(translate("Render","Unable to find a valid project in selection or document"))
            return
        project.Proxy.render(project)


class RenderExternalCommand:


    "Sends a selected Render project"


    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons","Render.svg"),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Render", "Render"),
                'ToolTip' : QtCore.QT_TRANSLATE_NOOP("Render", "Performs the render of a selected project or the default project")}

    def Activated(self):
        import FreeCADGui
        project = None
        sel = FreeCADGui.Selection.getSelection()
        for o in sel:
            if "Renderer" in o.PropertiesList:
                project = o
                break
        if not project:
            for o in FreeCAD.ActiveDocument.Objects:
                if "Renderer" in o.PropertiesList:
                    project = o
                    break
        if not project:
            FreeCAD.Console.PrintError(translate("Render","Unable to find a valid project in selection or document"))
            return
        project.Proxy.render(project)


class Project:


    "A rendering project"

    def __init__(self,obj):

        obj.addProperty("App::PropertyString",       "Renderer",     "Render", QT_TRANSLATE_NOOP("App::Property","The name of the raytracing engine to use"))
        obj.addProperty("App::PropertyBool",         "DelayedBuild", "Render", QT_TRANSLATE_NOOP("App::Property","If true, the views will be updated on render only"))
        obj.addProperty("App::PropertyFile",         "Template",     "Render", QT_TRANSLATE_NOOP("App::Property","The template to be use by this rendering"))
        obj.addProperty("App::PropertyString",       "Camera",       "Render", QT_TRANSLATE_NOOP("App::Property","The camera data to be used"))
        obj.addProperty("App::PropertyFileIncluded", "PageResult",   "Render", QT_TRANSLATE_NOOP("App::Property","The result file to be sent to the renderer"))
        obj.addExtension("App::GroupExtensionPython", self)
        obj.DelayedBuild = True
        obj.Proxy = self

    def execute(self,obj):

        return True

    def onChanged(self,obj,prop):

        if prop == "DelayedBuild":
            if not obj.DelayedBuild:
                for view in obj.Group:
                    view.touch()

    def setCamera(self,obj):

        if FreeCAD.GuiUp:
            import FreeCADGui
            obj.Camera = FreeCADGui.ActiveDocument.ActiveView.getCamera()

    def writeCamera(self,obj):

        if not obj.Camera:
            self.setCamera(obj)
            if not obj.Camera:
                FreeCAD.Console.PrintError(translate("Render","Unable to set the camera"))
                return ""
        if obj.Renderer:
            try:
                renderer = importlib.import_module("renderers."+obj.Renderer)
            except ImportError:
                FreeCAD.Console.PrintError(translate("Render","Error importing renderer")+" "+str(obj.Renderer))
                return ""
            else:
                return renderer.writeCamera(obj.Camera)

    def writeObject(self,obj,view):

        if not view.Source:
            return ""
        if obj.Renderer:
            try:
                renderer = importlib.import_module("renderers."+obj.Renderer)
            except ImportError:
                FreeCAD.Console.PrintError(translate("Render","Error importing renderer")+" "+str(obj.Renderer))
                return ""
            else:
                return renderer.writeObject(view)

    def render(self,obj,external=True):

        if obj.Renderer:

            # open template
            template = None
            if obj.Template:
                if os.path.exists(obj.Template):
                    f = open(obj.Template,"rb")
                    template = f.read()
                    f.close()
            if not template:
                return

            # write camera
            cam = self.writeCamera(obj)
            
            # write objects
            renderobjs = ""
            for view in obj.Group:
                if obj.DelayedBuild:
                    renderobjs += self.writeObject(obj,view)
                else:
                    renderobjs += view.ViewResult
            
            if "RaytracingCamera" in template:
                template = re.sub("(.*RaytracingCamera.*)",cam,template)
                template = re.sub("(.*RaytracingContent.*)",renderobjs,template)
            else:
                template = re.sub("(.*RaytracingContent.*)",cam+"\n"+renderobjs,template)

            # save page result
            fp = tempfile.mkstemp(prefix=obj.Name,suffix=os.path.splitext(obj.Template)[-1])[1]
            f = open(fp,"wb")
            f.write(template)
            f.close()
            obj.PageResult = fp
            os.remove(fp)
            
            FreeCAD.ActiveDocument.recompute()

            try:
                renderer = importlib.import_module("renderers."+obj.Renderer)
            except ImportError:
                FreeCAD.Console.PrintError(translate("Render","Error importing renderer")+" "+str(obj.Renderer))
                return ""
            else:
                try:
                    return renderer.render(obj,external)
                except:
                    FreeCAD.Console.PrintError(translate("Render","Error while executing renderer")+" "+str(obj.Renderer))


class ViewProviderProject:


    def __init__(self,vobj):
        vobj.Proxy = self

    def attach(self,vobj):
        self.Object = vobj.Object
        return True

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None

    def getDisplayModes(self,vobj):
        return ["Default"]

    def getDefaultDisplayMode(self):
        return "Default"

    def setDisplayMode(self,mode):
        return mode

    def isShow(self):
        return True

    def getIcon(self):
        return os.path.join(os.path.dirname(__file__),"icons","RenderProject.svg")

    def setupContextMenu(self,vobj,menu):
        from PySide import QtCore,QtGui
        import FreeCADGui
        action1 = QtGui.QAction(QtGui.QIcon(":/icons/camera-photo.svg"),"Save camera position",menu)
        QtCore.QObject.connect(action1,QtCore.SIGNAL("triggered()"),self.setCamera)
        menu.addAction(action1)
        action2 = QtGui.QAction(QtGui.QIcon(os.path.join(os.path.dirname(__file__),"icons","Render.svg")),"Render",menu)
        QtCore.QObject.connect(action2,QtCore.SIGNAL("triggered()"),self.render)
        menu.addAction(action2)

    def setCamera(self):
        if hasattr(self,"Object"):
            self.Object.Proxy.setCamera(self.Object)

    def render(self):
        if hasattr(self,"Object"):
            self.Object.Proxy.render(self.Object)

    def claimChildren(self):
        if hasattr(self,"Object"):
            return self.Object.Group


class View:


    "A rendering view"

    def __init__(self,obj):

        obj.addProperty("App::PropertyLink",         "Source",     "Render", QT_TRANSLATE_NOOP("App::Property","The name of the raytracing engine to use"))
        obj.addProperty("App::PropertyLink",         "Material",   "Render", QT_TRANSLATE_NOOP("App::Property","The template to be use by this rendering"))
        obj.addProperty("App::PropertyString",       "ViewResult", "Render", QT_TRANSLATE_NOOP("App::Property","The rendering output of this view"))
        obj.Proxy = self

    def execute(self,obj):

        for proj in obj.InList:
            if hasattr(proj,"Group"):
                for c in proj.Group:
                    if c == obj:
                        if not proj.DelayedBuild:
                            obj.ViewResult = proj.Proxy.writeObject(proj,obj)
                            break


class ViewProviderView:


    def __init__(self,vobj):
        vobj.Proxy = self

    def attach(self,vobj):
        self.Object = vobj.Object

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None

    def getDisplayModes(self,vobj):
        return ["Default"]

    def getDefaultDisplayMode(self):
        return "Default"

    def setDisplayMode(self,mode):
        return mode

    def isShow(self):
        return True

    def getIcon(self):
        return os.path.join(os.path.dirname(__file__),"icons","RenderViewTree.svg")



# Load available renderers and create the FreeCAD commands



if FreeCAD.GuiUp:

    import FreeCADGui

    RenderCommands = []
    Renderers = os.listdir(os.path.dirname(__file__)+os.sep+"renderers")
    Renderers = [r for r in Renderers if not ".pyc" in r]
    Renderers = [r for r in Renderers if not "__init__" in r]
    Renderers = [os.path.splitext(r)[0] for r in Renderers]
    for renderer in Renderers:
        FreeCADGui.addCommand('Render_'+renderer, RenderProjectCommand(renderer))
        RenderCommands.append('Render_'+renderer)
    FreeCADGui.addCommand('Render_View', RenderViewCommand())
    RenderCommands.append('Render_View')
    FreeCADGui.addCommand('Render_Render', RenderCommand())
    RenderCommands.append('Render_Render')

    # This is for InitGui.py because it cannot import os
    prefpage = os.path.join(os.path.dirname(__file__),"ui","RenderSettings.ui")
