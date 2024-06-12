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
import signal
import argparse
from multiprocessing.connection import Client, wait
from threading import Thread, Event


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
    from PySide2.QtCore import QObject, QTimer, Slot, Signal, Qt
    from PySide2.QtWidgets import QApplication, QMainWindow

if PYSIDE == "PySide6":
    from PySide6.QtCore import QObject, QTimer, Slot, Signal, Qt
    from PySide6.QtWidgets import QApplication, QMainWindow


class RenderPlugin(QObject):

    bye = Signal()

    def __init__(self, widget, *args):
        super().__init__()

        # Communication
        self.connection = Client(SERVERNAME)
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

        # Central widget
        try:
            self.widget = widget(*args)
        except:
            self.widget = None
        else:
            self.widget.setParent(self.mainwindow)
            self.widget.setVisible(True)

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
    def add_widget(self):
        """Add viewer (once application has been started)."""
        if self.widget:
            self.mainwindow.setCentralWidget(self.widget)
            self.widget.showMaximized()
        winid = self.mainwindow.winId()
        self.parent_send("WINID", winid)

    def exec(self):
        """Execute application (start event loop)."""
        QTimer.singleShot(0, self.add_widget)
        if PYSIDE == "PySide6":
            return self.app.exec()
        else:
            return self.app.exec_()
