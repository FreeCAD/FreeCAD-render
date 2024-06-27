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

"""This module implements a web viewer for MaterialX as a Render plugin.

Workflow is:
- choose
- download
- convert (from materialx to fccard)
- import (into FreeCAD)
"""

import os.path
from urllib.parse import urlparse
import argparse
import sys
import pathlib


from qtpy import PYQT5, PYQT6, PYSIDE2, PYSIDE6
from qtpy.QtCore import (
    Slot,
    Qt,
    Signal,
    QUrl,
    QEvent,
    QDir,
)
from qtpy.QtWidgets import (
    QWidget,
    QToolBar,
    QVBoxLayout,
    QMessageBox,
    QLabel,
    QFileDialog,
)
from qtpy.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEnginePage,
    QWebEngineProfile,
)

from materialx.downloader import MaterialXDownloadWindow, HdriDownloadWindow
from materialx.polyhaven import polyhaven_getsize

from renderplugin import (
    ARGS,
    RenderPluginApplication,
    msg,
    log,
    SOCKET,
    PluginMessageEvent,
)

if PYQT5:
    from PyQt5.QtWebEngineWidgets import QWebEngineDownloadItem
elif PYSIDE2:
    from PySide2.QtWebEngineWidgets import QWebEngineDownloadItem
elif PYQT6:
    from PyQt6.QtWebEngineCore import (
        QWebEngineDownloadRequest as QWebEngineDownloadItem,
    )
elif PYSIDE6:
    from PySide6.QtWebEngineCore import (
        QWebEngineDownloadRequest as QWebEngineDownloadItem,
    )
else:
    raise ImportError()


MX_EVENT_TYPE = QEvent.registerEventType()

# Remark: please do not use:
# - QWebEngineProfile.setDownloadPath
# - QWebEngineDownloadItem.downloadFileName
# - QWebEngineDownloadItem.downloadDirectory
# as they may not be compatible with old PySide (and old Ubuntu)
# (2024-04-24)


