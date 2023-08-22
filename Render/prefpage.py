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

from PySide.QtGui import (
    QWidget,
    QCheckBox,
    QRadioButton,
    QComboBox,
    QTextEdit,
    QLineEdit,
)

import FreeCAD as App
import FreeCADGui as Gui

from Render.constants import PREFPAGE


class PreferencesPage(QWidget):
    """A custom widget to display a preferences page.

    Inspired by FreeCAD/src/Mod/AddonManager/AddonManagerOptions.py (thanks)
    """

    def __init__(self, parent=None):
        """Initialize widget.

        Structure of the widget is taken from ui file.
        """
        super().__init__(parent)
        page = Gui.PySideUic.loadUi(PREFPAGE, self)
        self.setLayout(page.layout())
        self.setWindowTitle(page.windowTitle())

    def loadSettings(self):  # pylint: disable=invalid-name
        """Load settings to widget (callback).

        Required function: called by the preferences dialog when it is
        launched, loads the preference data and assigns it to the subwidgets.

        Actual logic is coded in a separate helper, to allow both recursive
        implementation and easier debugging.
        """
        _load_settings_helper(self)

    def saveSettings(self):  # pylint: disable=invalid-name
        """Save settings from widget (callback).

        Required function: called by the preferences dialog when Apply or Save
        is clicked, saves out the preference data by reading it from the
        widget.

        Actual logic is coded in a separate helper, to allow both recursive
        implementation and easier debugging.
        """
        _save_settings_helper(self)


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
