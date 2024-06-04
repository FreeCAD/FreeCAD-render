# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2024 Howetuft <howetuft@gmail.com>                      *
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

"""This module allows to embed an external application in FreeCAD

It is firstly intended to embed QtWebEngine features, following the
removal of QtWebEngine from FreeCAD dependencies (May 2024).
This module reduces Render dependencies to FreeCAD and PySide.
"""

# A few design comments:
# - Communication between Render and embedded app is done by pipes
# - For a reason I couldn't clarify, the subwindow to embed the external
#   application cannot be the first one created in the MDI, otherwise when a
#   new document is created, FreeCAD crashes. So I had to introduce a (bad)
#   workaround when the view list is empty (create and immediately destroy
#   a dummy doc...)

import os
import sys
import re
import pickle
import uuid

from PySide.QtCore import (
    QProcess,
    QObject,
    Signal,
    Slot,
    QEventLoop,
    Qt,
    QByteArray,
)
from PySide.QtWidgets import QWidget, QLabel
from PySide.QtGui import QWindow, QMdiSubWindow, QGuiApplication
from PySide.QtNetwork import QLocalServer, QLocalSocket

import FreeCADGui as Gui
import FreeCAD as App

from Render.constants import WBDIR, PKGDIR
from Render.virtualenv import get_venv_python


# From:
# https://stackoverflow.com/questions/40348044/executing-a-qt-application-inside-qt-application

from multiprocessing.connection import Client, Listener, Connection, wait
from threading import Thread


class PipeListener(QObject):
    new_connection = Signal(Connection)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listener = Listener()
        self.connections = []
        self.thread = Thread(target=self._do_listen)

    def start_listening(self):
        self.thread.start()

    @property
    def address(self):
        return self.listener.address

    @property
    def last_accepted(self):
        return self.listener.last_accepted

    def _do_listen(self):
        while conn := self.listener.accept():
            self.connections.append(conn)
            self.new_connection.emit(conn)
            print("Connection accepted from", self.listener.last_accepted)


class PythonSubprocess(QProcess):
    """A helper to run a Python script as a subprocess.

    This object provides:
    - echoing of subprocess stdout/stderr
    - a communication server to interact with process (based on QLocalServer)
    """

    winid_available = Signal(int)

    def __init__(self, python, args, parent=None):
        super().__init__(parent)

        # Set stdout/stderr echoing
        self.setReadChannel(QProcess.StandardOutput)
        self.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.readyRead.connect(self._echo_stdout)

        # Create communication server
        # TODO
        # self.server = QLocalServer(self)
        # self.server.setSocketOptions(QLocalServer.UserAccessOption)
        # self.server.newConnection.connect(self._server_new_connection)
        self.listener = PipeListener()
        self.listener.new_connection.connect(self._new_connection)
        self.listener.start_listening()

        server_name = self.listener.address
        # server_name = f"render.{str(uuid.uuid1())}"
        # res = self.server.listen(server_name)
        # if not res:
        # App.Console.PrintWarning(self.server.error())
        # raise RuntimeError(
        # "[Render][Sub] Unable to launch server: "
        # f"'{server.errorString()}'"
        # )
        args = args + ["--server", server_name]
        self.connection = None
        self.connection_listener = None

        # Set program and arguments
        self.setProgram(python)
        self.setArguments(args)
        statement = " ".join([python] + args)
        App.Console.PrintLog(statement + "\n")

    @Slot(Connection)
    def _new_connection(self, connection):
        """Handle new connection to communication server.

        Nota: only one connection is allowed.
        """
        if self.connection:
            raise RuntimeError(
                "New incoming connection, but connection already set"
            )
        self.connection = connection
        self.connection_listener = Thread(target=self._connection_read)
        self.connection_listener.start()
        # TODO
        # self.connection.readyRead.connect(self._server_read)

    def _connection_read(self):
        while True:
            print("HERE")
            try:
                obj = self.connection.recv()
            except EOFError:
                break
            verb, argument = obj
            print(verb, argument)  # TODO

            # Handle
            if verb == "WINID":
                argument = int(argument)
                self.winid_available.emit(argument)
            else:
                App.Console.PrintError(
                    f"[Render][Sub] Unknown verb/argument: '{verb}' '{argument}')"
                )

    @Slot()
    def _server_read(self):
        """Read data from communication server."""
        # Read verb and argument
        self.connection.startTransaction()
        data = self.connection.readAll()
        try:
            obj = pickle.loads(data, encoding="utf-8")
            verb, argument = obj
        except pickle.UnpicklingError as err:
            App.Console.PrintWarning(
                f"[Render][Sub] Cannot unpickle subprocess message: {err}"
            )
            self.connection.rollbackTransaction()
            return
        except TypeError as err:
            App.Console.PrintWarning(
                f"[Render][Sub] Cannot interpret subprocess message: {err}"
            )
            self.connection.rollbackTransaction()
            return
        self.connection.commitTransaction()

        # Handle
        if verb == "WINID":
            argument = int(argument)
            self.winid_available.emit(argument)
        else:
            App.Console.PrintError(
                f"[Render][Sub] Unknown verb/argument: '{verb}' '{argument}')"
            )

    @Slot()
    def _echo_stdout(self):
        """Handle subprocess messages, piped to subprocess stdout.

        If subprocess output is recognized as a message, it is parsed
        and transmitted to dispatch_message.
        """

        raw = self.readAllStandardOutput()
        lines = raw.split("\n")
        for line in lines:
            print("[Render][Sub] " + str(line, encoding="utf-8"))

    @Slot(bytes)
    def send_message(self, verb, argument=None):
        """Write a message to subprocess."""
        message = (verb, argument)
        self.connection.send(message)
        # self.connection.flush()


