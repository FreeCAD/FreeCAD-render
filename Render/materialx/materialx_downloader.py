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
from urllib.parse import urlparse

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import (
        QWebEnginePage,
        QWebEngineDownloadRequest,
    )

    QWebEngineDownloadItem = QWebEngineDownloadRequest
except ModuleNotFoundError:
    from PySide2.QtWebEngineWidgets import (
        QWebEngineView,
        QWebEnginePage,
        QWebEngineDownloadItem,
    )

from PySide.QtCore import (
    Slot,
    Qt,
    QThread,
    Signal,
    QObject,
    QEventLoop,
    QUrl,
)
from PySide.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest,
)
from PySide.QtGui import (
    QWidget,
    QToolBar,
    QVBoxLayout,
    QMessageBox,
    QProgressDialog,
)

import FreeCADGui as Gui
import FreeCAD as App

from Render import ImageLight

from .materialx_importer import MaterialXImporter
from .materialx_profile import WEBPROFILE


# Remark: please do not use:
# - QWebEngineProfile.setDownloadPath
# - QWebEngineDownloadItem.downloadFileName
# - QWebEngineDownloadItem.downloadDirectory
# as they may not be compatible with old PySide (and old Ubuntu)
# (2024-04-24)


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
        self.page.javaScriptConsoleMessage = _nope  # Hide console messages
        self.view.setPage(self.page)
        self.layout().addWidget(self.view)

        # Set download manager
        WEBPROFILE.downloadRequested.connect(self.download_requested)
        self._download_required.connect(self.run_download, Qt.QueuedConnection)

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
        try:
            _, filename = os.path.split(download.path())
            download.setPath(os.path.join(App.getTempPath(), filename))
        except AttributeError:
            # Qt6
            filename = download.downloadFileName()
            download.setDownloadDirectory(App.getTempPath())

        download.accept()

    @Slot()
    def run_download(self, download):
        """Run download actually.

        This slot allows to run download in object thread, while
        being triggered from 'download_requested'.
        """
        # Special case: HDRI
        if self._is_hdri_download(download):
            win = HdriDownloadWindow(download, self.fcdoc, self)
            win.open()
            return

        # Nominal case: materialx import
        polyhaven_actual_size = polyhaven_getsize(self.page)

        win = MaterialXDownloadWindow(
            download, self.fcdoc, self, self.disp2bump, polyhaven_actual_size
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
            print(ext)
            return False

        # Seems to be one of ours
        return True


class DownloadWindow(QProgressDialog):
    """A simple widget to handle download and import from the web.

    This is mainly a QProgressDialog, with ability to trace progress of a
    download from WebEngineProfile and trigger import afterwards.
    """

    def __init__(
        self,
        download,
        fcdoc,
        parent,
    ):
        super().__init__(parent)
        self._download = download
        self._fcdoc = fcdoc
        try:
            _, filename = os.path.split(download.path())
        except AttributeError:
            # Qt6
            filename = download.downloadFileName()
        self.setWindowTitle("Import from MaterialX Library")
        self.setLabelText(f"Downloading '{filename}'...")
        self.setAutoClose(False)
        self.setAutoReset(False)

        try:
            self._download.downloadProgress.connect(self.set_progress)
            download.finished.connect(self.finished_download)
        except:
            # Qt6
            self._download.receivedBytesChanged.connect(self.set_progress_6)
            download.isFinishedChanged.connect(self.finished_download)

        self.canceled.connect(download.cancel)

        self.thread = None
        self.worker = None

    @Slot()
    def set_progress(self, bytes_received, bytes_total):
        """Set value of widget progress bar (Qt5)."""
        # Caveat: this slot must be executed in DownloadWindow thread
        self.setMaximum(bytes_total)
        self.setValue(bytes_received)

    @Slot()
    def set_progress_6(self):
        """Set value of widget progress bar (Qt6)."""
        # Caveat: this slot must be executed in DownloadWindow thread
        bytes_total = self._download.totalBytes()
        bytes_received = self._download.receivedBytes()
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
        try:
            _, filenameshort = os.path.split(self._download.path())
        except AttributeError:
            # Qt6
            filenameshort = self._download.downloadFileName()
        self.setLabelText(f"Importing '{filenameshort}'...")
        self.do_import()

    def do_import(self):
        """Do importation of downloaded file (callback).

        To be overriden by specialized widgets.
        """


class MaterialXDownloadWindow(DownloadWindow):
    """A simple widget to handle MaterialX download and import from the web."""

    def __init__(
        self,
        download,
        fcdoc,
        parent,
        disp2bump=False,
        polyhaven_actual_size=None,
    ):
        super().__init__(download, fcdoc, parent)
        self._disp2bump = disp2bump
        self._polyhaven_size = polyhaven_actual_size

        self.thread = None
        self.worker = None

    def do_import(self):
        """Do import of MaterialX downloaded file.

        This function handles import. Import is executed in a separate thread
        to avoid blocking UI.
        """
        try:
            filename = self._download.path()
        except AttributeError:
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
            self._polyhaven_size,
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
        loop = QEventLoop()
        self.worker.finished.connect(loop.exit, Qt.QueuedConnection)
        self.thread.start(QThread.IdlePriority)
        if loop.exec_():
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

    def __init__(
        self, filename, fcdoc, progress, disp2bump, page, polyhaven_actual_size
    ):
        super().__init__()
        self.filename = filename

        self._report_progress.connect(progress)

        self.importer = MaterialXImporter(
            self.filename,
            fcdoc,
            self._report_progress.emit,
            disp2bump,
            polyhaven_actual_size,
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
            App.Console.PrintError(f"{type(exc)}{exc.args}\n")
            traceback.print_exception(exc)
            self.finished.emit(-99)  # Uncaught error
        else:
            self.finished.emit(res)

    @Slot()
    def cancel(self):
        """Request importer to cancel."""
        self.importer.cancel()


class HdriDownloadWindow(DownloadWindow):
    """A simple widget to handle HDRI download and import from the web."""

    def do_import(self):
        """Do import of HDRI downloaded file."""
        try:
            filepath = self._download.path()
        except:
            # Qt6
            filepath = os.path.join(
                self._download.downloadDirectory(),
                self._download.downloadFileName(),
            )
        basename = os.path.basename(filepath)
        _, fpo, _ = ImageLight.create(self._fcdoc)
        fpo.Label = basename
        fpo.ImageFile = filepath

        # Finalize (success)
        os.remove(filepath)
        self.setLabelText("Done")
        self.canceled.connect(self.cancel)
        self.setCancelButtonText("Close")


def open_mxdownloader(url, doc, disp2bump=False):
    """Open a downloader."""
    if not App.GuiUp:
        App.Console.PrintError("Fatal: open_mxdownloader requires GUI")
        return

    viewer = MaterialXDownloader(doc, None, disp2bump)
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("MaterialX Downloader")
    subw.setVisible(True)

    viewer.setUrl(url)
    viewer.show()


class JavaScriptRunner(QObject):
    """An object to run a JavaScript script on a web page."""

    # https://stackoverflow.com/questions/42592999/qt-waiting-for-a-signal-using-qeventloop-what-if-the-signal-is-emitted-too-ear
    javascript_done = Signal()

    def __init__(self, script, page):
        super().__init__()
        self._page = page
        self._result = None
        self._script = script

    def run(self):
        """Run JavaScript and wait for result."""
        self._page.javaScriptConsoleMessage = self.cb_get_console_message
        self._page.runJavaScript(self._script, 0)

    @Slot()
    def cb_get_console_message(self, level, message, line_number, source_id):
        """Get console message - callback for JS script to output result."""
        self._result = message
        self.javascript_done.emit()

    @property
    def result(self):
        """Get result value."""
        return self._result


def _nope(*_):
    """No operation function."""


class GetPolyhavenLink(JavaScriptRunner):
    """A class to get the link to polyhaven page, from gpuopen page."""

    done = Signal()

    def __init__(self, page):
        # JavaScript snippet to get all links in a web page
        getlinks_snippet = """
        var links = document.getElementsByTagName("a");
        var results = [];
        for(var i=0, max=links.length; i<max; i++) {
            results.push(links[i].href);
        }
        results.join(" ");
        console.log(results);
        """
        super().__init__(getlinks_snippet, page)
        self.javascript_done.connect(self._echo_done, Qt.QueuedConnection)
        self._result = None
        self._link = None

    @Slot()
    def _echo_done(self):
        """Slot to trigger when javascript has run."""
        res = super().result.split(",")

        # Search for a link to poly haven
        polyhaven_links = (
            l
            for l in res
            if urlparse(l).hostname
            and urlparse(l).hostname.endswith(".polyhaven.com")
        )
        try:
            link = next(polyhaven_links)
        except StopIteration:
            link = None

        self._link = link
        self.done.emit()

    @property
    def link(self):
        """Get link attribute."""
        return self._link


ACCESS_MANAGER = QNetworkAccessManager()


class GetPolyhavenData(QObject):
    """A class to get data from polyhaven.com, for gpuopen.

    Some dimensions in gpuopen, for materials originating from polyhaven.com,
    are wrong. To remedy, this class can retrieve those information querying
    polyhaven.com.
    """

    done = Signal()

    def __init__(self, link):
        """Initialize object."""
        super().__init__()
        self._link = QUrl(link)
        self._data = None
        self._reply = None

    def run(self):
        """Run get request."""
        request = QNetworkRequest(self._link)
        self._reply = ACCESS_MANAGER.get(request)
        self._reply.finished.connect(self._process_reply, Qt.QueuedConnection)

    @Slot()
    def _process_reply(self):
        """Process reply of get request."""
        self._data = self._reply.readAll()
        self.done.emit()

    @property
    def data(self):
        """Get result."""
        return self._data


def polyhaven_getsize(page):
    """Get texture size (in meters) for gpuopen textures.

    Some textures from gpuopen imported from polyhaven.com have wrong
    dimensions. This hook fetches right dimensions from the original site.
    """
    # Check this is gpuopen
    url = page.url()
    if not url.host() == "matlib.gpuopen.com":
        return None

    # Get link in gpuopen page
    loop = QEventLoop()
    getlink = GetPolyhavenLink(page)
    getlink.done.connect(loop.quit, Qt.QueuedConnection)
    getlink.run()
    loop.exec_()
    if (link := getlink.link) is None:
        return None

    # Get data in polyhaven page
    getdata = GetPolyhavenData(link)
    getdata.done.connect(loop.exit, Qt.QueuedConnection)
    getdata.run()
    loop.exec_()
    data = getdata.data

    # Search size
    sizes = (
        res
        for regex in (
            rb"<strong>(.*)</strong><p>wide</p>",
            rb"<strong>(.*)</strong><p>tall</p>",
        )
        if (res := re.search(regex, data)) is not None
    )
    try:
        result = next(sizes)
    except StopIteration:
        App.Console.PrintLog(
            "[Render][MaterialX] Polyhaven - failed to find tags"
        )
        return None

    # Parse quantity
    try:
        quantity = App.Units.parseQuantity(result.group(1))
    except ValueError:
        App.Console.PrintLog(
            "[Render][MaterialX] Polyhaven - failed to parse quantity"
        )
        return None

    # Convert to meters
    try:
        value = quantity.getValueAs("m")
    except ValueError:
        App.Console.PrintLog(
            "[Render][MaterialX] Polyhaven - failed to get valye as meters"
        )
        return None

    return value
