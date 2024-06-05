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

"""This module implements a renderer executor object for Render workbench.

The renderer executor allows to run a rendering engine in a responsive,
non-blocking way, provided a command line that should have been generated by a
renderer plugin, and optionnally to display the rendering result (image) in
FreeCAD graphical user interface.
"""

import threading
import shlex
import traceback
from subprocess import Popen, PIPE, STDOUT, SubprocessError

from PySide.QtCore import (
    QThread,
    Signal,
    Slot,
    QObject,
    QCoreApplication,
    QEventLoop,
    QMetaObject,
    Qt,
)

import FreeCAD as App

from Render.imageviewer import display_image


class RendererWorker(QObject):
    """Worker class to run renderer.

    This class embeds the treatment to be executed to run renderer in separate
    thread.
    """

    finished = Signal(int)
    result_ready = Signal(str)  # Triggered when result is ready for display

    def __init__(self, cmd, img, cwd, open_after_render):
        """Initialize worker.

        Args:
            cmd -- command to execute (str)
            img -- path to resulting image (the renderer output) (str)
            cwd -- directory where to execute subprocess
            open_after_render -- flag to make GUI open rendered image (bool)
        """
        super().__init__()
        self.cmd = cmd
        self.img = img
        self.cwd = cwd
        if open_after_render:
            self.result_ready.connect(display_image)

    def run(self):
        """Run worker.

        This method represents the thread activity. It is not intended to be
        called directly, but via thread's run() method.
        """
        message = App.Console.PrintMessage
        warning = App.Console.PrintWarning
        error = App.Console.PrintError
        result_ready = self.result_ready.emit

        message(f"Starting rendering...\n{self.cmd}\n")
        try:
            # Main loop
            with Popen(
                shlex.split(self.cmd),
                stdout=PIPE,
                stderr=STDOUT,
                bufsize=1,
                universal_newlines=True,
                cwd=self.cwd,
            ) as proc:
                for line in proc.stdout:
                    message(line)
        except (OSError, SubprocessError) as err:
            errclass = err.__class__.__name__
            errmsg = str(err)
            error(f"{errclass}: {errmsg}\n")
            message("Aborting rendering...\n")
        else:
            rcode = proc.returncode
            msg = f"Exiting rendering - Return code: {rcode}\n"
            if not rcode:
                message(msg)
            else:
                warning(msg)

            # Open result in GUI if relevant
            if self.img:
                if App.GuiUp:
                    result_ready(self.img)
                else:
                    message(f"Output file written to '{self.img}'\n")

            # Terminate (for Qt)
            self.finished.emit(rcode)


class ExporterWorker(QObject):
    """Worker class to export scene.

    This class embeds the treatment to be executed to export scene in separate
    thread.
    """

    finished = Signal(int)

    def __init__(self, func, args, errormsg=None):
        """Initialize worker.

        Args:
            func -- function to run (callable)
            args -- arguments to pass (tuple)
            errormsg -- error message
        """
        super().__init__()
        self.func = func
        self.args = args
        self.lock = threading.Lock()
        self.res = []
        self.errormsg = (
            errormsg or "[Render][Objstrings] /!\\ EXPORT ERROR /!\\\n"
        )

    @Slot()
    def run(self):
        """Run worker.

        This method represents the thread activity. It is not intended to be
        called directly, but via thread's run() method.
        """
        try:
            res = self.func(*self.args)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            App.Console.PrintError(self.errormsg)
            traceback.print_exception(exc)
        else:
            with self.lock:
                self.res = res
        finally:
            # Terminate (for Qt)
            self.finished.emit(0)

    def result(self):
        """Return result.

        Worker must have been joined before, otherwise behaviour is undefined.
        """
        with self.lock:
            res = self.res
        return res


class RendererExecutorGui(QObject):
    """A class to execute a rendering engine in Graphical User Interface mode.

    This class is designed to run a worker in a separate thread, keeping GUI
    responsive.  Meanwhile, stdout/stderr are piped to FreeCAD console, in such
    a way it is possible to follow the evolution of the work.  To achieve
    that, worker is executed in a separate thread, using **QThread**.
    Nota: in this class, it is assumed that Qt GUI is up, so it is not tested
    anywhere.
    """

    def __init__(self, worker):
        """Initialize executor.

        Args:
            worker -- the worker to run
        """
        super().__init__(QCoreApplication.instance())
        self.thread = QThread()
        self.worker = worker
        self.thread.setObjectName("fcd-renderexec")

    def start(self):
        """Start executor."""
        # Move worker to thread
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.thread.exit)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.thread.finished.connect(lambda: print("Thread finished")) # Dbg

        # Start the thread
        self.thread.start()

    def join(self):
        """Join thread.

        This method is provided for consistency with CLI executor, but it
        should not be of much use in GUI context.
        """
        loop = QEventLoop()
        self.thread.finished.connect(loop.quit)
        if not self.thread.isFinished():
            loop.exec_(flags=QEventLoop.ExcludeUserInputEvents)


class RendererExecutorCli(threading.Thread):
    """A class to execute a rendering engine in Command Line Interface mode.

    This class is designed to run a renderer in a separate thread, keeping CLI
    responsive.  Meanwhile, stdout/stderr are piped to FreeCAD console, in such
    a way it is possible to follow the evolution of the rendering.  To achieve
    that, renderer is executed in a separate thread, using **Python threads**.
    """

    def __init__(self, worker):
        """Initialize executor.

        Args:
            worker -- the worker to run
        """
        super().__init__()
        self.worker = worker

    def run(self):
        """Run thread.

        This method represents the thread activity. It is not intended to be
        called directly, but via Thread.start().
        """
        self.worker.run()


def exec_in_mainthread(func, *args):
    """Execute a function in the main thread.

    Some methods of FreeCAD API require to be executed in main thread.
    This function provides a way to do so.
    """
    worker = ExporterWorker(func, *args)
    main_thread = QCoreApplication.instance().thread()
    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    worker.moveToThread(main_thread)
    QMetaObject.invokeMethod(worker, "run", Qt.QueuedConnection)
    loop.exec_()
    return worker.result()


RendererExecutor = RendererExecutorGui if App.GuiUp else RendererExecutorCli
