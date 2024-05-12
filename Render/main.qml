import QtQuick
import QtQuick.Window
import QtWebEngine

Window {
    width: 1024
    height: 750
    visible: true
    WebEngineView {
        anchors.fill: parent
        url: "https://www.qt.io"
    }
}
