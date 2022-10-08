from PySide2 import QtWebEngineWidgets
from PySide2 import QtCore
import FreeCADGui as Gui

from Render.constants import WBDIR

def open_help():
    viewer = QtWebEngineWidgets.QWebEngineView()
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("Render help")
    subw.setVisible(True)
    url = QtCore.QUrl(f"file://{WBDIR}/README.md")
    print(url)
    viewer.setUrl(url)
    viewer.show()
