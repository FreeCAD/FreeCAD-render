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

"""This module implements a downloader for MaterialX and HDRI."""

import os.path
import traceback
import re
from urllib.parse import urlparse
import tempfile
import itertools


from qtpy import PYQT5, PYQT6, PYSIDE2, PYSIDE6
from qtpy.QtCore import (
    Slot,
    Qt,
    QThread,
    Signal,
    QObject,
    QEventLoop,
    QUrl,
)
from qtpy.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest,
)
from qtpy.QtWidgets import (
    QProgressDialog,
)

from materialx.importer import MaterialXImporter
from renderplugin import (
    log,
    msg,
    error,
    SOCKET,
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


# Remark: please do not use:
# - QWebEngineProfile.setDownloadPath
# - QWebEngineDownloadItem.downloadFileName
# - QWebEngineDownloadItem.downloadDirectory
# as they may not be compatible with old PySide (and old Ubuntu)
# (2024-04-24)


def get_download_filename(download):
    """Get file name from download."""
    if PYQT5 or PYSIDE2:
        _, filename = os.path.split(download.path())
    elif PYQT6 or PYSIDE6:
        filename = download.downloadFileName()
    else:
        raise RuntimeError()

    return filename


def get_download_filepath(download):
    """Get file path from download."""
    if PYQT5 or PYSIDE2:
        return download.path()

    if PYQT6 or PYSIDE6:
        return os.path.join(
            download.downloadDirectory(),
            download.downloadFileName(),
        )

    raise RuntimeError()


class DownloadWindow(QProgressDialog):
    # pylint: disable=too-many-ancestors
    """A simple widget to handle download and import from the web - base class.

    This is mainly a QProgressDialog, with ability to trace progress of a
    download from WebEngineProfile and trigger import afterwards.
    """

    def __init__(
        self,
        download,
        parent,
        release_material_signal,
    ):
        super().__init__(parent)
        self._download = download
        self._release_material_signal = release_material_signal
        filename = get_download_filename(download)
        self.setWindowTitle("Import from MaterialX Library")
        self.setLabelText(f"Downloading '{filename}'...")
        self.setAutoClose(False)
        self.setAutoReset(False)

        if PYQT5 or PYSIDE2:
            self._download.downloadProgress.connect(self.set_progress)
            download.finished.connect(self.finished_download)
        if PYQT6 or PYSIDE6:
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
        state = self._download.state()
        if state == QWebEngineDownloadItem.DownloadCancelled:
            msg("Download cancelled")
            return
        if state == QWebEngineDownloadItem.DownloadInterrupted:
            msg("Download interrupted")
            return
        assert state == QWebEngineDownloadItem.DownloadCompleted

        filenameshort = get_download_filename(self._download)
        self.setLabelText(f"Importing '{filenameshort}'...")
        self.do_import()

    def do_import(self):
        """Do importation of downloaded file (callback).

        To be overriden by specialized widgets.
        """

    def wait_for_release(self):
        """Wait for the host to release transmitted file."""
        # Wait for acknowledgement
        worker_loop = QEventLoop()
        self._release_material_signal.connect(
            worker_loop.quit, Qt.QueuedConnection
        )
        worker_loop.exec()


class MaterialXDownloadWindow(DownloadWindow):
    # pylint: disable=too-many-ancestors
    """A simple widget to handle MaterialX download and import from the web.

    Subclass intended for materials.
    """

    def __init__(
        self,
        download,
        parent,
        release_material_signal,
        disp2bump=False,
        polyhaven_actual_size=None,
    ):
        super().__init__(download, parent, release_material_signal)
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
            self.set_progress,
            self._disp2bump,
            self._download.page(),
            self._polyhaven_size,
            self.wait_for_release,
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

        if loop.exec():
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

    # Signals
    finished = Signal(int)
    _report_progress = Signal(int, int)

    def __init__(
        self,
        filename,
        progress,
        disp2bump,
        page,
        polyhaven_actual_size,
        wait_for_release,
    ):
        super().__init__()
        self.filename = filename

        self._report_progress.connect(progress)

        self.importer = MaterialXImporter(
            self.filename,
            self._report_progress.emit,
            disp2bump,
            polyhaven_actual_size,
        )
        self.page = page
        self._wait_for_release = wait_for_release

    def run(self):
        """Run in worker thread."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                returncode = self.importer.run(tmpdir)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                error("/!\\ IMPORT ERROR /!\\")
                error(f"{type(exc)}{exc.args}")
                trace = traceback.format_exception(exc)
                for elem in trace:
                    for line in elem.splitlines():
                        error(line)
                self.finished.emit(-99)  # Uncaught error
                return

            if not returncode:  # Import succeeded
                # Notify FreeCAD to import result
                in_file = os.path.join(tmpdir, "out.FCMat")
                SOCKET.send("MATERIAL", in_file)
                self._wait_for_release()

            # Notify finished
            self.finished.emit(returncode)
            msg(f"Releasing {tmpdir}")
            msg("IMPORT TERMINATED")

    @Slot()
    def cancel(self):
        """Request importer to cancel."""
        self.importer.cancel()


class HdriDownloadWindow(DownloadWindow):
    # pylint: disable=too-many-ancestors
    """A simple widget to handle HDRI download and import from the web.

    DownloadWindow subclass intended for HDRI.
    """

    def do_import(self):
        """Do import of HDRI downloaded file."""
        filepath = get_download_filepath(self._download)
        basename = os.path.basename(filepath)

        SOCKET.send("IMAGELIGHT", (basename, filepath))
        self.wait_for_release()

        # Finalize (success)
        os.remove(filepath)
        self.setLabelText("Done")
        self.canceled.connect(self.cancel)
        self.setCancelButtonText("Close")


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
            if urlparse(l).netloc and urlparse(l).netloc == "polyhaven.com"
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


class GetPolyhavenData(QObject):
    """A class to get data from polyhaven.com, for gpuopen.

    Some dimensions in gpuopen, for materials originating from polyhaven.com,
    are wrong. To remedy, this class can retrieve those data querying
    polyhaven.com.
    """

    done = Signal()

    def __init__(self, link):
        """Initialize object."""
        super().__init__()
        self._link = QUrl(link)
        self._data = None
        self._reply = None
        self._access_manager = QNetworkAccessManager()

    def run(self):
        """Run get request."""
        request = QNetworkRequest(self._link)
        self._reply = self._access_manager.get(request)
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
    loop.exec()

    if (link := getlink.link) is None:
        return None

    # Get data in polyhaven page
    getdata = GetPolyhavenData(link)
    getdata.done.connect(loop.exit, Qt.QueuedConnection)
    getdata.run()
    loop.exec()
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
        log("[Render][MaterialX] Polyhaven - failed to find tags")
        return None

    # Extract and clean quantity
    try:
        quantity = result.group(1)
    except IndexError:
        log("[Render][MaterialX] Polyhaven - failed to extract quantity")
        return None
    quantity = bytes(filter(lambda x: x != 32, quantity))  # Remove spaces
    quantity = quantity.lower()

    # Parse amount/unit
    amount_bytes = bytes(
        itertools.takewhile(lambda x: x in b"0123456789.", quantity)
    )
    unit = quantity[len(amount_bytes) :]
    try:
        amount = float(amount_bytes)
    except ValueError:
        log(
            "[Render][MaterialX] Polyhaven - "
            "failed to parse amount from quantity ('{quantity}')"
        )
        return None

    # Normalize amount
    factors = {
        b"mm": 0.001,
        b"cm": 0.01,
        b"dm": 0.1,
        b"m": 1.0,
        b"dam": 10.0,
        b"hm": 100.0,
        b"km": 1000.0,
        b"": 1.0,
    }
    try:
        factor = factors[unit]
    except KeyError:
        log(
            "[Render][MaterialX] Polyhaven - "
            "failed to parse unit from quantity ('{quantity}')"
        )
        return None

    return amount * factor