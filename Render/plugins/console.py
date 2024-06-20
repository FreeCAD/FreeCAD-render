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

"""This module implements an embedded console (debugging purpose)."""

import sys
import argparse

from renderplugin import RenderPluginApplication, ARGS, PYSIDE

if PYSIDE == "PySide6":
    from PySide6.QtWidgets import QWidget, QVBoxLayout
    from PySide6.QtCore import QProcess
if PYSIDE == "PyQt6":
    from PyQt6.QtWidgets import QWidget, QVBoxLayout
    from PyQt6.QtCore import QProcess


class Terminal(QWidget):
    def __init__(self, terminal):
        super().__init__()
        self.process = QProcess(self)
        self.terminal = QWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.terminal)
        wid = str(int(self.terminal.winId()))
        if terminal == "uxrvt":
            options = ["-embed", wid]
        elif terminal == "xterm":
            options = ["-into", wid]
        else:
            options = ["-embed", wid]
        self.process.start(terminal, options)

    def closeEvent(self, event):
        self.process.terminate()
        self.process.waitForFinished(1000)


def main():
    """Entry point."""
    # Get arguments
    parser = argparse.ArgumentParser(
        prog="Render help",
        description="Open a terminal emulator",
    )
    parser.add_argument(
        "--term",
        help="the terminal emulator to open",
        type=str,
    )
    args = parser.parse_args(ARGS)
    application = RenderPluginApplication(Terminal, args.term)
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
