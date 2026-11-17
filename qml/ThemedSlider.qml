import QtQuick
import QtQuick.Controls

Slider {
    id: control

    ThemeColors { id: theme }

    implicitHeight: 28
    implicitWidth: 160
    hoverEnabled: true

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 4
        radius: 2
        color: theme.borderColor

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: theme.accentColor
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: 18
        implicitHeight: 18
        radius: 9
        color: control.hovered || control.pressed
            ? Qt.lighter(theme.accentColor, 1.1)
            : theme.accentColor
        border.color: theme.bgColor
        border.width: 2
    }
}
