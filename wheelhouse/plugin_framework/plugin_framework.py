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

"""This module implements a framework for Render plugins.

A plugin is an applet that can be launched by Render in a separate process,
with an access to Render virtual environment.
"""
import sys
import os
import signal
import argparse
from multiprocessing.connection import Client, wait
from threading import Thread, Event
from dataclasses import dataclass


sys.path.append(os.getcwd())


# Partially parse command line
plugin_parser = argparse.ArgumentParser()
plugin_parser.add_argument(
    "--server",
    help="the communication server name",
    type=str,
)
plugin_parser.add_argument(
    "--pyside",
    help="pyside version",
    type=str,
    choices=("PySide2", "PySide6"),
)
PLUGIN_ARGS, ARGS = plugin_parser.parse_known_args()
PYSIDE = PLUGIN_ARGS.pyside
SERVERNAME = PLUGIN_ARGS.server

if PYSIDE == "PySide2":
    from PySide2.QtCore import QObject, QTimer, Slot, Signal, Qt, QThread
    from PySide2.QtWidgets import QApplication, QMainWindow, QMessageBox

if PYSIDE == "PySide6":
    from PySide6.QtCore import QObject, QTimer, Slot, Signal, Qt, QThread
    from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs
            )
        return cls._instances[cls]


class Socket(object, metaclass=Singleton):
    """A socket to listen to parent process."""

    def __init__(self):
        """Initialize socket."""
        # Communication
        self._connection = Client(SERVERNAME)
        self._connection_active = Event()
        self._connection_active.set()
        self._connection_listener = Thread(target=self.recv)
        self._connection_listener.start()
        self._close_event = Event()
        self._close_event.clear()

    def send(self, verb, argument):
        """Send message to parent process."""
        message = (verb, argument)
        self._connection.send(message)

    def recv(self):
        """Receive messages from parent process."""
        while self._connection_active.is_set():
            # We use wait to get a timeout parameter
            for conn in wait([self._connection], timeout=1):
                try:
                    message = conn.recv()
                except EOFError:
                    self._connection_active.clear()
                else:
                    verb, argument = message

                    # Handle
                    if verb == "CLOSE":
                        self._close_event.set()
                        self._connection_active.clear()

    def close(self):
        """Close socket."""
        self._connection_active.clear()
        self._connection_listener.join()

    def wait_for_close(self):
        """Wait for close event."""
        self._close_event.wait()


SOCKET = Socket()
signal.signal(signal.SIGTERM, signal.SIG_DFL)


class RenderPlugin(QApplication):
    """Plugin base class."""

    quit_plugin = Signal()

    def __init__(self, widget, *args):
        """Initialize plugin."""
        super().__init__()

        # Application and window
        self.aboutToQuit.connect(self.close_socket)
        self.mainwindow = QMainWindow(flags=Qt.FramelessWindowHint)
        self.mainwindow.showMaximized()

        # Close listener
        self.quit_plugin.connect(self.close_and_quit)
        self.close_thread = Thread(target=self.wait_for_close)
        self.close_thread.start()

        # Central widget
        try:
            self.widget = widget(*args)
        except:
            print("WARNING: Could not initialize plugin central widget")
            self.widget = None
        else:
            self.widget.setParent(self.mainwindow)

    @Slot()
    def add_widget(self):
        """Add viewer (once application has been started)."""
        if self.widget:
            self.mainwindow.setCentralWidget(self.widget)
            self.widget.showMaximized()
            self.widget.setVisible(True)
        winid = self.mainwindow.winId()
        SOCKET.send("WINID", winid)

    def wait_for_close(self):
        """Wait for close event from socket."""
        SOCKET.wait_for_close()
        self.quit_plugin.emit()

    @Slot()
    def close_and_quit(self):
        """Quit application."""
        self.closeAllWindows()
        self.quit()

    @Slot()
    def close_socket(self):
        """Close socket (to be called in aboutToQuit)."""
        SOCKET.close()

    def exec(self):
        """Execute application (start event loop)."""
        QTimer.singleShot(0, self.add_widget)
        if PYSIDE == "PySide2":
            return super().exec_()
        if PYSIDE == "PySide6":
            return super().exec()


@dataclass
class Bcolors:
    """Blender terminal colors."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    COLOROFF = "\033[0m"


def log(msg):
    """Print message as log."""
    print(f"{Bcolors.OKBLUE}{msg}{Bcolors.COLOROFF}", file=sys.stdout)


def msg(msg):
    """Print message as plain message."""
    print(f"{Bcolors.COLOROFF}{msg}{Bcolors.COLOROFF}", file=sys.stdout)


def warn(msg):
    """Print message as warning."""
    print(f"{Bcolors.WARNING}{msg}{Bcolors.COLOROFF}", file=sys.stderr)


def error(msg):
    """Print message as error."""
    print(f"{Bcolors.FAIL}{msg}{Bcolors.COLOROFF}", file=sys.stderr)
