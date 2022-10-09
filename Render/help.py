from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PySide2.QtCore import QUrl, QObject, Signal, Slot
import FreeCADGui as Gui
import markdown

from Render.constants import WBDIR

class Content(QObject):

    new_content = Signal()

    def __init__(self):
        super().__init__()
        self._text = ""

    def __call__(self, text):
        self._text = str(text)
        self.new_content.emit()

    def text(self):
        return self._text

class HelpViewer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loadFinished.connect(self.after_load)
        self.content = Content()
        self.content.new_content.connect(self.convert_markdown)
        self.convert = True
        self.renderProcessTerminated.connect(self.after_render)

    @Slot(bool)
    def after_load(self, success):
        print("after_load")
        if not self.convert:
            # Protect with mutex?
            self.convert = True
            return

        # Convert to html
        if not success:
            print("Load Failed")
            return
        self.page().toPlainText(self.content)  # Asynchronous!

    @Slot(QWebEnginePage.RenderProcessTerminationStatus, int)
    def after_render(self, status, exit_code):
        print("after_render")

    @Slot()
    def convert_markdown(self):
        self.convert = False
        print(self.content.text())
        html = markdown.markdown(self.content.text())
        url = QUrl(f"file://{WBDIR}")  # TODO
        self.setHtml(html, url)



def open_help():
    url = QUrl(f"file://{WBDIR}/README.md")
    viewer = HelpViewer()
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("Render help")
    subw.setVisible(True)
    print(url)
    viewer.setUrl(url)
    viewer.show()
