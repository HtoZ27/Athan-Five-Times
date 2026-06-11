import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0
import "."

SettingsField {
    property real from: 0
    property real to: 1
    property real value: 0.5
    property real stepSize: 0.01
    property string suffix: ""

    field: RowLayout {
        Layout.fillWidth: true
        spacing: 8
        Slider {
            id: slider
            Layout.fillWidth: true
            from: root.from
            to: root.to
            value: root.value
            stepSize: root.stepSize
            background: Rectangle {
                height: 4
                radius: 2
                color: root._pal.border
            }
            contentItem: Rectangle {
                implicitHeight: 4
                radius: 2
                color: root._pal.primary
                width: slider.visualPosition * slider.width
            }
            handle: Rectangle {
                width: 16
                height: 16
                radius: 8
                color: root._pal.primary
                border.color: root._pal.text
                border.width: 2
                x: slider.visualPosition * (slider.width - width)
            }
        }
        Label {
            text: (slider.value * (root.suffix === "%" ? 100 : 1)).toFixed(root.suffix === "%" ? 0 : 2) + root.suffix
            color: _pal.text
            Layout.preferredWidth: 50
        }
    }
}
