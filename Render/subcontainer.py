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

from Render.rdrexecutor import RendererExecutor

# From:
# https://stackoverflow.com/questions/40348044/executing-a-qt-application-inside-qt-application


class SubprocessWorker(QObject):

    finished = Signal(int)
    create_window = Signal(int, QProcess)
    write_to_process = Signal(bytes)

    def __init__(self, python, args):
        super().__init__()
        self.python = python
        self.args = args
        self.process = None

    def run(self):
        loop = QEventLoop()

        # Get central widget
        mdiarea = Gui.getMainWindow().centralWidget()

        # Prepare process
        self.process = QProcess()
        self.process.setReadChannel(QProcess.StandardOutput)
        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )

        # Connect signals
        self.process.readyRead.connect(self.handle_input)
        self.process.finished.connect(loop.exit, Qt.QueuedConnection)
        self.write_to_process.connect(self.write)

        # Start process
        self.process.start(self.python, self.args)
        started = self.process.waitForStarted()

        loop.exec_()

        self.process.terminate()

    @Slot()
    def handle_input(self):
        raw = self.process.readAllStandardOutput()
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
                self.dispatch_message(message_type, message_content)
            else:
                print("[Render][Sub] " + str(line, encoding="utf-8"))

    def dispatch_message(self, command, message):
        if command == b"WINID":
            winid, _ = QByteArray(message).toLongLong()
            self.create_window.emit(winid, self)

    @Slot(bytes)
    def write(self, message):
        res = self.process.write(message + b"\n")
        print(res)


@Slot(int, SubprocessWorker)
def create_window(winid, worker):
    mdiarea = Gui.getMainWindow().centralWidget()

    all_windows = QGuiApplication.instance().allWindows()
    main_qwindow = next(
        w
        for w in all_windows
        if w.objectName() == "Gui::MainWindowClassWindow"
    )

    window = QWindow.fromWinId(winid)
    container = QWidget.createWindowContainer(
        window, None, Qt.FramelessWindowHint | Qt.Window
    )

    subw = mdiarea.addSubWindow(container)

    container.show()
    worker.write_to_process.emit(b"@@START@@")


def start_subapp(script, options=None):
    # Process arguments
    script = str(script)
    options = options or []
    options = list(options)

    python = get_venv_python()
    args = ["-u", script] + options

    worker = SubprocessWorker(python, args)
    worker.create_window.connect(create_window)
    executor = RendererExecutor(worker)
    executor.start()


def start_help():
    script = os.path.join(PKGDIR, "help.py")
    script = os.path.normpath(script)
    wbdir = os.path.normpath(WBDIR)
    options = [wbdir]
    start_subapp(script, options)
