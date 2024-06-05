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
import signal
from multiprocessing.connection import Client, wait
from threading import Thread, Event

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
    from PySide6.QtCore import QUrl, Qt, QTimer, Slot, QObject, Signal
    from PySide6.QtWidgets import (
        QWidget,
        QToolBar,
        QVBoxLayout,
        QApplication,
        QMainWindow,
    )

    PYSIDE6 = True
except ModuleNotFoundError:
    from PySide2.QtWebEngineWidgets import (
        QWebEngineView,
        QWebEngineScript,
        QWebEnginePage,
    )
    from PySide2.QtCore import QUrl, Qt, QTimer, Slot, QObject, Signal
    from PySide2.QtWidgets import (
        QWidget,
        QToolBar,
        QVBoxLayout,
        QApplication,
        QMainWindow,
    )

    PYSIDE6 = False


THISDIR = os.path.dirname(__file__)


class HelpViewer(QWidget):  # pylint: disable=too-few-public-methods
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

    def __init__(self, scripts_dir, parent=None):
        """Initialize HelpViewer."""
        super().__init__(parent)

        # Set subwidgets
        self.setLayout(QVBoxLayout(self))
        self.toolbar = QToolBar(self)
        self.layout().addWidget(self.toolbar)
        self.view = QWebEngineView(self)
        self.layout().addWidget(self.view)

        # Add actions to toolbar
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Back))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Forward))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Reload))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Stop))

        # Prepare scripts
        jquery_path = os.path.join(scripts_dir, "jQuery.js")
        with open(jquery_path, encoding="utf-8") as f:
            script_jquery_source = self.SCRIPT_GREASEBLOCK + f.read()

        marked_path = os.path.join(scripts_dir, "marked.min.js")
        with open(marked_path, encoding="utf-8") as f:
            script_marked_source = self.SCRIPT_GREASEBLOCK + f.read()

        css_path = os.path.join(scripts_dir, "waterlight.css")
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

    def setUrl(self, url):  # pylint: disable=invalid-name
        """Set viewer url.

        Args:
            url -- url to set viewer to (QUrl)
        """
        self.view.load(url)


class HelpApplication(QObject):
    """Open a help viewer on Render documentation.

    The help files are located in ./docs directory, except the root file, which
    is in the workbench root directory. As the files are located in local
    files, the help is available off-line.
    Help files are in markdown format.
    """

    bye = Signal()

    def __init__(self, workbench_dir, connection_name, parent=None):
        super().__init__(parent)
        readme = os.path.join(workbench_dir, "README.md")
        scripts_dir = os.path.join(THISDIR, "3rdparty")

        # Communication
        self.connection = Client(connection_name)
        self.connection_active = Event()
        self.connection_active.set()
        self.connection_listener = Thread(target=self.parent_recv)
        self.connection_listener.start()

        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self.bye.connect(self.quit)

        # Application and widget
        self.app = QApplication()
        self.app.aboutToQuit.connect(self.stop_listening)
        self.mainwindow = QMainWindow(flags=Qt.FramelessWindowHint)
        self.mainwindow.showMaximized()

        self.viewer = HelpViewer(scripts_dir, parent=self.mainwindow)
        self.viewer.setUrl(QUrl.fromLocalFile(readme))
        self.viewer.setVisible(True)

        QTimer.singleShot(0, self.add_viewer)

    def parent_send(self, verb, argument):
        """Send message to parent process."""
        message = (verb, argument)
        self.connection.send(message)

    def parent_recv(self):
        """Receive messages from parent process."""
        while self.connection_active.is_set():
            # We use wait to get a timeout parameter
            for conn in wait([self.connection], timeout=1):
                try:
                    message = conn.recv()
                except EOFError:
                    self.connection_active.clear()
                else:
                    verb, argument = message

                    # Handle
                    if verb == "CLOSE":
                        self.bye.emit()
                        self.connection_active.clear()

    @Slot()
    def stop_listening(self):
        """Stop listening to parent messages."""
        self.connection_active.clear()
        self.connection_listener.join()

    @Slot()
    def quit(self):
        """Quit application."""
        self.app.closeAllWindows()
        self.app.quit()

    @Slot()
    def add_viewer(self):
        """Add viewer (once application has been started)."""
        self.mainwindow.setCentralWidget(self.viewer)
        self.viewer.showMaximized()
        winid = self.mainwindow.winId()
        self.parent_send("WINID", winid)

    def exec(self):
        """Execute application (start event loop)."""
        if PYSIDE6:
            return self.app.exec()
        else:
            return self.app.exec_()


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
    parser.add_argument(
        "--server",
        help="the communication server name",
        type=str,
    )
    args = parser.parse_args()

    application = HelpApplication(args.path_to_workbench, args.server)
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
