from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEngineScript
from PySide2.QtCore import QUrl
import FreeCADGui as Gui
import FreeCAD as App

from Render.constants import WBDIR


def open_help():
    if not SCRIPT_JQUERY or not SCRIPT_MARKED or not App.GuiUp:
        return

    viewer = QWebEngineView()
    scripts = viewer.page().scripts()

    script_jquery = QWebEngineScript()
    script_jquery.setSourceCode(SCRIPT_JQUERY)
    script_jquery.setInjectionPoint(QWebEngineScript.DocumentCreation)
    scripts.insert(script_jquery)

    script_marked = QWebEngineScript()
    script_marked.setSourceCode(SCRIPT_MARKED)
    script_marked.setInjectionPoint(QWebEngineScript.DocumentCreation)
    scripts.insert(script_marked)

    script_run = QWebEngineScript()
    script_run.setSourceCode(SCRIPT_RUN)
    script_run.setInjectionPoint(QWebEngineScript.DocumentReady)
    scripts.insert(script_run)

    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("Render help")
    subw.setVisible(True)

    viewer.setUrl(URL)
    viewer.show()


# Init module
SCRIPT_JQUERY, SCRIPT_MARKED = None, None

with open(f"{WBDIR}/docs/3rdparty/jQuery.js") as f:
    SCRIPT_JQUERY = f.read()

with open(f"{WBDIR}/docs/3rdparty/marked.min.js") as f:
    SCRIPT_MARKED = f.read()

SCRIPT_RUN = f"""\
  $.when( $.ready).then(function() {{
    var now_body = $( "body" ).text();
    $( "body" ).html( marked.parse(now_body) );
    }});
"""

URL = QUrl(f"file://{WBDIR}/README.md")
