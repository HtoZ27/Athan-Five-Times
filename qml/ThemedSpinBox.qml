import QtQuick
import QtQuick.Controls

SpinBox {
    id: control

    ThemeColors { id: theme }

    implicitHeight: 30
    implicitWidth: 104
    editable: true
    font.pixelSize: 13

    contentItem: TextInput {
        z: 2
        text: control.textFromValue(control.value, control.locale)
        font: control.font
        color: theme.textColor
        selectionColor: theme.accentColor
        selectedTextColor: "#ffffff"
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: control.inputMethodHints
        leftPadding: 26
        rightPadding: 26
    }

    up.indicator: Rectangle {
        x: control.mirrored ? 0 : parent.width - width
        height: parent.height
        implicitWidth: 24
        implicitHeight: 24
        color: control.up.pressed
            ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.3)
            : "transparent"

        Text {
            anchors.centerIn: parent
            text: "+"
            color: control.up.pressed ? theme.accentColor : theme.textMutedColor
            font.pixelSize: 14
            font.bold: true
        }
    }

    down.indicator: Rectangle {
        x: control.mirrored ? parent.width - width : 0
        height: parent.height
        implicitWidth: 24
        implicitHeight: 24
        color: control.down.pressed
            ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.3)
            : "transparent"

        Text {
            anchors.centerIn: parent
            text: "−"
            color: control.down.pressed ? theme.accentColor : theme.textMutedColor
            font.pixelSize: 14
            font.bold: true
        }
    }

    background: Rectangle {
        implicitWidth: 104
        color: theme.bgColor
        radius: 6
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: 1
    }
}
