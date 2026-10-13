import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Rectangle {
    id: root

    ThemeColors { id: theme }

    color: Qt.rgba(theme.bgColor.r, theme.bgColor.g, theme.bgColor.b, 0.55)
    radius: 10
    clip: true

    property var prayerModel: []

    function refresh() {
        var list = prayerEngine ? prayerEngine.getPrayerTimes() : []
        prayerModel = list
        listView.model = prayerModel
        // Keep the highlighted (next) prayer visible even in short windows.
        for (var i = 0; i < list.length; i++) {
            if (list[i].isNext) {
                listView.positionViewAtIndex(i, ListView.Contain)
                break
            }
        }
    }

    Component.onCompleted: refresh()
    Connections {
        target: prayerEngine
        function onPrayerTimesChanged() { refresh() }
        function onLanguageChanged() { refresh() }
    }

    ListView {
        id: listView
        anchors.fill: parent
        anchors.margins: 12
        spacing: 6
        clip: true
        cacheBuffer: 30
        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AlwaysOn
            width: 8
        }

        delegate: Rectangle {
            required property var modelData

            width: listView.width - listView.leftMargin - listView.rightMargin
            height: 50
            radius: 12
            color: modelData && modelData.isNext ? theme.accentColor : Qt.rgba(theme.cardColor.r, theme.cardColor.g, theme.cardColor.b, 0.55)
            border.color: modelData && modelData.isNext ? "transparent" : theme.borderColor
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 16
                spacing: 12

                PrayerIcon {
                    prayerKey: modelData ? modelData.key : "fajr"
                    active: modelData ? modelData.isNext : false
                    iconSize: 32
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                }

                Label {
                    text: modelData ? modelData.name : ""
                    color: modelData && modelData.isNext ? "#ffffff" : theme.textColor
                    font.bold: modelData && modelData.isNext
                    font.pixelSize: 16
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: modelData ? modelData.time : ""
                    color: modelData && modelData.isNext ? "#ffffff" : theme.accentColor
                    font.bold: true
                    font.pixelSize: 16
                }
            }
        }
    }
}
