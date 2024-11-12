# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2022 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
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
    QFileDialog,
    QApplication,
)
from PySide.QtCore import Qt, Slot, QSize, QPoint

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
        self.imglabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imglabel.setScaledContents(True)  # Resize pixmap along with label
        self.imglabel.setAlignment(Qt.AlignCenter)
        self.imglabel.setText("(No image yet)")

        self.namelabel = QLabel()

        self.scrollarea = QScrollArea()
        self.scrollarea.setWidget(self.imglabel)
        self.scrollarea.setWidgetResizable(False)
        self.scrollarea.setAlignment(Qt.AlignCenter)
        self.previous_scrollarea_wheel = self.scrollarea.wheelEvent

        # Scrollarea: do not handle CTRL+Wheel
        def handle_wheel(event):
            if event.modifiers() == Qt.CTRL:
                event.ignore()
            else:
                self.previous_scrollarea_wheel(event)
                event.accept()

        setattr(self.scrollarea, "wheelEvent", handle_wheel)

        self.layout().addWidget(self.scrollarea)
        self.layout().addWidget(self.namelabel)

        self.scale_factor = 1.0
        self._initial_size = QSize(0, 0)
        self._img_path = ""

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.menu = QMenu()
        self.add_actions_to_menu(self.menu)

    def add_actions_to_menu(self, menu):
        """Add widget actions to a given menu.

        Args:
            menu -- the menu to add the actions (QMenu)
        """
        zoom_in_act = menu.addAction("Zoom In (25%)")
        zoom_in_act.triggered.connect(self.zoom_in)

        zoom_out_act = menu.addAction("Zoom Out (25%)")
        zoom_out_act.triggered.connect(self.zoom_out)

        zoom_normal_act = menu.addAction("Normal Size")
        zoom_normal_act.triggered.connect(self.normal_size)

        menu.addSeparator()

        saveas_act = menu.addAction("Save Image as...")
        saveas_act.triggered.connect(self.save_image_as)

        copy_filename_act = menu.addAction("Copy Image to Clipboard")
        copy_filename_act.triggered.connect(self.copy_image)

        copy_filename_act = menu.addAction("Copy Filename to Clipboard")
        copy_filename_act.triggered.connect(self.copy_filename)

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
        zoom_limits = (factor > 1.0 and self.scale_factor < 3.0) or (
            factor < 1.0 and self.scale_factor > 0.2
        )
        if zoom_limits:
            self.scale_factor *= float(factor)
            new_size = self.scale_factor * self._initial_size
            self.resize_image(new_size)

    def adjust_scrollbars(self, factor):
        """Adjust scrollbars of scroll area to zoom factor."""
        factor = float(factor)
        scrollbars = [
            self.scrollarea.horizontalScrollBar(),
            self.scrollarea.verticalScrollBar(),
        ]
        for scrollbar in scrollbars:
            value = float(scrollbar.value())
            pagestep = float(scrollbar.pageStep())
            scrollbar.setValue(
                round(factor * value + (factor - 1.0) * pagestep / 2.0)
            )

    @Slot()
    def zoom_in(self):
        """Zoom embedded image in (slot)."""
        self.scale_image(1.25)

    @Slot()
    def zoom_out(self):
        """Zoom embedded image out (slot)."""
        self.scale_image(0.8)

    def zoom_from_wheel(self, num_steps):
        """Zoom from wheel event."""
        steps = num_steps.y() / 120
        if steps > 0:
            scale = 1.25**steps
        elif steps < 0:
            scale = 0.80 ** (-steps)
        else:
            return
        self.scale_image(scale)
        self.adjust_scrollbars(scale)

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
    def save_image_as(self):
        """Save embedded image as file (slot)."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save F:xile",
            None,
            "Images (*.png *.xpm *.jpg)",
        )
        pixmap = self.imglabel.pixmap()
        pixmap.save(filename)

    @Slot(QPoint)
    def show_context_menu(self, pos):
        """Show context menu."""
        self.menu.exec_(self.mapToGlobal(pos))

    def wheelEvent(self, event):
        """Catch wheel event (callback)."""
        if event.modifiers() != Qt.CTRL:
            event.ignore()
            return

        num_pixels = event.pixelDelta()
        num_degrees = event.angleDelta() / 8

        if num_pixels is not None:
            self.zoom_from_wheel(num_pixels)
        elif num_degrees is not None:
            num_steps = num_degrees / 15
            self.zoom_from_wheel(num_steps)

        event.accept()


@Slot(str)
def display_image(img_path):
    """Display an image in FreeCAD Gui, using MDI (slot).

    This slot is intended to be connected to renderer executor worker's
    'result_ready' signal.
    It creates a MDI subwindow in FreeCAD Gui and embeds an ImageViewer into
    it.
    """
    if not img_path:
        return

    # Create widget and subwindow
    viewer = ImageViewer(None)
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("Rendering result")
    subw.setVisible(True)

    # Set subwindow background to opaque
    try:
        bkg = Gui.getMainWindow().palette().color(QPalette.Background)
    except AttributeError:
        # Qt6
        bkg = Gui.getMainWindow().palette().color(QPalette.ColorRole.Window)
    style = (
        "QMdiSubWindow {"
        f"background-color:rgb({bkg.red()},{bkg.green()},{bkg.blue()});"
        "border-style:none;"
        "margin:0px;"
        "}"
    )
    subw.setStyleSheet(style)

    # Create context menu
    menu = subw.systemMenu()
    menu.addSeparator()
    subw.widget().add_actions_to_menu(menu)

    # Load image and show window
    subw.widget().load_image(img_path)
    subw.showMaximized()
