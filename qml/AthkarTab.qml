import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Rectangle {
    id: root
    color: "transparent"

    ThemeColors { id: theme }

    property var categories: []
    property string openCategoryId: ""
    property string openCategoryName: ""
    property var openItems: []

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function catIconFile(icon) {
        var known = ["morning", "evening", "after_prayer", "sleep",
                     "waking", "home", "eating", "mosque", "travel", "dua"]
        var k = icon || "dua"
        if (known.indexOf(k) < 0) k = "dua"
        return "../assets/adhkar_icons/" + k + ".png"
    }

    function refresh() {
        var p = prayerEngine ? prayerEngine.getAthkarProvider() : null
        var all = p ? p.getCategories() : []
        categories = all.filter(function(c) { return c.id !== "after_prayer" })
        grid.model = categories
    }

    function openCategory(id, name) {
        openCategoryId = id
        openCategoryName = name
        var p = prayerEngine ? prayerEngine.getAthkarProvider() : null
        openItems = p ? p.getCategoryItems(id) : []
        catDialog.open()
    }

    function retranslate() {
        titleLabel.text = tr("الأذكار العامة")
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
                text: tr("الأذكار العامة")
                font.pixelSize: 20
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                color: theme.accentColor
            }

            GridView {
                id: grid
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                cellWidth: Math.floor(width / 3)
                cellHeight: 118
                model: categories

                delegate: Rectangle {
                    required property var modelData
                    required property int index

                    width: grid.cellWidth - 8
                    height: grid.cellHeight - 8
                    radius: 14
                    color: Qt.rgba(theme.cardColor.r, theme.cardColor.g, theme.cardColor.b, 0.55)
                    border.color: theme.borderColor
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 4

                        Image {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 40
                            source: catIconFile(modelData ? modelData.icon : "")
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                            cache: true
                            sourceSize.width: 128
                            sourceSize.height: 128
                        }

                        Text {
                            text: modelData ? modelData.name_ar : ""
                            font.pixelSize: 12
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            color: theme.textColor
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData) openCategory(modelData.id, modelData.name_ar)
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: catDialog
        modal: true
        parent: Overlay.overlay
        property real frameW: Overlay.overlay ? Overlay.overlay.width : 500
        property real frameH: Overlay.overlay ? Overlay.overlay.height : 800
        width: frameW - 24
        height: frameH - 24
        x: Math.round((frameW - width) / 2)
        y: Math.round((frameH - height) / 2)

        background: Rectangle {
            color: theme.bgColor
            radius: 16
            border.color: theme.borderColor
            border.width: 1
        }

        header: Rectangle {
            color: "transparent"
            height: 52

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 8
                spacing: 8

                Label {
                    id: dlgTitle
                    text: openCategoryName
                    font.pixelSize: 17
                    font.bold: true
                    color: theme.textColor
                    Layout.fillWidth: true
                }

                Button {
                    text: "×"
                    font.pixelSize: 16
                    implicitWidth: 36
                    implicitHeight: 36
                    background: Rectangle { color: "transparent" }
                    contentItem: Text { text: parent.text; color: theme.textMutedColor; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: catDialog.close()
                }
            }
        }

        ListView {
            id: dlgList
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8
            clip: true
            model: openItems
            ScrollIndicator.vertical: ScrollIndicator { }

            delegate: AdhkarItemDelegate {
                required property var modelData
                required property int index

                width: dlgList.width
                itemData: modelData
                itemIndex: index
                athkarProvider: prayerEngine ? prayerEngine.getAthkarProvider() : null
            }
        }
    }
}
