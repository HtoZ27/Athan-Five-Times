import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Rectangle {
    id: root

    // Reactive palette - updates when themeController.resolvedTheme changes
    // Reactive palette - updates when themeController.resolvedTheme changes
    property var _pal: Theme.resolvePalette(
        typeof themeController !== 'undefined' && themeController
            ? themeController.resolvedTheme : "light")

    // Color properties - updated when theme changes
    property color bgColor: _pal.background
    property color cardColor: _pal.surface
    property color textColor: _pal.text
    property color accentColor: _pal.primary
    property color borderColor: _pal.border

    // Force _pal and colors update when themeController.resolvedTheme changes
    Connections {
        target: themeController
        function onResolvedThemeChanged(resolvedTheme) {
            _pal = Theme.resolvePalette(resolvedTheme)
            bgColor = _pal.background
            cardColor = _pal.surface
            textColor = _pal.text
            accentColor = _pal.primary
            borderColor = _pal.border
        }
    }

    color: Qt.rgba(bgColor.r, bgColor.g, bgColor.b, 0.55)
    radius: 10
    clip: true

    property var prayerModel: []

    function refresh() {
        prayerModel = prayerEngine ? prayerEngine.getPrayerTimes() : []
        listView.model = prayerModel
    }

    Component.onCompleted: refresh()
    Connections {
        target: prayerEngine
        function onPrayerTimesChanged() { refresh() }
    }

    ListView {
        id: listView
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        clip: true
        cacheBuffer: 30
        ScrollIndicator.vertical: ScrollIndicator { }

        delegate: Rectangle {
            required property var modelData

            width: listView.width - listView.leftMargin - listView.rightMargin
            height: 52
            radius: 12
            color: modelData && modelData.isNext ? accentColor : Qt.rgba(cardColor.r, cardColor.g, cardColor.b, 0.55)
            border.color: modelData && modelData.isNext ? "transparent" : borderColor
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16

                Label {
                    text: modelData ? modelData.name : ""
                    color: modelData && modelData.isNext ? "#ffffff" : textColor
                    font.bold: modelData && modelData.isNext
                    font.pixelSize: 16
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: modelData ? modelData.time : ""
                    color: modelData && modelData.isNext ? "#ffffff" : accentColor
                    font.bold: true
                    font.pixelSize: 16
                }
            }
        }
    }
}
