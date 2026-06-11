import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

GroupBox {
    id: root
    Layout.fillWidth: true
    property string titleText: ""
    property var _pal: Theme.resolvePalette(
        typeof themeController !== 'undefined' && themeController
            ? themeController.resolvedTheme : "dark")
    property color textColor: _pal.text
    property color cardColor: _pal.surface
    property color borderColor: _pal.border

    label: Label {
        text: root.titleText
        color: root.textColor
        font.bold: true
    }

    background: Rectangle {
        color: root.cardColor
        radius: 8
        border.color: root.borderColor
        border.width: 1
    }
}
