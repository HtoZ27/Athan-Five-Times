import QtQuick
import QtQuick.Controls
import Theme 1.0
import "."

SettingsField {
    property bool checked: false
    property string indicatorColor: _pal.primary

    field: CheckBox {
        id: checkBox
        checked: root.checked
        indicator: Rectangle {
            implicitWidth: 20
            implicitHeight: 20
            radius: 4
            border.color: checkBox.checked ? root.indicatorColor : root._pal.border
            border.width: 2
            color: checkBox.checked ? root.indicatorColor : "transparent"
            Rectangle {
                anchors.centerIn: parent
                width: 10
                height: 10
                visible: checkBox.checked
                color: "#fff"
            }
        }
        contentItem: Text {
            text: checkBox.text
            color: _pal.text
            font.pixelSize: 13
        }
    }
}
