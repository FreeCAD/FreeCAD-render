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
import re

from PySide2.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEnginePage,
    QWebEngineDownloadItem,
)
from PySide2.QtCore import (
    Slot,
    Qt,
    QThread,
    Signal,
    QObject,
    QEventLoop,
)
from PySide2.QtNetwork import QNetworkAccessManager, QNetworkRequest
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
from .materialx_profile import WEBPROFILE


class MaterialXDownloader(QWidget):
    """A MaterialX downloader widget.

    This is an embedded html viewer that catches download requests and triggers
    MaterialX import accordingly.
    """

    _download_required = Signal(QWebEngineDownloadItem)

    def __init__(self, fcdoc, parent, disp2bump=False):
        """Initialize HelpViewer."""
        super().__init__(parent)
        self.parent = parent
        self.fcdoc = fcdoc
        self.disp2bump = disp2bump

        self.setLayout(QVBoxLayout())

        # Set subwidgets
        self.toolbar = QToolBar(self)
        self.layout().addWidget(self.toolbar)
        self.view = QWebEngineView(self)
        self.page = QWebEnginePage(WEBPROFILE, self)
        self.view.setPage(self.page)
        self.layout().addWidget(self.view)

        # Set download manager
        WEBPROFILE.setDownloadPath(App.getTempPath())
        WEBPROFILE.downloadRequested.connect(self.download_requested)
        self._download_required.connect(self.run_download, Qt.QueuedConnection)
        self.win = None

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
        self.view = None
        self.page = None

    @Slot()
    def download_requested(self, download):
        """Answer to download_requested signal."""
        # For unknown reason, I can't manage to run a QEventLoop in this
        # slot (perhaps because it is run in WebEngineProfile thread, or
        # because of the accept/cancel mechanism?). As a consequence, the
        # effective code has been moved to another slot which is triggered via
        # a signal and runs in this class context

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
        download.accept()

    @Slot()
    def run_download(self, download):
        """Run download actually.

        This slot allows to run download in object thread, while
        being triggered from 'download_requested'.
        """
        actual_size = polyhaven_getsize(self.page)

        self.win = DownloadWindow(download, self.fcdoc, self, self.disp2bump)
        self.win.open()


class DownloadWindow(QProgressDialog):
    """A simple widget to handle MaterialX download and import from the web.

    This is mainly a QProgressDialog, with ability to trace progress of a
    download from WebEngineProfile and handle import afterwards.
    """

    def __init__(self, download, fcdoc, parent, disp2bump=False):
        super().__init__(parent)
        self._download = download
        self._fcdoc = fcdoc
        self._disp2bump = disp2bump
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
        # Caveat: this slot must be executed in DownloadWindow thread
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
        self.worker = ImporterWorker(
            filename,
            self._fcdoc,
            self.set_progress,
            self._disp2bump,
            self._download.page(),
        )
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
            os.remove(filename)
            self.cancel()
            return

        # Finalize (success)
        os.remove(filename)
        self.setLabelText("Done")
        self.canceled.connect(self.cancel)
        self.setCancelButtonText("Close")


class ImporterWorker(QObject):
    """A worker for import.

    Runs an importer in a separate thread, with the ability:
    - to report progress
    - to cancel
    - to return a result code
    """

    def __init__(self, filename, fcdoc, progress, disp2bump, page):
        super().__init__()
        self.filename = filename

        self._report_progress.connect(progress)

        self.importer = MaterialXImporter(
            self.filename, fcdoc, self._report_progress.emit, disp2bump
        )
        self.page = page

    # Signals
    finished = Signal(int)
    _report_progress = Signal(int, int)

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


def open_mxdownloader(url, doc, disp2bump=False):
    """Open a downloader."""
    if not App.GuiUp:
        App.Console.PrintError("Fatal: open_mxdownloader requires GUI")
        return

    if not MATERIALX:
        critical_nomatx()
        return

    viewer = MaterialXDownloader(doc, None, disp2bump)
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("MaterialX Downloader")
    subw.setVisible(True)

    viewer.setUrl(url)
    viewer.show()


class JavaScriptRunner(QObject):
    """An object to run synchronously a JavaScript script on a web page."""

    # https://stackoverflow.com/questions/42592999/qt-waiting-for-a-signal-using-qeventloop-what-if-the-signal-is-emitted-too-ear
    _done = Signal()

    def __init__(self, script, page):
        super().__init__()
        self._page = page
        self._result = None
        self._loop = QEventLoop()
        self._script = script

    def run(self):
        """Run JavaScript and wait for result."""
        self._done.connect(self._loop.quit, type=Qt.QueuedConnection)
        self._page.runJavaScript(self._script, 0, self._get_result)
        self._loop.exec_()

    @Slot()
    def _get_result(self, _result):
        """Get result from QWebEnginePage.runJavaScript."""
        self._result = _result
        self._done.emit()

    @property
    def result(self):
        """Get result value."""
        return self._result


def polyhaven_getsize(page):
    """Get texture size (in meters) for gpuopen textures.

    Some textures from gpuopen imported from polyhaven.com have wrong
    dimensions. This hook fetches right dimensions from the original site.
    """
    # Check this is gpuopen
    url = page.url()
    if not url.host() == "matlib.gpuopen.com":
        return None

    # Get links in page
    runner = JavaScriptRunner(GETLINKS_JS, page)
    runner.run()
    result = runner.result.split(" ")

    # Search for a link to poly haven
    polyhaven_links = (
        l for l in result if l.startswith("https://polyhaven.com")
    )
    try:
        link = next(polyhaven_links)
    except StopIteration:
        return None

    # Load page from polyhaven
    request = QNetworkRequest(link)
    access_manager = QNetworkAccessManager()
    loop = QEventLoop()
    access_manager.finished.connect(loop.quit, Qt.QueuedConnection)
    polyhaven_page = access_manager.get(request)
    loop.exec_()
    data = polyhaven_page.readAll()

    # Search width
    if not (result := re.search(rb"<strong>(.*)</strong><p>wide</p>", data)):
        return None

    # Parse quantity
    try:
        quantity = App.Units.parseQuantity(result.group(1))
    except ValueError:
        return None

    # Convert to meters
    try:
        value = quantity.getValueAs("m")
    except ValueError:
        return None

    print(
        "Polyhaven material: will use actual texture size from polyhaven.com "
        f"('{value} {'meters' if value > 1 else 'meter'}')"
    )

    return value


# JavaScript snippet to get all links in a web page
GETLINKS_JS = """
var links = document.getElementsByTagName("a");
var results = [];
for(var i=0, max=links.length; i<max; i++) {
    results.push(links[i].href);
}
results.join(" ");
"""
