import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Rectangle {
    id: root
    color: "transparent"

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

    property string prayerKey: ""
    property string prayerTitle: ""

    function tr(key) {
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function retranslate() {
        titleLabel.text = prayerTitle || tr("أذكار بعد الصلاة")
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
                text: prayerTitle || tr("أذكار بعد الصلاة")
                font.pixelSize: 20
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                color: accentColor
            }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: Qt.rgba(cardColor.r, cardColor.g, cardColor.b, 0.55)
                    radius: 14
                    border.color: borderColor
                    border.width: 1

                Flickable {
                    id: flick
                    anchors.fill: parent
                    anchors.margins: 12
                    contentHeight: bodyText.height + 16
                    clip: true
                    ScrollIndicator.vertical: ScrollIndicator { }

                    Text {
                        id: bodyText
                        text: prayerEngine && prayerEngine.getAthkarProvider()
                            ? prayerEngine.getAthkarProvider().getPrayerAthkarText() : ""
                        wrapMode: Text.WordWrap
                        width: parent.width - 4
                        color: textColor
                        horizontalAlignment: Text.AlignHCenter
                        lineHeight: 1.8
                        font.pixelSize: 18
                        onHeightChanged: flick.contentHeight = bodyText.height + 16
                    }

                    Connections {
                        target: prayerEngine ? prayerEngine.getAthkarProvider() : null
                        function onAthkarChanged() {
                            if (prayerEngine && prayerEngine.getAthkarProvider()) {
                                bodyText.text = prayerEngine.getAthkarProvider().getPrayerAthkarText()
                                titleLabel.text = prayerEngine.getAthkarProvider().getTitle()
                            }
                        }
                    }
                }
            }
        }
    }
}