class WebChooser(QWidget):
    """A MaterialX website chooser widget.

    This is an embedded html viewer that catches download requests and triggers
    MaterialX import accordingly.
    """

    _download_required = Signal(QWebEngineDownloadItem)
    release_material_signal = Signal()

    def __init__(self, url, temp_path, disp2bump=False):
        """Initialize chooser."""
        super().__init__()
        self.disp2bump = disp2bump
        self.temp_path = temp_path

        self.setLayout(QVBoxLayout())
        self.profile = QWebEngineProfile()

        # Set subwidgets
        self.toolbar = QToolBar(self)
        self.layout().addWidget(self.toolbar)
        self.view = QWebEngineView(self)
        self.page = QWebEnginePage(self.profile, self)
        self.page.javaScriptConsoleMessage = _nope  # Hide console messages
        self.view.setPage(self.page)
        self.layout().addWidget(self.view)

        # Set download manager
        self.profile.downloadRequested.connect(self.download_requested)
        self._download_required.connect(self.run_download, Qt.QueuedConnection)

        # Add actions to toolbar
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Back))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Forward))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Reload))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Stop))

        # Set url
        self.view.load(url)

    def setUrl(self, url):  # pylint: disable=invalid-name
        """Set viewer url.

        Args:
            url -- url to set viewer to (QUrl)
        """
        self.view.setUrl(url)

    def __del__(self):
        # Have page released before profile is, and avoid offending message :
        # 'Release of profile requested but WebEnginePage still not deleted.
        # Expect troubles !'
        self.view = None
        self.page = None

    @Slot(QWebEngineDownloadItem)
    def download_requested(self, download):
        """Answer to download_requested signal."""
        # For unknown reason, I can't manage to run a QEventLoop in this
        # slot (perhaps because it is run in WebEngineProfile thread, or
        # because of the accept/cancel mechanism?). As a consequence, the
        # effective code has been moved to another slot which is triggered via
        # a signal and runs in this class context

        # Check origin
        if download.page() != self.page:
            return

        # Exclude save page download
        if download.isSavePageDownload():
            QMessageBox.warning(
                self.parent,
                "MaterialX library import",
                "Save page is not supported",
            )
            download.cancel()
            return
        # Trigger effective download
        self._download_required.emit(download)
        if PYQT5 or PYSIDE2:
            _, filename = os.path.split(download.path())
            download.setPath(os.path.join(self.temp_path, filename))
        elif PYQT6 or PYSIDE6:
            filename = download.downloadFileName()
            download.setDownloadDirectory(self.temp_path)

        download.accept()

    @Slot()
    def run_download(self, download):
        """Run download actually.

        This slot allows to run download in object thread, while
        being triggered from 'download_requested'.
        """
        # Special case: HDRI
        if self._is_hdri_download(download):
            win = HdriDownloadWindow(
                download, self, self.release_material_signal
            )
            win.open()
            return

        # Nominal case: materialx import
        polyhaven_actual_size = polyhaven_getsize(self.page)

        win = MaterialXDownloadWindow(
            download,
            self,
            self.release_material_signal,
            self.disp2bump,
            polyhaven_actual_size,
        )
        win.open()

    def _is_hdri_download(self, download):
        """Check whether download is HDRI (rather than MaterialX)."""
        # Only for a restricted list of sites (ambientcg...)
        url = self.page.url().toString()
        if not (
            (hostname := urlparse(url).hostname)
            and hostname
            in ["ambientcg.com", "acg-download.struffelproductions.com"]
        ):
            return False

        # And only for a restricted list of file extensions
        try:
            _, ext = os.path.splitext(download.path())
        except AttributeError:
            # Qt6
            _, ext = os.path.splitext(download.downloadFileName())
        if ext.lower() not in [".exr", ".jpg"]:
            msg(ext)
            return False

        # Seems to be one of ours
        return True

    def event(self, event):
        """Handle event (Qt callback)."""
        if event.type() == PluginMessageEvent.TYPE:
            verb, _ = event.message
            if verb == "RELEASE":
                self.release_material_signal.emit()
            return True

        return super().event(event)


def _nope(*_):
    """No operation function."""


class LocalChooser(QWidget):
    def __init__(self, tmp):
        super().__init__()
        self.temp_path = tmp
        self.setObjectName("RenderLocalChooser")

        # Subwidgets
        self.setLayout(QVBoxLayout())
        self.label = QLabel(
            "<b><big>Select a MaterialX file:</big></b>", parent=self
        )
        self.filedialog = QFileDialog()
        self.filedialog.setOption(QFileDialog.DontUseNativeDialog, True)
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.filedialog)

        # File dialog settings
        filters = ["MaterialX (*.mtlx *.zip)", "All files (*.*)"]
        self.filedialog.setNameFilters(filters)
        self.filedialog.setDirectory(QDir.home())
        self.setObjectName("RenderLocalChooserFileDialog")
        self.filedialog.setParent(self)

        # Connect
        self.filedialog.finished.connect(self.end)

    @Slot(int)
    def end(self, result):
        SOCKET.send("DETACH", None)
        self.close()


def main():
    """The entry point."""
    # Get arguments
    parser = argparse.ArgumentParser(
        prog="Render MaterialX downloader",
        description="Open a browser to download MaterialX materials",
    )
    parser.add_argument(
        "url",
        help="the url of the site",
        type=str,
    )
    parser.add_argument(
        "--tmp",
        help="a temporary folder",
        type=pathlib.Path,
    )
    args = parser.parse_args(ARGS)

    # Build application and launch
    SOCKET.send("APPNAME", "MaterialX")
    if args.url != "LOCAL":
        application = RenderPluginApplication(
            WebChooser,
            QUrl(args.url),
            str(args.tmp),
        )
    else:
        application = RenderPluginApplication(
            LocalChooser,
            str(args.tmp),
        )
    sys.exit(application.exec())
    log("Exiting plugin")


if __name__ == "__main__":
    main()
