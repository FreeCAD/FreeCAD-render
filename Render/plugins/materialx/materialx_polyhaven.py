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

"""This module implements a hook for polyhaven materials in gpuopen.

For polyhaven materials (polyhaven.com), texture size is usually wrong on
gpuopen web site. This hook fetches the right dimension from original
site.
"""

import os.path
import traceback
import re
from urllib.parse import urlparse
import argparse
import sys
import pathlib
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
    QEvent,
)
from qtpy.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest,
)
from qtpy.QtWidgets import (
    QWidget,
    QToolBar,
    QVBoxLayout,
    QMessageBox,
    QProgressDialog,
)
from qtpy.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEnginePage,
    QWebEngineProfile,
)

from renderplugin import (
    ARGS,
    RenderPluginApplication,
    log,
    msg,
    error,
    SOCKET,
    PluginMessageEvent,
)

from .materialx_importer import MaterialXImporter

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
