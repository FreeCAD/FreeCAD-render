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
            self._download.downloadProgress.connect(
                self.set_progress, Qt.QueuedConnection
            )
            self._download.finished.connect(
                self.finished_download, Qt.QueuedConnection
            )
        if PYQT6 or PYSIDE6:
            self._download.receivedBytesChanged.connect(
                self.set_progress_6, Qt.QueuedConnection
            )
            self._download.isFinishedChanged.connect(
                self.finished_download, Qt.QueuedConnection
            )

        self.canceled.connect(self._download.cancel, Qt.QueuedConnection)

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
        remove_after_import=True,
    ):
        super().__init__(download, parent, release_material_signal)
        self._disp2bump = disp2bump
        self._polyhaven_size = polyhaven_actual_size
        self._remove_after_import = bool(remove_after_import)

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
            if self._remove_after_import:
                os.remove(filename)
            self.cancel()
            return

        # Finalize (success)
        if self._remove_after_import:
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
