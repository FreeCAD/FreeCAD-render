# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2024 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
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

"""This module allows to embed an external application in FreeCAD

It is firstly intended to embed QtWebEngine features, following the
removal of QtWebEngine from FreeCAD dependencies (May 2024).
This module reduces Render dependencies to FreeCAD and PySide.
"""

# A few comments about design:
# - Communication between Render and embedded app is done by pipes, thanks to
#   Python. I did not opt for QLocalServer/QLocalSocket, as QtNetwork is not
#   available in all FreeCAD versions (and could be removed in the future?)
# - For a reason I couldn't clarify, the subwindow to embed the external
#   application cannot be the first one created in the MDI, otherwise when a
#   new document is created, FreeCAD crashes. So I had to introduce a (bad)
#   workaround when the view list is empty (create and immediately destroy
#   a dummy doc...)
#
# From:
# https://stackoverflow.com/questions/40348044/executing-a-qt-application-inside-qt-application


import os
from multiprocessing.connection import Listener, Connection, wait
from threading import Thread, Event
import pathlib
import configparser
import sys

import FreeCADGui as Gui
import FreeCAD as App

from Render.constants import PLUGINDIR, PARAMS
from Render.virtualenv import (
    get_venv_python,
    get_venv_pyside_version,
    get_venv_sitepackages,
)
from Render.material import make_material
from Render.lights import ImageLight

from PySide.QtCore import (
    QProcess,
    QProcessEnvironment,
    QObject,
    Signal,
    Slot,
    Qt,
    QEventLoop,
)

from PySide.QtGui import (
    QWidget,
    QWindow,
    QMdiSubWindow,
    QGuiApplication,
)

from PySide.QtWidgets import QWidget, QLabel, QVBoxLayout


class ConnectionServer(QObject):
    """A server to connect the host process and the sub process."""

    new_connection = Signal(Connection)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listener = Listener()
        self.connections = []
        self.thread = Thread(target=self._do_listen)

    def start_listening(self):
        """Start listening to incoming connection requests."""
        self.thread.start()

    @property
    def address(self):
        """Give server address."""
        return self.listener.address

    @property
    def last_accepted(self):
        """Return last accepted connection."""
        return self.listener.last_accepted

    def _do_listen(self):
        """Listen to incoming conn requests (worker)."""
        while conn := self.listener.accept():
            self.connections.append(conn)
            self.new_connection.emit(conn)

    def close(self):
        """Close listener."""
        self.listener.close()


