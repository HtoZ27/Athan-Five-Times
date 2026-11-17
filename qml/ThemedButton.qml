import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool primary: false
    property bool compact: false

    ThemeColors { id: theme }

    implicitHeight: compact ? 32 : 34
    implicitWidth: compact
        ? 32
        : Math.max(84, contentItem.implicitWidth + 24)
    font.pixelSize: 13
    hoverEnabled: true

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.primary
            ? "#ffffff"
            : (control.enabled ? theme.textColor : theme.textMutedColor)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 6
        color: control.primary
            ? (control.down
                ? Qt.darker(theme.accentColor, 1.15)
                : control.hovered ? Qt.lighter(theme.accentColor, 1.08) : theme.accentColor)
            : (control.down
                ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.25)
                : control.hovered
                    ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.15)
                    : theme.bgColor)
        border.color: control.primary ? theme.accentColor : theme.borderColor
        border.width: 1
        opacity: control.enabled ? 1.0 : 0.5
    }
}
