import QtQuick
import QtQuick.Controls

CheckBox {
    id: control

    ThemeColors { id: theme }

    implicitHeight: Math.max(28, contentItem.implicitHeight + 4)
    padding: 0
    spacing: 8
    font.pixelSize: 13
    hoverEnabled: true

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? theme.textColor : theme.textMutedColor
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
        leftPadding: control.mirrored ? control.indicator.width + control.spacing : 0
        rightPadding: control.mirrored ? 0 : control.indicator.width + control.spacing
    }

    indicator: Rectangle {
        implicitWidth: 20
        implicitHeight: 20
        x: control.mirrored
            ? control.width - width - control.rightPadding
            : control.leftPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        radius: 4
        color: control.checked
            ? theme.accentColor
            : (control.hovered ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.12)
                               : "transparent")
        border.color: control.checked || control.hovered ? theme.accentColor : theme.borderColor
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: "✓"
            visible: control.checked
            color: "#ffffff"
            font.pixelSize: 13
            font.bold: true
        }
    }
}
