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
import pathlib
import argparse
import sys

PYSIDE6 = False

if PYSIDE6:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
    from PySide6.QtCore import QUrl, Qt, QTimer, Slot, QCoreApplication
    from PySide6.QtGui import QGuiApplication, QWindow
    from PySide6.QtWidgets import (
        QWidget,
        QToolBar,
        QVBoxLayout,
        QApplication,
        QMainWindow,
        QLabel,
        QTabWidget,
        QMdiArea,
    )
    from PySide6.QtWebEngineQuick import QtWebEngineQuick
    from PySide6.QtQml import QQmlApplicationEngine
else:
    from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEngineScript, QWebEnginePage
    from PySide2.QtCore import QUrl, Qt, QTimer, Slot, QCoreApplication
    from PySide2.QtGui import QGuiApplication, QWindow
    from PySide2.QtWidgets import (
        QWidget,
        QToolBar,
        QVBoxLayout,
        QApplication,
        QMainWindow,
        QLabel,
        QTabWidget,
        QMdiArea,
    )
    # from PySide2.QtWebEngineQuick import QtWebEngineQuick
    # from PySide2.QtQml import QQmlApplicationEngine



class HelpViewer(QWidget):
    """A help viewer widget.

    The help viewer is an html viewer but is able to render (local) markdown
    files.
    Markdown files are converted on-the-fly, thanks to 'marked.js' module.
    (https://github.com/markedjs/marked)
    """

    SCRIPT_GREASEBLOCK = """\
    // ==UserScript==
    // @match file://*/*.md
    // ==/UserScript==
    """

    def __init__(self, wbdir, parent=None):
        """Initialize HelpViewer."""

        jquery_path = os.path.join(wbdir, "docs", "3rdparty", "jQuery.js")
        with open(jquery_path, encoding="utf-8") as f:
            script_jquery_source = self.SCRIPT_GREASEBLOCK + f.read()

        marked_path = os.path.join(wbdir, "docs", "3rdparty", "marked.min.js")
        with open(marked_path, encoding="utf-8") as f:
            script_marked_source = self.SCRIPT_GREASEBLOCK + f.read()

        css_path = os.path.join(wbdir, "docs", "3rdparty", "waterlight.css")
        css_url = QUrl.fromLocalFile(css_path).url()

        script_run_source = (
            self.SCRIPT_GREASEBLOCK
            + f"""\
        $.when( $.ready).then(function() {{
          var now_body = $("body").text();
          $("body").html( marked.parse(now_body) );
          $("head").append('<link rel="stylesheet" href="{css_url}">');
        }});
        """
        )  # Stylesheet credit: https://github.com/kognise/water.css

        super().__init__(parent)

        self.setLayout(QVBoxLayout())

        # Set subwidgets
        self.toolbar = QToolBar()
        self.layout().addWidget(self.toolbar)
        self.view = MyViewer()
        self.layout().addWidget(self.view)

        # Add actions to toolbar
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Back))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Forward))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Reload))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Stop))

        # Insert scripts into Web view
        scripts = self.view.page().scripts()

        script_jquery = QWebEngineScript()
        script_jquery.setSourceCode(script_jquery_source)
        script_jquery.setInjectionPoint(QWebEngineScript.DocumentCreation)
        scripts.insert(script_jquery)

        script_marked = QWebEngineScript()
        script_marked.setSourceCode(script_marked_source)
        script_marked.setInjectionPoint(QWebEngineScript.DocumentCreation)
        scripts.insert(script_marked)

        script_run = QWebEngineScript()
        script_run.setSourceCode(script_run_source)
        script_run.setInjectionPoint(QWebEngineScript.DocumentReady)
        scripts.insert(script_run)

        self.view.page().createWindow = fail

    def setUrl(self, url):  # pylint: disable=invalid-name
        """Set viewer url.

        Args:
            url -- url to set viewer to (QUrl)
        """
        self.view.load(url)


def send_message(message_type, message_content):
    message = f"@@{message_type}@@{message_content}"
    print(message)
    sys.stdout.flush()


class MyViewer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createWindow(self, type):
        raise RuntimeError()
        print("createWindow", type)
        return None


def fail():
    raise RuntimeError()


def open_help(workbench_dir):
    """Open a help viewer on Render documentation.

    The help files are located in ./docs directory, except the root file, which
    is in the workbench root directory. As the files are located in local
    files, the help is available off-line.
    Help files are in markdown format.
    """
    # app = QApplication(["", "--no-sandbox"])
    # QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    # app = QApplication(["", "--no-sandbox"])

    # QCoreApplication.setAttribute(Qt.AA_NativeWindows)
    # QCoreApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    # app = QApplication()
    # main_window = QMainWindow()
    # winid = main_window.winId()
    # send_message("WINID", winid)
    # input()
    # print(winid)  # TODO

    readme = os.path.join(workbench_dir, "README.md")

    # label = QLabel("Hello")
    # main_window.setCentralWidget(QMdiArea())
    # area = main_window.centralWidget()
    # area.show()

    # winid = view.winId()
    # # view.setWindowFlags(Qt.FramelessWindowHint | Qt.BypassGraphicsProxyWidget)
    # send_message("WINID", winid)
    # input()
    # view.setUrl(QUrl.fromLocalFile(readme))
    # print(winid)  # TODO

    # print(f"{view.windowType()=}")
    # print(f"{view.windowFlags()=}")
    # # main_window.setCentralWidget(view)
    # # main_window.setCentralWidget(viewer)
    # # viewer.show()
    # # main_window.show()
    # view.show()
    # print(view.winId())  # TODO
    # print(view.winId())  # TODO
    # send_message("WINID", winid)
    # input()
    # main_window.show()

    # area.addSubWindow(QLabel("Hello")).show()

    # Via QQmlApplicationEngine
    @Slot()
    def send_winid_qml():
        objects = engine.rootObjects()
        print("Objects:", objects)
        winid = objects[0].winId()
        send_message("WINID", winid)

    @Slot()
    def send_winid_wigdet():
        objects = engine.rootObjects()
        print("Objects:", objects)
        winid = objects[0].winId()
        send_message("WINID", winid)

    QML = False
    if QML:
        QtWebEngineQuick.initialize()
        app = QGuiApplication()
        engine = QQmlApplicationEngine()
        engine.load(
            QUrl(
                "file:///home/vincent/Documents/DevGit/FreeCAD-render/Render/main.qml"
            )
        )
        QTimer.singleShot(5000, send_winid_qml)

    # Via widget
    @Slot()
    def add_viewer():
        # window = QWindow()
        viewer = HelpViewer(workbench_dir, parent=None)
        viewer.setUrl(QUrl.fromLocalFile(readme))
        viewer.setVisible(True)
        mainwindow.setCentralWidget(viewer)
        viewer.show()
        winid = mainwindow.winId()
        send_message("WINID", winid)

    if not QML:
        app = QApplication()
        mainwindow = QMainWindow()
        mainwindow.show()
        QTimer.singleShot(0, add_viewer)

    if PYSIDE6:
        app.exec()
    else:
        app.exec_()


def main():
    """The entry point."""
    # Get workbench path from command line arguments
    parser = argparse.ArgumentParser(
        prog="Render help",
        description="Open a help browser for Render Workbench",
    )
    parser.add_argument(
        "path_to_workbench",
        help="the path to the workbench",
        type=pathlib.Path,
    )
    args = parser.parse_args()

    open_help(args.path_to_workbench)


if __name__ == "__main__":
    print("Starting help")  # TODO
    # Script
    main()
