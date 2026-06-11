import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0
import "."

SettingsField {
    property string placeholder: ""
    property string text: ""
    property var validator
    property color backgroundColor: _pal.background
    property color borderColor: _pal.border
    property color placeholderTextColor: _pal.textMuted

    field: TextField {
        id: textField
        Layout.fillWidth: true
        placeholderText: root.placeholder
        text: root.text
        color: _pal.text
        placeholderTextColor: root.placeholderTextColor
        validator: root.validator
        background: Rectangle {
            color: root.backgroundColor
            radius: 6
            border.color: root.borderColor
            border.width: 1
        }
    }
}
