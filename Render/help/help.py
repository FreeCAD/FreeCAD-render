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
import uuid
import pickle
from multiprocessing.connection import Client, wait
from threading import Thread

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
    from PySide6.QtCore import QUrl, Qt, QTimer, Slot, QObject, Signal
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
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
    from PySide2.QtCore import QUrl, Qt, QTimer, Slot
    from PySide2.QtNetwork import QLocalServer, QLocalSocket
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


# def send_message(message_type, message_content):
# """Send message to the parent process."""
# message = f"@@{message_type}@@{message_content}"
# print(message)  # Needed, not debug!
# sys.stdout.flush()

connections = []


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
        self.connection_listener = Thread(target=self._connection_read)
        self.connection_listener.start()

        self.app = QApplication()
        self.mainwindow = QMainWindow(flags=Qt.FramelessWindowHint)
        self.mainwindow.showMaximized()

        self.viewer = HelpViewer(scripts_dir, parent=self.mainwindow)
        self.viewer.setUrl(QUrl.fromLocalFile(readme))
        self.viewer.setVisible(True)

        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self.bye.connect(self.quit)

        QTimer.singleShot(0, self.add_viewer)

    def send_message(self, verb, argument):
        """Send message to the parent process."""
        message = (verb, argument)
        self.connection.send(message)

    # TODO Rename
    def _connection_read(self):
        while True:
            try:
                obj = self.connection.recv()
            except EOFError:
                break
            verb, argument = obj
            print(verb, argument)  # TODO

            # Handle
            if verb == "CLOSE":
                self.bye.emit()
                break

    @Slot()
    def quit(self):
        self.app.closeAllWindows()
        self.app.quit()

    @Slot()
    def add_viewer(self):
        self.mainwindow.setCentralWidget(self.viewer)
        self.viewer.showMaximized()
        winid = self.mainwindow.winId()
        self.send_message("WINID", winid)

    def exec(self):
        if PYSIDE6:
            return self.app.exec()
        else:
            return self.app.exec_()


def open_help(workbench_dir, server_name):
    """Open a help viewer on Render documentation.

    The help files are located in ./docs directory, except the root file, which
    is in the workbench root directory. As the files are located in local
    files, the help is available off-line.
    Help files are in markdown format.
    """
    readme = os.path.join(workbench_dir, "README.md")
    scripts_dir = os.path.join(THISDIR, "3rdparty")
    app = QApplication()
    connection = None

    def send_message(verb, argument):
        """Send message to the parent process."""
        message = (verb, argument)
        connection.send(message)

    @Slot()
    def add_viewer():
        viewer = HelpViewer(scripts_dir, parent=mainwindow)
        viewer.setUrl(QUrl.fromLocalFile(readme))
        viewer.setVisible(True)
        mainwindow.setCentralWidget(viewer)
        viewer.showMaximized()
        winid = mainwindow.winId()
        server.listen("render." + str(uuid.uuid1()))
        send_message("WINID", winid)
        # if os.name == "nt":
        # send_message("SERVER", server.fullServerName())
        # else:
        # send_message("SERVER", server.serverName())

    @Slot()
    def read_socket():
        # Read verb and argument
        connection.startTransaction()
        data = connection.readAll()
        try:
            obj = pickle.loads(data, encoding="utf-8")
            verb, argument = obj
        except pickle.UnpicklingError as err:
            print(f"[Render][Sub] Cannot unpickle subprocess message: {err}")
            connection.rollbackTransaction()
            return
        except TypeError as err:
            App.Console.PrintWarning(
                f"[Render][Sub] Cannot interpret subprocess message: {err}"
            )
            connection.rollbackTransaction()
            return
        connection.commitTransaction()

        # Handle
        if verb == "CLOSE":
            app.closeAllWindows()
            app.quit()

    @Slot()
    def new_connection():
        connection = server.nextPendingConnection()
        connections.append(connection)  # Keep
        connection.readyRead.connect(read_socket)

    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    mainwindow = QMainWindow(flags=Qt.FramelessWindowHint)
    mainwindow.show()
    QTimer.singleShot(0, add_viewer)
    server = QLocalServer(app)
    server.setSocketOptions(QLocalServer.UserAccessOption)
    server.newConnection.connect(new_connection)

    # connection = QLocalSocket()
    # connection.connectToServer(server_name)
    # res = connection.waitForConnected(2000)
    # if not res:
    # print(connection.error())
    # exit(-1)
    # connection.readyRead.connect(read_socket)
    connection = Client(server_name)

    if PYSIDE6:
        sys.exit(app.exec())
    else:
        sys.exit(app.exec_())


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
