# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2024 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software: you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation, either version 3 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.                  *
# *   See the GNU General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU General Public License     *
# *   along with this program. If not, see <https://www.gnu.org/licenses/>. *
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


from qtpy.QtCore import (
    Slot,
    Qt,
    Signal,
    QUrl,
    QEvent,
    QDir,
    QObject,
)
from qtpy.QtWidgets import (
    QWidget,
    QToolBar,
    QVBoxLayout,
    QMessageBox,
    QFileDialog,
)
from qtpy.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEnginePage,
    QWebEngineProfile,
)

from materialx.downloader import MaterialXDownloadWindow, HdriDownloadWindow
from materialx.polyhaven import polyhaven_getsize

from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest

from renderplugin import (
    ARGS,
    RenderPluginApplication,
    msg,
    log,
    SOCKET,
    PluginMessageEvent,
)


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

    _download_required = Signal(QWebEngineDownloadRequest)
    release_material_signal = Signal()

    def __init__(self, url, temp_path, disp2bump=False):
        """Initialize chooser."""
        super().__init__()
        self.disp2bump = disp2bump
        self.temp_path = temp_path

        self._layout = QVBoxLayout(self)
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
        webaction = QWebEnginePage.WebAction
        self.toolbar.addAction(self.view.pageAction(webaction.Back))
        self.toolbar.addAction(self.view.pageAction(webaction.Forward))
        self.toolbar.addAction(self.view.pageAction(webaction.Reload))
        self.toolbar.addAction(self.view.pageAction(webaction.Stop))

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

    @Slot(QWebEngineDownloadRequest)
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
        download.setDownloadDirectory(self.temp_path)

        download.accept()

    @Slot(QWebEngineDownloadRequest)
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


class LocalChooser(QFileDialog):
    """A MaterialX local chooser widget.

    This is a file dialog that allows to select and import a materialx file
    into FreeCAD.
    """

    # pylint: disable=too-many-ancestors
    release_material_signal = Signal()

    def __init__(self, temp_path, disp2bump=False):
        super().__init__()
        self.temp_path = temp_path
        self.disp2bump = disp2bump
        self.setObjectName("RenderLocalChooser")

        # Subwidgets
        self.setLabelText(
            QFileDialog.LookIn,
            "<b><big>Select a MaterialX file:</big></b>",
        )

        self.setOption(QFileDialog.DontUseNativeDialog, True)
        filters = ["MaterialX (*.mtlx *.zip)", "All files (*.*)"]
        self.setNameFilters(filters)
        self.setDirectory(QDir.home())
        self.setFileMode(QFileDialog.ExistingFiles)
        self.setObjectName("RenderLocalChooserFileDialog")

    @Slot()
    def accept(self):
        for file in self.selectedFiles():

            download = LocalDownload(file)
            win = MaterialXDownloadWindow(
                download,
                self,
                self.release_material_signal,
                self.disp2bump,
                None,  # polyhaven
                False,  # remove_after_import
            )
            download.set_ready()
            win.exec()

    @Slot()
    def reject(self):
        log("Closing dialog")
        SOCKET.send("DETACH", None)

    def event(self, event):
        """Handle event (Qt callback)."""
        if event.type() == PluginMessageEvent.TYPE:
            verb, _ = event.message
            if verb == "RELEASE":
                self.release_material_signal.emit()
            return True

        return super().event(event)


class LocalDownload(QObject):
    """A download object for MaterialX local import.

    This object mimics QWebEngineDownloadItem (duck typing), for local import
    use case. Basically, it tricks the downloader into thinking that a local
    file has actually been downloaded, even though it was there all along. This
    allows the entire download mechanism to be reused in the simpler case of
    importing a local file.
    """

    receivedBytesChanged = Signal()
    isFinishedChanged = Signal()

    DUMMY_DOWNLOAD_SIZE = 1
    DUMMY_DOWNLOAD_STATE = (
        QWebEngineDownloadRequest.DownloadState.DownloadCompleted
    )

    def __init__(self, filepath):
        """Initialize object."""
        super().__init__()
        self.filepath = filepath

    def set_ready(self):
        """Set download object to ready state.

        As there is no actual download in local import, the 'ready' state
        emits a 'finished' event.
        """
        self.receivedBytesChanged.emit()
        self.isFinishedChanged.emit()

    def path(self):
        """Get downloaded file path."""
        return self.filepath

    def downloadFileName(self):  # pylint: disable=invalid-name
        """Get downloaded file name."""
        _, filename = os.path.split(self.filepath)
        return filename

    def downloadDirectory(self):  # pylint: disable=invalid-name
        """Get downloaded file directory."""
        directory, _ = os.path.split(self.filepath)
        return directory

    @Slot()
    def cancel(self):
        """Cancel download callback.

        As no actual download occurs, this callback is inactive.
        """

    def state(self):
        """Return downloading state.

        This state is always 'download completed'.
        """
        return self.DUMMY_DOWNLOAD_STATE

    def receivedBytes(self):  # pylint: disable=invalid-name
        """Return received bytes.

        Returns dummy value
        """
        return self.DUMMY_DOWNLOAD_SIZE

    def totalBytes(self):  # pylint: disable=invalid-name
        """Return total bytes.

        Always 1 (dummy)
        """
        return self.DUMMY_DOWNLOAD_SIZE


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
    res = application.exec()
    log(f"Exiting plugin (return code: {res})")
    sys.exit(res)


if __name__ == "__main__":
    main()
