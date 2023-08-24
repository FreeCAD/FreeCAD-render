# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2023 Howetuft <howetuft@gmail.com>                      *
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

"""This module implements Render Preferences Page.

The preferences page of Render is implemented as a widget, rather than a mere
traditional ui file. The rationale is to add some enhanced features (like
testing renderers pathes...) that are not supported by ui file. However, an
underlying ui file is still used, embedded in the widget, as it is a convenient
way to describe the layout.
"""

import subprocess

from PySide.QtGui import (
    QWidget,
    QCheckBox,
    QRadioButton,
    QComboBox,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QStyle,
    QSpacerItem,
    QSizePolicy,
)
from PySide.QtCore import Slot, QObject

import FreeCAD as App
import FreeCADGui as Gui

from Render.constants import PREFPAGE
from Render.rdrhandler import RendererHandler


# ===========================================================================
#                                Main class
# ===========================================================================


class PreferencesPage(QWidget):
    """A custom widget to display a preferences page.

    This widget is suitable as an input to `FreeCADGui.addPreferencePage`.
    Inspired by FreeCAD/src/Mod/AddonManager/AddonManagerOptions.py (thanks)
    """

    def __init__(self, parent=None):
        """Initialize widget.

        Structure of the widget is taken from ui file.
        """
        # Create layout
        super().__init__(parent)
        page = Gui.PySideUic.loadUi(PREFPAGE, self)
        self.setLayout(page.layout())
        self.setWindowTitle(page.windowTitle())

        # Connect test buttons
        test_buttons = (
            "AppleseedCli_Test",
            "AppleseedStudio_Test",
            "Cycles_Test",
            "LuxcoreCli_Test",
            "LuxcoreUi_Test",
        )

        for name in test_buttons:
            button = self.findChild(QPushButton, name)
            button.clicked.connect(self.test_dispatcher)


    def loadSettings(self):  # pylint: disable=invalid-name
        """Load settings to widget (callback).

        Required function: called by the preferences dialog when it is
        launched, loads the preference data and assigns it to the subwidgets.

        Actual logic is written in a separate helper, to allow both recursive
        implementation and easier debugging.
        """
        _load_settings_helper(self)

    def saveSettings(self):  # pylint: disable=invalid-name
        """Save settings from widget (callback).

        Required function: called by the preferences dialog when Apply or Save
        is clicked, saves out the preference data by reading it from the
        widget.

        Actual logic is written in a separate helper, to allow both recursive
        implementation and easier debugging.
        """
        _save_settings_helper(self)

    @Slot()
    def test_dispatcher(self):
        """Dispatch test requests (slot).

        Renderer information is extracted from sender widget, which owns them
        as dynamic properties (see ui file).

        Treatment logic is then written in a separate helper, for debugging
        purpose.
        """
        sender = self.sender()
        renderer = sender.property("renderer")
        batch = sender.property("batch")
        _test_dispatcher_helper(renderer, batch, self)


# ===========================================================================
#                                Helpers
# ===========================================================================


def _load_settings_helper(widget):
    """Load settings to a widget (helper).

    Containers are handled in a recursive way.
    """
    # One of ours?
    try:
        pref_path = widget.property("prefPath").data()
        pref_entry = widget.property("prefEntry").data()
    except AttributeError:
        # Not one of ours: pass
        pass
    else:
        # One of ours: fill
        pref = App.ParamGet(
            f"User parameter:BaseApp/Preferences/{str(pref_path,'utf-8')}"
        )
        pref_entry = str(pref_entry, "utf-8")
        if isinstance(widget, QCheckBox):
            widget.setChecked(pref.GetBool(pref_entry))
        elif isinstance(widget, QRadioButton):
            if pref.GetBool(pref_entry):
                widget.setChecked(True)
        elif isinstance(widget, QComboBox):
            new_index = pref.GetInt(pref_entry)
            widget.setCurrentIndex(new_index)
        elif isinstance(widget, QTextEdit):
            text = pref.GetString(pref_entry)
            widget.setText(text)
        elif isinstance(widget, QLineEdit):
            text = pref.GetString(pref_entry)
            widget.setText(text)
        elif widget.metaObject().className() == "Gui::PrefFileChooser":
            filename = pref.GetString(pref_entry)
            widget.setProperty("fileName", filename)
        elif widget.metaObject().className() == "Gui::PrefSpinBox":
            value = pref.GetInt(pref_entry)
            widget.setProperty("value", value)
        else:
            raise NotImplementedError(widget.metaObject().className())

    # Recurse over children
    for subwidget in widget.children():
        _load_settings_helper(subwidget)


