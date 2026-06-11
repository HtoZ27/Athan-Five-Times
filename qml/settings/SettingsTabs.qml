import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

RowLayout {
    id: root
    Layout.fillWidth: true
    Layout.preferredHeight: 36
    spacing: 2
    property int currentIndex: 0
    property var model: []

    Item { Layout.fillWidth: true }

    Repeater {
        model: root.model
        delegate: Rectangle {
            id: tabRect
            required property var modelData
            required property int index
            implicitWidth: tabLabel.implicitWidth + 20
            implicitHeight: 36
            color: root.currentIndex === index ? root._pal.primary : "transparent"
            radius: 6
            Behavior on color { ColorAnimation { duration: 120 } }

            Label {
                id: tabLabel
                anchors.centerIn: parent
                text: modelData
                color: root.currentIndex === index ? "#fff" : root._pal.text
                font.pixelSize: 12
                font.bold: root.currentIndex === index
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.currentIndex = index
            }
        }
    }

    Item { Layout.fillWidth: true }
}
