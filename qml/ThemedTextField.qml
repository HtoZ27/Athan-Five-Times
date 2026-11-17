import QtQuick
import QtQuick.Controls

TextField {
    id: control

    ThemeColors { id: theme }

    implicitHeight: 32
    font.pixelSize: 13
    color: theme.textColor
    placeholderTextColor: theme.textMutedColor
    selectionColor: theme.accentColor
    selectedTextColor: "#ffffff"
    leftPadding: 10
    rightPadding: 10
    verticalAlignment: Text.AlignVCenter

    background: Rectangle {
        color: theme.bgColor
        radius: 6
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: 1
    }
}
