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

"""This module implements an image file viewer widget.

In addition, it provides a (Qt) slot to display this widget into FreeCAD GUI,
using MDI.
"""

from PySide.QtGui import (
    QLabel,
    QPixmap,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QPalette,
    QSizePolicy,
    QGuiApplication,
    QMenu,
)
from PySide.QtCore import Qt, Slot, QSize

import FreeCADGui as Gui


class ImageViewer(QWidget):
    """A custom widget to display an image in Gui."""

    # Inspired by :
    # https://doc.qt.io/qt-6/qtwidgets-widgets-imageviewer-example.html
    # https://code.qt.io/cgit/pyside/pyside-setup.git/tree/examples/widgets/imageviewer

    def __init__(self, parent=None):
        """Initialize Widget."""
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.imglabel = QLabel()
        self.imglabel.setBackgroundRole(QPalette.Base)
        self.imglabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.namelabel = QLabel()

        self.scrollarea = QScrollArea()
        self.scrollarea.setWidget(self.imglabel)
        self.scrollarea.setWidgetResizable(False)
        self.imglabel.setScaledContents(True)  # Resize pixmap along with label
        self.imglabel.setAlignment(Qt.AlignCenter)

        self.layout().addWidget(self.scrollarea)
        self.layout().addWidget(self.namelabel)
        self.imglabel.setText("(No image yet)")

        self.scale_factor = 1.0
        self._initial_size = QSize(0, 0)
        self._img_path = ""

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # pylint: disable=no-member
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.menu = QMenu()
        self.add_actions_to_menu(self.menu)

    def add_actions_to_menu(self, menu):
        """Add widget actions to a given menu.

        Args:
            menu -- the menu to add the actions (QMenu)
        """
        zoom_in_act = menu.addAction("Zoom &In (25%)")
        zoom_in_act.triggered.connect(self.zoom_in)

        zoom_out_act = menu.addAction("Zoom &Out (25%)")
        zoom_out_act.triggered.connect(self.zoom_out)

        zoom_normal_act = menu.addAction("&Normal Size")
        zoom_normal_act.triggered.connect(self.normal_size)

        menu.addSeparator()

        copy_filename_act = menu.addAction("Copy &Filename to Clipboard")
        copy_filename_act.triggered.connect(self.copy_filename)

        copy_filename_act = menu.addAction("Copy &Image to Clipboard")
        copy_filename_act.triggered.connect(self.copy_image)

    def load_image(self, img_path):
        """Load an image in widget from a file.

        Args:
            img_path -- Path of image file to load (str)
        """
        img_path = str(img_path)
        pixmap = QPixmap(img_path)
        self.imglabel.setPixmap(pixmap)
        self.imglabel.resize(pixmap.size())
        self.namelabel.setText(f"File: {img_path}")
        self._img_path = img_path
        self._initial_size = pixmap.size()

    def resize_image(self, new_size=None):
        """Resize embedded image to target size.

        Args:
            new_size -- target size to resize image to (QSize)
        """
        if not new_size:
            new_size = self._initial_size
            self.scale_factor = 1.0
        new_size = QSize(new_size)
        self.imglabel.setMinimumSize(new_size)
        self.imglabel.setMaximumSize(new_size)

    def scale_image(self, factor):
        """Rescale embedded image applying a factor.

        Factor is applied relatively to current scale.

        Args:
            factor -- Factor to apply (float)
        """
        self.scale_factor *= float(factor)
        new_size = self.scale_factor * self._initial_size
        self.resize_image(new_size)

    @Slot()
    def zoom_in(self):
        """Zoom embedded image in (slot)."""
        self.scale_image(1.25)

    @Slot()
    def zoom_out(self):
        """Zoom embedded image out (slot)."""
        self.scale_image(0.8)

    @Slot()
    def normal_size(self):
        """Set embedded image scale to 1:1 (slot)."""
        self.resize_image()

    @Slot()
    def copy_filename(self):
        """Copy file name to clipboard (slot)."""
        QGuiApplication.clipboard().setText(self._img_path)

    @Slot()
    def copy_image(self):
        """Copy embedded image to clipboard (slot)."""
        QGuiApplication.clipboard().setImage(self.imglabel.pixmap().toImage())

    @Slot()
    def show_context_menu(self, pos):
        """Show context menu."""
        self.menu.exec_(self.mapToGlobal(pos))


@Slot()
def display_image(img_path):
    """Display an image in FreeCAD Gui, using MDI (slot).

    This slot is intended to be connected to renderer executor worker's
    'result_ready' signal.
    It creates a MDI subwindow in FreeCAD Gui and embeds an ImageViewer into
    it.
    """
    # Create widget and subwindow
    viewer = ImageViewer()
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("Rendering result")
    subw.setVisible(False)

    # Create contextual menu
    menu = subw.systemMenu()
    menu.addSeparator()
    subw.widget().add_actions_to_menu(menu)

    # Load image and show window
    subw.widget().load_image(img_path)
    subw.showMaximized()
