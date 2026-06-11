import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

// Base field with label
Item {
    id: root
    Layout.fillWidth: true
    property string labelText: ""
    property var _pal: Theme.resolvePalette(
        typeof themeController !== 'undefined' && themeController
            ? themeController.resolvedTheme : "dark")
    property color textColor: _pal.text
    property alias field: fieldItem
    property alias layout: rowLayout

    RowLayout {
        id: rowLayout
        anchors.fill: parent
        spacing: 8

        Label {
            text: root.labelText
            color: root.textColor
            Layout.preferredWidth: 120
            verticalAlignment: Text.AlignVCenter
        }

        Item {
            id: fieldItem
            Layout.fillWidth: true
        }
    }
}
