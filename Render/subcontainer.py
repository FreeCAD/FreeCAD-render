# TODO license etc.

import os
import sys
import re

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

import FreeCADGui as Gui
import FreeCAD as App

from Render.constants import WBDIR, PKGDIR
from Render.virtualenv import get_venv_python


# From:
# https://stackoverflow.com/questions/40348044/executing-a-qt-application-inside-qt-application


class PythonSubprocess(QProcess):

    winid_available = Signal(int)

    def __init__(self, python, args, parent=None):
        super().__init__(parent)

        # Set program and arguments
        self.setProgram(python)
        self.setArguments(args)

        # Set channel processing
        self.setReadChannel(QProcess.StandardOutput)
        self.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # Connect signals
        self.readyRead.connect(self._handle_input)

    @Slot()
    def _handle_input(self):
        raw = self.readAllStandardOutput()
        lines = raw.split("\n")
        for line in lines:
            if not line:
                continue
            match = re.match(rb"^@@(.*?)@@(.*)", line)
            if match:
                groups = match.groups()
                if len(groups) < 2:
                    App.Console.PrintError("Malformed process message")
                    continue
                message_type, message_content, *_ = groups
                self._dispatch_message(message_type, message_content)
            else:
                print("[Render][Sub] " + str(line, encoding="latin-1"))  # TODO

    def _dispatch_message(self, command, message):
        if command == b"WINID":
            winid, _ = QByteArray(message).toLongLong()
            self.winid_available.emit(winid)

    @Slot(bytes)
    def write(self, message):
        res = super().write(message + b"\n")
        print(res)


class PythonSubprocessWindow(QMdiSubWindow):
    def __init__(self, python, args):
        super().__init__()  # Parent will be set at start
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.process = PythonSubprocess(python, args, parent=self)

        self.container = None

        # Signal/slot connections
        self.process.winid_available.connect(self.attach_process)

    def __del__(self):
        if self.process:
            self.process.terminate()
            finished = self.process.waitForFinished()
            if not finished:
                self.process.kill()
                self.process.waitForFinished()

    def start(self):
        self.process.start()
        mdiarea = Gui.getMainWindow().centralWidget()
        if not mdiarea.subWindowList():
            # Hack: if we don't do that, FreeCAD crashes at next "newDocument"
            # I haven't found out the reason of the crash, but the following
            # open/close trick will avoid that
            doc = App.newDocument()
            App.closeDocument(doc.Name)
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
        self.show()

        self.process.write(b"@@START@@")


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
    script = os.path.join(PKGDIR, "help.py")
    script = os.path.normpath(script)
    wbdir = os.path.normpath(WBDIR)
    options = [wbdir]
    start_subapp(script, options)