class PythonSubprocessWindow(QMdiSubWindow):
    def __init__(self, python, args):
        super().__init__()  # Parent will be set at start
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.process = PythonSubprocess(python, args, parent=self)

        self.container = None

        # Signal/slot connections
        self.process.winid_available.connect(self.attach_process)

    def start(self):
        self.process.start()
        mdiarea = Gui.getMainWindow().centralWidget()
        if not mdiarea.subWindowList():
            # Hack: if we don't do that, FreeCAD crashes at next "newDocument"
            # I haven't found out the reason of the crash, but the following
            # open/close trick will avoid that
            doc = App.newDocument()
            App.closeDocument(doc.Name)
        self.setWindowTitle("Render")
        mdiarea.addSubWindow(self)

    @Slot(int)
    def attach_process(self, winid):
        # Create and embed container
        self.window = QWindow.fromWinId(winid)
        self.window.setObjectName("RenderWindowFromWinid")
        self.container = QWidget.createWindowContainer(
            self.window, None, Qt.FramelessWindowHint | Qt.ForeignWindow
        )
        self.container.setObjectName("RenderProcessWindowContainer")
        self.setWidget(self.container)
        self.showMaximized()

        self.process.write(b"@@START@@")

    def closeEvent(self, event):
        self.process.send_message("CLOSE")
        QGuiApplication.instance().processEvents()
        finished = self.process.waitForFinished(3000)
        if not finished:
            self.process.terminate()
            finished = self.process.waitForFinished(3000)
            if not finished:
                App.Console.PrintWarning(
                    "[Render][Sub] Subprocess terminate timeout, have to kill it\n"
                )
                self.process.kill()


def start_subapp(script, options=None):
    # Process arguments
    script = str(script)
    options = options or []
    options = list(options)

    python = get_venv_python()
    args = ["-u", script] + options

    subw = PythonSubprocessWindow(python, args)
    subw.start()


def start_help():
    script = os.path.join(PKGDIR, "help", "help.py")
    script = os.path.normpath(script)
    wbdir = os.path.normpath(WBDIR)
    options = [wbdir]
    start_subapp(script, options)