def _save_settings_helper(widget):
    """Save settings from a widget (helper).

    Containers are handled in a recursive way.
    """
    # One of ours?
    try:
        pref_path = widget.property("prefPath").data()
        pref_entry = widget.property("prefEntry").data()
    except AttributeError:
        # Not one of ours: pass
        pass
    else:
        # One of ours: fill
        pref = App.ParamGet(
            f"User parameter:BaseApp/Preferences/{str(pref_path,'utf-8')}"
        )
        pref_entry = str(pref_entry, "utf-8")
        if isinstance(widget, QCheckBox):
            pref.SetBool(pref_entry, widget.isChecked())
        elif isinstance(widget, QRadioButton):
            pref.SetBool(pref_entry, widget.isChecked())
        elif isinstance(widget, QComboBox):
            pref.SetInt(pref_entry, widget.currentIndex())
        elif isinstance(widget, QTextEdit):
            pref.SetString(pref_entry, widget.toPlainText())
        elif isinstance(widget, QLineEdit):
            pref.SetString(pref_entry, widget.text())
        elif widget.metaObject().className() == "Gui::PrefFileChooser":
            pref.SetString(pref_entry, str(widget.property("fileName")))
        elif widget.metaObject().className() == "Gui::PrefSpinBox":
            pref.SetInt(pref_entry, widget.property("value"))
        else:
            raise NotImplementedError(widget.metaObject().className())

    # Recurse over children
    for subwidget in widget.children():
        _save_settings_helper(subwidget)


def _show_result(success, informative, detailed, parent):
    """Show result of test.

    Result is shown in a QMessageBox.
    """
    # Create message box
    msgbox = QMessageBox(parent)
    msgbox.setWindowTitle("Test Renderer Path")

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


def _test_dispatcher_helper(renderer, batch, parent):
    """Dispatch test request to renderer and run test.

    Args:
        renderer -- the renderer name (str, as expected by rdrhandler)
        batch -- flag to run the CLI (True) or GUI (false) favor of
          the renderer
        parent -- the parent widget
    """
    # Save settings
    parent.saveSettings()

    # Build renderer handler and get test command line
    handler = RendererHandler(renderer)
    cmdline = handler.test_cmdline(batch)

    # Run command
    try:
        result = subprocess.run(cmdline, capture_output=True, timeout=5)
    except FileNotFoundError:
        _show_result(False, f"File not found ('{cmdline[0]}')", "", parent)
        return


    # Print result
    msgbox = QMessageBox(parent)
    informative = (
        f"File: '{cmdline[0]}'"
        "\n\n"
        f"Return code: {result.returncode}"
    )
    detailed = (
        f"$> {' '.join(cmdline)}\n",
        "\n",
        f"{result.stdout.decode()}\n",
        f"{result.stderr.decode()}\n",
        "\n",
        f"Return code: {result.returncode}",
    )
    detailed = ''.join(detailed)
    _show_result(not result.returncode, informative, detailed, parent)


# TODO
def _test_renderer(rdrpath, args=["--version"]):
    """Test a renderer setting.

    Run the renderer with the given path to check whether
    the installation is correct.
    """
    args = list(args)
    cmdline = [rdrpath] + args
    # TODO Add timeout
    completed_process = subprocess.run(cmdline, capture_output=True)
    return completed_process
