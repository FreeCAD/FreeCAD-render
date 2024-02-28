# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
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
    QWebEngineScript,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineDownloadItem,
)
from PySide2.QtCore import QUrl, Slot, Qt, QThread, Signal, QObject, QEventLoop
from PySide2.QtWidgets import (
    QWidget,
    QToolBar,
    QVBoxLayout,
    QMessageBox,
    QProgressDialog,
)

import FreeCADGui as Gui
import FreeCAD as App

from Render.constants import WBDIR
from Render.rdrexecutor import RendererExecutorGui
from Render.materialx import import_materialx


class MaterialXDownloader(QWidget):
    """A MaterialX downloader widget.

    This viewer is an html viewer but is able to download and import MaterialX
    files.
    """

    def __init__(self, doc, parent=None):
        """Initialize HelpViewer."""
        super().__init__(parent)
        self.parent = parent

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
    def __init__(self, download, parent=None):
        parent = Gui.getMainWindow()
        super().__init__(parent)
        self._download = download
        filename = download.downloadFileName()
        self.setWindowTitle("Import from MaterialX Library")
        self.setLabelText(f"Downloading '{filename}'...")
        self.setAutoClose(False)
        self.setAutoReset(False)

        # self.canceled.connect(self.on_canceled)
        self._download.downloadProgress.connect(self.set_progress)
        self.canceled.connect(download.cancel)
        download.finished.connect(self.finished_download)

    # @Slot()
    # def on_canceled(self):
    # self._download.cancel()

    @Slot()
    def set_progress(self, bytes_received, bytes_total):
        self.setMaximum(bytes_total)
        self.setValue(bytes_received)

    @Slot()
    def finished_download(self):
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
            f"{self.labelText()}\n\nImporting '{self._download.downloadFileName()}'..."
        )
        filename = os.path.join(
            self._download.downloadDirectory(),
            self._download.downloadFileName(),
        )
        self.setValue(0)

        # Start import
        worker = ImporterWorker(filename)
        thread = QThread()
        thread.setTerminationEnabled()
        self.canceled.connect(thread.terminate)

        # Move worker to thread
        worker.moveToThread(thread)

        # Connect signals and slots
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(thread.exit)
        thread.finished.connect(thread.deleteLater)

        # Start the thread
        thread.start()
        loop = QEventLoop()
        thread.finished.connect(loop.quit)
        if not thread.isFinished():
            loop.exec_()
        print(f"FINISHED {filename}")


class ImporterWorker(QObject):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    finished = Signal(int)

    @Slot()
    def run(self):
        try:
            # TODO explicit doc?
            import_materialx(self.filename)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            App.Console.PrintError("/!\\ IMPORT ERROR /!\\\n")
            traceback.print_exception(exc)
        finally:
            self.finished.emit(0)


def open_mxdownloader(url, doc):
    """Open a downloader."""
    if not App.GuiUp:
        return

    viewer = MaterialXDownloader(doc)
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("MaterialX Downloader")
    subw.setVisible(True)

    viewer.setUrl(url)
    viewer.show()
