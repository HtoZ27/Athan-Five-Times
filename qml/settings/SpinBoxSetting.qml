import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0
import "."

SettingsField {
    property int from: 0
    property int to: 100
    property int value: 0
    property int stepSize: 1
    property color backgroundColor: _pal.surface
    property color borderColor: _pal.border

    field: SpinBox {
        id: spinBox
        Layout.fillWidth: true
        from: root.from
        to: root.to
        value: root.value
        stepSize: root.stepSize
        background: Rectangle {
            color: root.backgroundColor
            radius: 6
            border.color: root.borderColor
            border.width: 1
        }
        contentItem: Text {
            text: spinBox.textFromValue(spinBox.value)
            color: _pal.text
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            leftPadding: 8
            rightPadding: 8
        }
    }
}
