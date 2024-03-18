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

"""This module implements an installer for materialx."""


from PySide.QtWidgets import QMessageBox
from PySide.QtGui import QStyle, QSpacerItem, QSizePolicy

import FreeCAD as App
import FreeCADGui as Gui

from Render.utils import pip_install

translate = App.Qt.translate


def propose_install():
    """Propose MaterialX installation."""
    msg = translate(
        "Render",
        "Error: Cannot find MaterialX framework!\n\n"
        "Do you want Render to try to install MaterialX?",
    )
    res = QMessageBox.critical(
        Gui.getMainWindow(),
        translate("Render", "Render - MaterialX"),
        msg,
        buttons=QMessageBox.Yes | QMessageBox.No,
    )
    if res == QMessageBox.Yes:
        _install_materialx()


def _install_materialx():
    """Install MaterialX (with pip)."""
    res = pip_install("materialx")
    success = res.returncode == 0
    informative = (
        translate("Render", "Successful installation")
        if success
        else translate(
            "Render",
            f"Installation failed - pip returned code '{res.returncode}'.\n\n"
            "See details below...",
        )
    )
    detailed = res.stdout
    _show_result(success, informative, detailed, Gui.getMainWindow())


def _show_result(success, informative, detailed, parent):
    """Show result of the install.

    Result is shown in a QMessageBox.
    """
    # Create message box
    msgbox = QMessageBox(parent)
    msgbox.setWindowTitle("Install MaterialX")

    # Populate
    if bool(success):
        msgbox.setText("SUCCESS")
        pixmapi = QStyle.SP_DialogApplyButton
        icon = parent.style().standardIcon(pixmapi)
        msgbox.setIconPixmap(icon.pixmap(64))
    else:
        msgbox.setText("ERROR")
        pixmapi = QStyle.SP_DialogCancelButton
        icon = parent.style().standardIcon(pixmapi)
        msgbox.setIconPixmap(icon.pixmap(64))
    msgbox.setInformativeText(informative)
    msgbox.setDetailedText(detailed)

    # Resize
    hspacer = QSpacerItem(500, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    layout = msgbox.layout()
    layout.addItem(hspacer, layout.rowCount(), 0, 1, layout.columnCount())

    # Execute
    msgbox.exec()
