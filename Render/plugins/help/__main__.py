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

"""This module implements a help viewer for Render workbench.

This feature is implemented as an independent plugin.
"""

import os.path
import pathlib
import argparse
import sys

from qtpy.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEngineScript,
    QWebEnginePage,
)
from qtpy.QtCore import QUrl
from qtpy.QtWidgets import (
    QWidget,
    QToolBar,
    QVBoxLayout,
)

from renderplugin import ARGS, RenderPluginApplication


THISDIR = os.path.dirname(__file__)


class HelpViewer(QWidget):
    """A help viewer widget.

    The help viewer is an html viewer but is able to render (local) markdown
    files.
    Markdown files are converted on-the-fly, thanks to 'marked.js' module.
    (https://github.com/markedjs/marked)
    """

    SCRIPT_GREASEBLOCK = """\
    // ==UserScript==
    // @match file://*/*.md
    // ==/UserScript==
    """

    def __init__(self, starting_url, scripts_dir):
        """Initialize HelpViewer."""
        super().__init__()

        # Set subwidgets
        self.setLayout(QVBoxLayout(self))
        self.toolbar = QToolBar(self)
        self.layout().addWidget(self.toolbar)
        self.view = QWebEngineView(self)
        self.layout().addWidget(self.view)

        # Add actions to toolbar
        webaction = QWebEnginePage.WebAction
        self.toolbar.addAction(self.view.pageAction(webaction.Back))
        self.toolbar.addAction(self.view.pageAction(webaction.Forward))
        self.toolbar.addAction(self.view.pageAction(webaction.Reload))
        self.toolbar.addAction(self.view.pageAction(webaction.Stop))

        # Prepare scripts
        jquery_path = os.path.join(scripts_dir, "jQuery.js")
        with open(jquery_path, encoding="utf-8") as f:
            script_jquery_source = self.SCRIPT_GREASEBLOCK + f.read()

        marked_path = os.path.join(scripts_dir, "marked.min.js")
        with open(marked_path, encoding="utf-8") as f:
            script_marked_source = self.SCRIPT_GREASEBLOCK + f.read()

        css_path = os.path.join(scripts_dir, "waterlight.css")
        css_url = QUrl.fromLocalFile(css_path).url()

        script_run_source = (
            self.SCRIPT_GREASEBLOCK
            + f"""\
        $.when( $.ready).then(function() {{
          var now_body = $("body").text();
          $("body").html( marked.parse(now_body) );
          $("head").append('<link rel="stylesheet" href="{css_url}">');
        }});
        """
        )  # Stylesheet credit: https://github.com/kognise/water.css

        # Insert scripts into Web view
        scripts = self.view.page().scripts()

        script_jquery = QWebEngineScript()
        script_jquery.setSourceCode(script_jquery_source)

        injection_point = QWebEngineScript.InjectionPoint

        script_jquery.setInjectionPoint(injection_point.DocumentCreation)
        scripts.insert(script_jquery)

        script_marked = QWebEngineScript()
        script_marked.setSourceCode(script_marked_source)
        script_marked.setInjectionPoint(injection_point.DocumentCreation)
        scripts.insert(script_marked)

        script_run = QWebEngineScript()
        script_run.setSourceCode(script_run_source)
        script_run.setInjectionPoint(injection_point.DocumentReady)
        scripts.insert(script_run)

        # Set starting url
        self.setUrl(starting_url)

    def setUrl(self, url):  # pylint: disable=invalid-name
        """Set viewer url.

        Args:
            url -- url to set viewer to (QUrl)
        """
        self.view.load(url)


def main():
    """The entry point."""
    # Get arguments
    parser = argparse.ArgumentParser(
        prog="Render help",
        description="Open a help browser for Render Workbench",
    )
    parser.add_argument(
        "path_to_workbench",
        help="the path to the workbench",
        type=pathlib.Path,
    )
    args = parser.parse_args(ARGS)

    # Compute dirs
    workbench_dir = args.path_to_workbench
    readme = os.path.join(workbench_dir, "README.md")
    scripts_dir = os.path.join(THISDIR, "3rdparty")

    # Build application and launch
    application = RenderPluginApplication(
        HelpViewer, QUrl.fromLocalFile(readme), scripts_dir
    )
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
