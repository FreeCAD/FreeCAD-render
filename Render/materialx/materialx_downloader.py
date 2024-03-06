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

"""This module implements a downloader for MaterialX."""

import os.path
import traceback

from PySide2.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineDownloadItem,
)
from PySide2.QtCore import Slot, Qt, QThread, Signal, QObject, QEventLoop
from PySide2.QtWidgets import (
    QWidget,
    QToolBar,
    QVBoxLayout,
    QMessageBox,
    QProgressDialog,
)

import FreeCADGui as Gui
import FreeCAD as App

from .materialx_utils import MATERIALX, critical_nomatx
from .materialx_importer import MaterialXImporter


class MaterialXDownloader(QWidget):
    """A MaterialX downloader widget.

    This viewer is an html viewer but is able to download and import MaterialX
    files.
    """

    def __init__(self, fcdoc, parent=None):
        """Initialize HelpViewer."""
        super().__init__(parent)
        self.parent = parent
        self.fcdoc = fcdoc

        self.setLayout(QVBoxLayout())

        # Set subwidgets
        self.toolbar = QToolBar()
        self.layout().addWidget(self.toolbar)
        self.view = QWebEngineView()
        self.profile = QWebEngineProfile()
        self.page = QWebEnginePage(self.profile, parent)
        self.view.setPage(self.page)
        self.layout().addWidget(self.view)

        # Set download manager
        self.profile.setDownloadPath(App.getTempPath())
        self.profile.downloadRequested.connect(self.download_requested)

        # Add actions to toolbar
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Back))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Forward))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Reload))
        self.toolbar.addAction(self.view.pageAction(QWebEnginePage.Stop))

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
        self.page = None

    @Slot()
    def download_requested(self, download):
        """Answer to download_requested signal."""
        # No save page download
        if download.isSavePageDownload():
            QMessageBox.warning(
                self.parent,
                "MaterialX library import",
                "Save page is not supported",
            )
            download.cancel()
            return

        # Open download window
        win = DownloadWindow(download, self.parent)
        win.open()
        download.accept()


class DownloadWindow(QProgressDialog):
    """A simple widget to handle MaterialX download and import from the web.

    This is mainly a QProgressDialog, with ability to trace progress of a
    download from WebEngineProfile and handle import afterwards.
    """

    def __init__(self, download, fcdoc, parent=None):
        parent = Gui.getMainWindow()
        super().__init__(parent)
        self._download = download
        self._fcdoc = fcdoc
        filename = download.downloadFileName()
        self.setWindowTitle("Import from MaterialX Library")
        self.setLabelText(f"Downloading '{filename}'...")
        self.setAutoClose(False)
        self.setAutoReset(False)

        self._download.downloadProgress.connect(self.set_progress)
        self.canceled.connect(download.cancel)
        download.finished.connect(self.finished_download)

        self.thread = None
        self.worker = None

    @Slot()
    def set_progress(self, bytes_received, bytes_total):
        """Set value of widget progress bar."""
        self.setMaximum(bytes_total)
        self.setValue(bytes_received)

    @Slot()
    def finished_download(self):
        """Slot to trigger when download has finished.

        This slot handles import. Import is executed in a separate thread
        to avoid blocking UI.
        """
        self.canceled.disconnect(self.cancel)
        if self._download.state() == QWebEngineDownloadItem.DownloadCancelled:
            print("Download cancelled")
            return
        if (
            self._download.state()
            == QWebEngineDownloadItem.DownloadInterrupted
        ):
            print("Download interrupted")
            return
        assert (
            self._download.state() == QWebEngineDownloadItem.DownloadCompleted
        )
        self.setLabelText(
            f"Importing '{self._download.downloadFileName()}'..."
        )
        filename = os.path.join(
            self._download.downloadDirectory(),
            self._download.downloadFileName(),
        )

        # Start import
        self.setValue(0)
        self.worker = ImporterWorker(filename, self._fcdoc, self.set_progress)
        self.thread = QThread()
        self.canceled.connect(self.worker.cancel, type=Qt.DirectConnection)

        # Move worker to thread
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.thread.exit)

        # Start the thread
        self.thread.start(QThread.IdlePriority)
        loop = QEventLoop()
        self.worker.finished.connect(loop.exit)
        if not self.thread.isFinished():
            res = loop.exec_()
        loop.processEvents()
        if self.worker.canceled() or res:
            self.cancel()
        else:
            self.setLabelText("Done")

        # Finalize (success)
        self.canceled.connect(self.cancel)
        self.setCancelButtonText("Close")


class ImporterWorker(QObject):
    """A worker for import."""

    def __init__(self, filename, fcdoc, progress):
        super().__init__()
        self.filename = filename
        self.importer = MaterialXImporter(self.filename, fcdoc, progress)

    finished = Signal(int)

    def run(self):
        """Run in worker thread."""
        try:
            res = self.importer.run()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            App.Console.PrintError("/!\\ IMPORT ERROR /!\\\n")
            traceback.print_exception(exc)
            self.finished.emit(-1)
        else:
            self.finished.emit(res)

    @Slot()
    def cancel(self):
        """Request importer to cancel."""
        self.importer.cancel()

    def canceled(self):
        """Check whether importer was requested to canceled."""
        return self.importer.canceled()


def open_mxdownloader(url, doc):
    """Open a downloader."""
    if not App.GuiUp:
        App.Console.PrintError("Fatal: open_mxdownloader requires GUI")
        return

    if not MATERIALX:
        critical_nomatx()
        return

    viewer = MaterialXDownloader(doc)
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("MaterialX Downloader")
    subw.setVisible(True)

    viewer.setUrl(url)
    viewer.show()
