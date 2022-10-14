# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2022 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements a help viewer for Render workbench."""

import os.path

from PySide2.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEngineScript,
    QWebEnginePage,
)
from PySide2.QtCore import QUrl
from PySide2.QtWidgets import QWidget, QToolBar, QVBoxLayout

import FreeCADGui as Gui
import FreeCAD as App

from Render.constants import WBDIR


class HelpViewer(QWidget):
    """A help viewer widget.

    The help viewer is an html viewer but is able to render (local)markdown
    files.
    Markdown files are converted on-the-fly, thanks to 'marked.js' module.
    (https://github.com/markedjs/marked)
    """

    def __init__(self, parent=None):
        """Initialize HelpViewer."""
        assert SCRIPT_JQUERY and SCRIPT_MARKED

        super().__init__(parent)

        self.setLayout(QVBoxLayout())

        # Set subwidgets
        self.toolbar = QToolBar()
        self.layout().addWidget(self.toolbar)
        self.view = QWebEngineView()
        self.layout().addWidget(self.view)

        # Add actions to toolbar
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Back))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Forward))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Reload))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Stop))

        # Insert scripts into Web view
        scripts = self.view.page().scripts()

        script_jquery = QWebEngineScript()
        script_jquery.setSourceCode(SCRIPT_JQUERY)
        script_jquery.setInjectionPoint(QWebEngineScript.DocumentCreation)
        scripts.insert(script_jquery)

        script_marked = QWebEngineScript()
        script_marked.setSourceCode(SCRIPT_MARKED)
        script_marked.setInjectionPoint(QWebEngineScript.DocumentCreation)
        scripts.insert(script_marked)

        script_run = QWebEngineScript()
        script_run.setSourceCode(SCRIPT_RUN)
        script_run.setInjectionPoint(QWebEngineScript.DocumentReady)
        scripts.insert(script_run)

    def setUrl(self, url):  # pylint: disable=invalid-name
        """Set viewer url.

        Args:
            url -- url to set viewer to (QUrl)
        """
        self.view.setUrl(url)


def open_help():
    """Open a help viewer on Render documentation.

    The help files are located in ./docs directory, except the root file, which
    is in the workbench root directory. As the files are located in local
    files, the help is available off-line.
    Help files are in markdown format.
    """
    if not App.GuiUp:
        return

    viewer = HelpViewer()
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("Render help")
    subw.setVisible(True)
    
    path = os.path.join(WBDIR,"README.md")
    url = QUrl.fromLocalFile(path)
    viewer.setUrl(url)
    viewer.show()


# Init module
SCRIPT_JQUERY, SCRIPT_MARKED = None, None

SCRIPT_GREASEBLOCK = """\
// ==UserScript==
// @match file://*/*.md
// ==/UserScript==
"""

JQUERY_PATH = os.path.join(WBDIR, "docs", "3rdparty", "jQuery.js")
with open(JQUERY_PATH, encoding="utf-8") as f:
    SCRIPT_JQUERY = SCRIPT_GREASEBLOCK + f.read()

MARKED_PATH = os.path.join(WBDIR, "docs", "3rdparty", "marked.min.js")
with open(MARKED_PATH, encoding="utf-8") as f:
    SCRIPT_MARKED = SCRIPT_GREASEBLOCK + f.read()

CSS_PATH = os.path.join(WBDIR, "docs", "3rdparty", "waterlight.css")
CSS_URL = QUrl.fromLocalFile(CSS_PATH).url()
SCRIPT_RUN = SCRIPT_GREASEBLOCK + f"""\
$.when( $.ready).then(function() {{
  var now_body = $("body").text();
  $("body").html( marked.parse(now_body) );
  $("head").append('<link rel="stylesheet" href="{CSS_URL}">');
}});
"""  # Stylesheet credit: https://github.com/kognise/water.css