class PythonSubprocess(QProcess):
    """A helper to run a Python script as a subprocess.

    This object provides:
    - echoing of subprocess stdout/stderr
    - a communication server to interact with process
    """

    winid_available = Signal(int)
    detach_required = Signal()

    def __init__(self, python, args, parent=None):
        super().__init__(parent)

        # Set environment
        environment = QProcessEnvironment.systemEnvironment()
        environment.remove("PYTHONHOME")
        environment.remove("PYTHONPATH")
        environment.remove("QTWEBENGINE_DISABLE_SANDBOX")
        environment.remove("SESSION_MANAGER")
        if not environment.contains("SNAP"):
            environment.remove("LD_LIBRARY_PATH")
        resources = os.path.join(
            get_venv_sitepackages(),
            get_venv_pyside_version(),
            "Qt",
            "resources",
        )
        if os.path.exists(resources):
            environment.insert("QTWEBENGINE_RESOURCES_PATH", resources)
            App.Console.PrintLog(
                "[Render][Sub] QTWEBENGINE_RESOURCES_PATH set to "
                f"'{resources}'\n"
            )
        else:
            App.Console.PrintLog(
                "[Render][Sub] COULD NOT set QTWEBENGINE_RESOURCES_PATH to "
                f"'{resources}'\n"
            )
        environment.insert("QT_API", "pyqt6")
        self.setProcessEnvironment(environment)

        # Set stdout/stderr echoing
        self.setReadChannel(QProcess.StandardOutput)
        self.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.readyRead.connect(self._echo_stdout)

        # Create connection server
        self.server = ConnectionServer()
        self.server.new_connection.connect(self._new_connection)
        self.server.start_listening()

        server_name = self.server.address
        subcontainer_args = [
            "--server",
            server_name,
        ]
        if PARAMS.GetBool("PluginDisableEmbedding"):
            subcontainer_args += ["--disable-embedding"]
        args = ["-E"] + args + subcontainer_args
        self.connections = []
        self.connections_listener = Thread(target=self.child_recv)
        self.connections_active = Event()
        self.connections_active.set()
        self.appname = "Sub"  # 'Sub' by default

        # Set program and arguments
        self.setProgram(python)
        working_directory = PLUGINDIR
        self.setWorkingDirectory(working_directory)
        self.setArguments(args)

        # Log statement
        App.Console.PrintLog(f"cd '{working_directory}'\n")
        statement = " ".join([python] + args)
        App.Console.PrintLog(statement + "\n")

    @Slot(Connection)
    def _new_connection(self, connection):
        """Handle new connection."""
        self.connections.append(connection)
        if not self.connections_listener.is_alive():
            self.connections_listener.start()

    def msgfmt(self, msg):
        """Format message before display."""
        return f"[Render][{self.appname}] {str(msg)}"

    def child_recv(self):
        """Receive messages from subprocess."""
        while self.connections_active.is_set:
            # We use wait to get a timeout parameter
            for conn in wait(self.connections, timeout=1):
                try:
                    message = conn.recv()
                except EOFError:
                    self.connections.remove(conn)
                    if not self.connections:
                        self.connections_active.clear()
                else:
                    verb, argument = message

                    # Handle
                    if verb == "WINID":
                        argument = int(argument)
                        self.winid_available.emit(argument)
                    elif verb == "DETACH":
                        self.detach_required.emit()
                    elif verb == "LOG":
                        argument = str(argument)
                        App.Console.PrintLog(self.msgfmt(argument))
                    elif verb == "MSG":
                        argument = str(argument)
                        App.Console.PrintMessage(self.msgfmt(argument))
                    elif verb == "WARN":
                        argument = str(argument)
                        App.Console.PrintWarning(self.msgfmt(argument))
                    elif verb == "ERROR":
                        argument = str(argument)
                        App.Console.PrintError(self.msgfmt(argument))
                    elif verb == "MATERIAL":
                        try:
                            App.ActiveDocument.openTransaction(
                                "MaterialXImport"
                            )
                            argument = pathlib.Path(argument)
                            self.import_material(argument, App.ActiveDocument)
                        finally:
                            App.ActiveDocument.commitTransaction()
                            self.child_send("RELEASE")
                    elif verb == "APPNAME":
                        self.appname = str(argument)
                    elif verb == "IMAGELIGHT":
                        try:
                            App.ActiveDocument.openTransaction("HDRIImport")
                            basename, filepath = argument
                            _, fpo, _ = ImageLight.create(App.ActiveDocument)
                            fpo.Label = basename
                            fpo.ImageFile = filepath
                        finally:
                            App.ActiveDocument.commitTransaction()
                            self.child_send("RELEASE")
                    else:
                        msg = f"Unknown verb/argument: '{verb}' '{argument}'"
                        App.Console.PrintError(self.msgfmt(msg))

    @Slot()
    def stop_listening(self):
        """Stop listening to parent messages."""
        self.connections_active.clear()
        self.connections_listener.join()

    @Slot()
    def child_send(self, verb, argument=None):
        """Write a message to subprocess."""
        message = (verb, argument)
        for conn in self.connections:
            conn.send(message)

    @Slot()
    def _echo_stdout(self):
        """Handle subprocess stdout, echoing to parent stdout."""
        raw = self.readAllStandardOutput()
        lines = raw.split("\n")
        for line in lines:
            App.Console.PrintLog(
                f"[Render][Sub] {str(line, encoding='utf-8')}\n"
            )

    def import_material(self, path, doc):
        """Import a material card."""
        card = configparser.ConfigParser()
        card.optionxform = lambda x: x  # Case sensitive
        card.read(path)
        try:
            mxname = card["General"]["Name"]
        except LookupError:
            mxname = "Material"
        App.Console.PrintMessage(
            self.msgfmt(
                f"Importing material card as FreeCAD material: {mxname}\n"
            )
        )
        matdict = dict(card["Render"])
        mat = make_material(name=mxname, doc=doc)
        matdict = mat.Proxy.import_textures(matdict, basepath=None)

        # Reminder: Material.Material is not updatable in-place
        # (FreeCAD bug), thus we have to copy/replace
        mat.Material = matdict


