import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Rectangle {
    id: root

    property var itemData: null
    property int itemIndex: 0
    property var athkarProvider: null

    ThemeColors { id: theme }

    radius: 12
    color: Qt.rgba(theme.cardColor.r, theme.cardColor.g, theme.cardColor.b, 0.55)
    border.color: theme.borderColor
    border.width: 1

    height: Math.max(110, col.implicitHeight + 24)

    function numeral(n) {
        if (athkarProvider) return athkarProvider.toArabicNumeral(n)
        return String(n)
    }

    function refName(id) {
        var m = {
            "bukhari": "البخاري", "muslim": "مسلم", "abudawud": "أبو داود",
            "tirmidhi": "الترمذي", "ibnmajah": "ابن ماجه", "quran": "القرآن الكريم"
        }
        return m[id] || id
    }

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                radius: 7
                color: Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.15)

                Text {
                    anchors.centerIn: parent
                    text: numeral(itemIndex + 1)
                    font.pixelSize: 12
                    font.bold: true
                    color: theme.accentColor
                }
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                visible: itemData && itemData.count > 1
                Layout.preferredHeight: 24
                Layout.preferredWidth: chipText.implicitWidth + 16
                radius: 7
                color: Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.12)

                Text {
                    id: chipText
                    anchors.centerIn: parent
                    text: "× " + numeral(itemData ? itemData.count : 1) + " " + tr("مرات")
                    font.pixelSize: 11
                    font.bold: true
                    color: theme.accentColor
                }

    function tr(key) {
        if (typeof backendController === "undefined" || backendController === null)
            return key
        return backendController.translate(key)
    }
            }
        }

        Text {
            Layout.fillWidth: true
            text: itemData ? itemData.arabic : ""
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignRight
            color: theme.textColor
            font.pixelSize: 17
            font.bold: true
            lineHeight: 1.9
        }

        RowLayout {
            visible: itemData && (itemData.reference_detail || itemData.reference_id)
            Layout.fillWidth: true
            spacing: 4

            Text {
                text: "•"
                font.pixelSize: 12
                font.bold: true
                color: theme.accentColor
            }

            Text {
                Layout.fillWidth: true
                text: {
                    if (!itemData) return ""
                    var ref = refName(itemData.reference_id || "")
                    var det = itemData.reference_detail || ""
                    return det ? (ref ? ref + " " + det : det) : ref
                }
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                color: theme.textMutedColor
            }
        }
    }
}
