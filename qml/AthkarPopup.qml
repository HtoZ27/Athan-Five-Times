import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Popup {
    id: root

    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: Math.min(440, parent ? parent.width * 0.92 : 440)
    height: implicitHeight
    modal: false
    closePolicy: Popup.CloseOnEscape
    padding: 20

    // Reactive palette - updates when themeController.resolvedTheme changes
    property var _pal: Theme.resolvePalette(
        typeof themeController !== 'undefined' && themeController
            ? themeController.resolvedTheme : "light")

    // Color properties - updated when theme changes
    property color accentColor: _pal.primary
    property color textColor: _pal.text

    // Force _pal and colors update when themeController.resolvedTheme changes
    Connections {
        target: themeController
        function onResolvedThemeChanged(resolvedTheme) {
            _pal = Theme.resolvePalette(resolvedTheme)
            accentColor = _pal.primary
            textColor = _pal.text
        }
    }

    property string prayerKey: ""
    property string popupTitle: ""
    property int durationMs: 7000
    property string athkarText: ""
    property bool isDark: true

    signal dismissed()

    function showPopup(key, title, dur, text, dark) {
        prayerKey = key
        popupTitle = title
        durationMs = dur
        athkarText = text
        isDark = dark
        bodyText.text = text
        titleText.text = title
        open()
        autoTimer.interval = dur
        autoTimer.start()
    }

    function dismissPopup() {
        autoTimer.stop()
        close()
    }

    Timer { id: autoTimer; onTriggered: dismissPopup() }

    onClosed: dismissed()

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 300; easing.type: Easing.OutCubic }
    }

    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 300; easing.type: Easing.InCubic }
    }

    background: Rectangle {
        color: isDark ? "#1a1a1e" : "#f5f5f7"
        radius: 16
        border.color: accentColor
        border.width: 2

        MouseArea {
            anchors.fill: parent
            onClicked: dismissPopup()
        }
    }

    contentItem: ColumnLayout {
        spacing: 12

        Text {
            id: titleText
            font.pixelSize: 24
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
            color: accentColor
        }

        Text {
            id: bodyText
            font.pixelSize: 22
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
            maximumLineCount: 6
            elide: Text.ElideNone
            color: textColor
        }
    }
}
