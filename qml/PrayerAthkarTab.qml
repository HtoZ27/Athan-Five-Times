import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Rectangle {
    id: root
    color: "transparent"

    ThemeColors { id: theme }

    property string prayerKey: ""
    property string prayerTitle: ""
    property var items: []

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function refresh() {
        var p = prayerEngine ? prayerEngine.getAthkarProvider() : null
        items = p ? p.getCategoryItems("after_prayer") : []
        listView.model = items
        if (p) titleLabel.text = p.getTitle() || tr("أذكار بعد الصلاة")
    }

    function retranslate() {
        var p = prayerEngine ? prayerEngine.getAthkarProvider() : null
        titleLabel.text = (p && p.getTitle()) || prayerTitle || tr("أذكار بعد الصلاة")
    }

    Component.onCompleted: refresh()
    Connections {
        target: prayerEngine
        function onPrayerTimesChanged() { refresh() }
        function onLanguageChanged() { refresh(); retranslate() }
    }
    Connections {
        target: l10n
        function onLanguageChanged() { retranslate() }
    }
    Connections {
        target: prayerEngine ? prayerEngine.getAthkarProvider() : null
        function onAthkarChanged() { refresh() }
    }

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "transparent"
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            Label {
                id: titleLabel
                text: prayerTitle || tr("أذكار بعد الصلاة")
                font.pixelSize: 20
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                color: theme.accentColor
            }

            ListView {
                id: listView
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                clip: true
                cacheBuffer: 200
                ScrollIndicator.vertical: ScrollIndicator { }

                delegate: AdhkarItemDelegate {
                    required property var modelData
                    required property int index

                    width: listView.width
                    itemData: modelData
                    itemIndex: index
                    athkarProvider: prayerEngine ? prayerEngine.getAthkarProvider() : null
                }
            }
        }
    }
}