class PythonSubprocessWindow(QMdiSubWindow):
    """A window to embed a Python subprocess, intended for MDI area."""

    def __init__(self, python, args):
        super().__init__()  # Parent will be set at start
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.process = PythonSubprocess(python, args, parent=self)

        self.container = None

        # Signal/slot connections
        self.process.winid_available.connect(self.attach_process)
        self.process.detach_required.connect(self.detach_process)

    def start(self):
        """Start window."""
        self.process.start()
        mdiarea = Gui.getMainWindow().centralWidget()
        if not mdiarea.subWindowList():
            # Hack: if we don't do that, FreeCAD crashes at next
            # "newDocument" I haven't found out the reason of the crash,
            # but the following open/close trick will avoid that
            doc = App.newDocument()
            App.closeDocument(doc.Name)
        self.setWindowTitle("Render")
        mdiarea.addSubWindow(self)

    @Slot(int)
    def attach_process(self, winid):
        """Attach subprocess to FreeCAD Gui."""
        # Create container and embed process inside
        # QWindow.fromWinId is not supported on macOS and QT <6, so open a new window instead.
        if sys.platform == "darwin":
            print(
                "QWindow.fromWinId not supported on macOS – showing placeholder window."
            )
            self.container = QWidget()
            layout = QVBoxLayout(self.container)
            label = QLabel(
                "Renderer running in external window.\nEmbedding not supported on macOS."
            )
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            self.setWidget(self.container)
            self.container.setParent(self)
            self.show()
            return
        else:
            self.window = QWindow.fromWinId(winid)
            self.window.setObjectName("RenderWindowFromWinid")
            self.container = QWidget.createWindowContainer(
                self.window,
                parent=None,
                flags=Qt.FramelessWindowHint | Qt.ForeignWindow,
            )
            self.container.setObjectName("RenderProcessWindowContainer")
            self.setWidget(self.container)
            self.container.setParent(self)
            self.show()

    @Slot()
    def detach_process(self):
        """Detach subprocess from FreeCAD Gui."""
        self.window.setParent(None)
        self.close()

    def closeEvent(self, event):
        """Respond to close event."""
        self.process.child_send("CLOSE")
        QGuiApplication.instance().processEvents()
        if not self.process.waitForFinished(3000):
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                App.Console.PrintWarning(
                    "[Render][Sub] Subprocess terminate timeout, "
                    "have to kill it\n"
                )
                self.process.kill()


class PythonSubprocessExternal(QObject):
    """A class to launch a plugin as external (no embedding in FreeCAD GUI)."""

    def __init__(self, python, args):
        super().__init__()  # Parent will be set at start
        self.process = PythonSubprocess(python, args, parent=self)

        # Signal/slot connections
        self.process.winid_available.connect(self.attach_process)
        self.process.detach_required.connect(self.detach_process)

    def start(self):
        """Start window."""
        self.process.start()
        loop = QEventLoop()
        loop.exec_()

    @Slot(int)
    def attach_process(self, winid):
        """Attach subprocess to FreeCAD Gui."""

    @Slot()
    def detach_process(self):
        """Detach subprocess from FreeCAD Gui."""
        self.deleteLater()

    def closeEvent(self, event):
        """Respond to close event."""
        self.process.child_send("CLOSE")
        QGuiApplication.instance().processEvents()
        if not self.process.waitForFinished(3000):
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                App.Console.PrintWarning(
                    "[Render][Sub] Subprocess terminate timeout, "
                    "have to kill it\n"
                )
                self.process.kill()


def start_plugin(app, options=None):
    """Start plugin."""
    # Process arguments
    path = os.path.join(PLUGINDIR, f"{app}")
    path = os.path.normpath(path)
    options = options or []
    options = list(options)

    python = get_venv_python()
    args = ["-u", "-m", app] + options

    if not PARAMS.GetBool("PluginDisableEmbedding"):
        subw = PythonSubprocessWindow(python, args)
    else:
        subw = PythonSubprocessExternal(python, args)

    subw.start()
