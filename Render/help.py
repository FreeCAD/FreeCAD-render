from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineScript, QWebEngineScriptCollection
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

INDEX_HTML = f"""\
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Marked in the browser</title>
  <script src="https://code.jquery.com/jquery-1.12.0.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script>
    $.get( "file://{WBDIR}/README.md", function( data ) {{
      $( "#content" ).html( marked.parse(data) );
    }});
  </script>
</head>

<body>
  <div id="content"></div>
</body>
</html>
"""

INDEX_HTML = f"""\
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Marked in the browser</title>
  <script src="https://code.jquery.com/jquery-1.12.0.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script>
  $.when( $.ready).then(function() {{
    alert('ready');
    $.get( "file://{WBDIR}/README.md", function( data ) {{
      $( "#content" ).html( marked.parse(data) );
    }});
  }} )

  </script>
</head>

<body>
  <div id="content"></div>
</body>
</html>
"""
SCRIPT_LOAD=""" import("https://code.jquery.com/jquery-1.12.0.min.js") """
SCRIPT_LOAD=f""" import {{ $ }} from '{WBDIR}/docs/3rdparty/jQuery.js' """
SCRIPT = f"""\
  (async () => {{
  await import('{WBDIR}/docs/3rdparty/jQuery.js');
  }})();
"""
SCRIPT = f"""\
  (async () => {{
  await import('{WBDIR}/docs/3rdparty/jQuery.js'); }}
  $.when( $.ready).then(function() {{
    alert('ready');
    var now_body = $( "#body" ).text();
    $( "#body" ).html( marked.parse() );
    }});
"""
with open(f"{WBDIR}/docs/3rdparty/jQuery.js") as f:
    SCRIPT_JQUERY = f.read()
with open(f"{WBDIR}/docs/3rdparty/marked/marked.min.js") as f:
    SCRIPT_MARKED = f.read()
SCRIPT_RUN = f"""\
  $.when( $.ready).then(function() {{
    var now_body = $( "body" ).text();
    $( "body" ).html( marked.parse(now_body) );
    }});
"""

class HelpViewer(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loadFinished.connect(self.after_load)
        self.content = Content()
        self.content.new_content.connect(self.convert_markdown)
        self.convert = True

        scripts = self.page().scripts()

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


    @Slot(bool)
    def after_load(self, success):
        print("after_load")
        self.page().toHtml(self.content)  # Asynchronous!
        # self.page().runJavaScript(SCRIPT_LOAD)
        # self.page().runJavaScript(SCRIPT)
        # print("after_load")
        # if not self.convert:
            # # Protect with mutex?
            # self.convert = True
            # return

        # # Convert to html
        # if not success:
            # print("Load Failed")
            # return
        # self.page().toPlainText(self.content)  # Asynchronous!

    @Slot()
    def convert_markdown(self):
        print(self.content.text())
        return  # TODO
        self.convert = False
        print(self.content.text())
        html = markdown.markdown(self.content.text())
        url = QUrl(f"file://{WBDIR}")  # TODO
        self.setHtml(html, url)



def open_help():
    url = QUrl(f"file://{WBDIR}/README.md")
    base_url = QUrl(f"file://{WBDIR}")
    print(base_url)
    viewer = HelpViewer()
    mdiarea = Gui.getMainWindow().centralWidget()
    subw = mdiarea.addSubWindow(viewer)
    subw.setWindowTitle("Render help")
    subw.setVisible(True)
    # print(url)
    # viewer.setUrl(url)
    viewer.setUrl(url)
    viewer.show()
