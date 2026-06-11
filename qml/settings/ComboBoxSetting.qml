import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0
import "."

SettingsField {
    property var model: []
    property string textRole: "name"
    property int currentIndex: -1
    property color backgroundColor: _pal.surface
    property color borderColor: _pal.border

    field: ComboBox {
        id: comboBox
        Layout.fillWidth: true
        model: root.model
        textRole: root.textRole
        currentIndex: root.currentIndex
        editable: true
        background: Rectangle {
            color: root.backgroundColor
            radius: 6
            border.color: root.borderColor
            border.width: 1
        }
        contentItem: Text {
            text: comboBox.displayText
            color: _pal.text
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            leftPadding: 8
        }
    }
}
