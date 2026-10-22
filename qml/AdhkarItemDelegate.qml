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

    height: Math.max(110, 12 + headerRow.height + 8 + bodyText.height
                        + (translationText.visible
                           ? 8 + translationLabel.height + 8 + translationText.height
                           : 0)
                        + (refRow.visible ? 8 + refRow.height : 0) + 12)

    function numeral(n) {
        if (athkarProvider) return athkarProvider.toArabicNumeral(n)
        return String(n)
    }

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function refName(id) {
        var m = {
            "bukhari": "البخاري", "muslim": "مسلم", "abudawud": "أبو داود",
            "tirmidhi": "الترمذي", "ibnmajah": "ابن ماجه", "quran": "القرآن الكريم",
            "ahmad": "أحمد", "nasai": "النسائي", "hakim": "الحاكم",
            "bayhaqi": "البيهقي", "hisn": "حصن المسلم"
        }
        return m[id] ? tr(m[id]) : id
    }

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        RowLayout {
            id: headerRow
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
                    text: itemData
                          ? (itemData.count > 1
                             ? "× " + numeral(itemData.count) + " " + tr("مرات")
                             : "× " + numeral(itemData.count))
                          : ""
                    font.pixelSize: 11
                    font.bold: true
                    color: theme.accentColor
                }
            }
        }

        Text {
            id: bodyText
            Layout.fillWidth: true
            text: itemData ? itemData.arabic : ""
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignRight
            color: theme.textColor
            font.pixelSize: 17
            font.bold: true
            lineHeight: 1.9
        }

        Text {
            id: translationLabel
            Layout.fillWidth: true
            visible: translationText.visible
            text: tr("الترجمة")
            color: theme.accentColor
            font.pixelSize: 10
            font.bold: true
            horizontalAlignment: (typeof l10n !== "undefined" && l10n && l10n.isRtl)
                                 ? Text.AlignRight : Text.AlignLeft
        }

        Text {
            id: translationText
            Layout.fillWidth: true
            visible: text !== ""
            text: {
                if (!itemData || !itemData.translations) return ""
                var lang = (typeof l10n !== "undefined" && l10n)
                           ? l10n.currentLanguage : "ar"
                if (lang === "ar") return ""
                return itemData.translations[lang] || ""
            }
            wrapMode: Text.WordWrap
            horizontalAlignment: (typeof l10n !== "undefined" && l10n && l10n.isRtl)
                                 ? Text.AlignRight : Text.AlignLeft
            color: theme.textMutedColor
            font.pixelSize: 13
            lineHeight: 1.6
        }

        RowLayout {
            id: refRow
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
                    if (!det) return ref
                    if (!ref) return det
                    return det.indexOf(ref) === 0 ? det : ref + " " + det
                }
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                color: theme.textMutedColor
            }
        }
    }
}
