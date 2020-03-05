# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
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


class RenderWorkbench (Workbench):


    "the Render Workbench"

    def __init__(self):
        self.__class__.MenuText = "Render"
        self.__class__.ToolTip = "The Render module is a modern replacement for the Raytracing module"
        self.__class__.Icon='''
/* XPM */
static char * Render_xpm[] = {
"16 16 33 1",
" 	c None",
".	c #103F06",
"+	c #224702",
"@	c #1A580E",
"#	c #2F5600",
"$	c #386402",
"%	c #297014",
"&	c #416B00",
"*	c #537200",
"=	c #3C7B0F",
"-	c #4B880D",
";	c #579310",
">	c #609702",
",	c #858B13",
"'	c #6AA20A",
")	c #92A709",
"!	c #9EA610",
"~	c #ACA137",
"{	c #86B208",
"]	c #B6A94A",
"^	c #9DC400",
"/	c #ADC50F",
"(	c #B4C31F",
"_	c #C8BD71",
":	c #C2C731",
"<	c #CAD51A",
"[	c #D7D736",
"}	c #E9CD77",
"|	c #DCDA50",
"1	c #E5DF6D",
"2	c #EBE581",
"3	c #F4EFA8",
"4	c #F8F4C7",
"                ",
"                ",
"     #*)!~]     ",
"    &^^<[|2_}   ",
"   ${{/(|243_   ",
"  +;'{{(|2431~  ",
"  #->'{(:|11[,  ",
"  @--;')(::[<,  ",
"  @==-;'{)(//*  ",
"  .%%=-;>'{^^#  ",
"  .@%%=-;>'{;   ",
"   .@%%=-;>>+   ",
"    .@%%=-&+    ",
"      ....      ",
"                ",
"                "};
'''


    def Initialize(self):

        def QT_TRANSLATE_NOOP(scope, text):
            return text

        import Render
        commands = Render.RenderCommands
        self.appendToolbar(QT_TRANSLATE_NOOP("Workbench","Render"),commands)
        self.appendMenu(QT_TRANSLATE_NOOP("Workbench","&Render"),commands)
        FreeCADGui.addIconPath(Render.iconpath)
        FreeCADGui.addPreferencePage(Render.prefpage,"Render")
        Log ('Loading Render module...done\n')

    def GetClassName(self): 
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(RenderWorkbench)


