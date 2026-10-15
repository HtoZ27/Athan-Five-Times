import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Popup {
    id: root

    // Full-window overlay: covers the application window like the
    // category dialog in AthkarTab, with a scrollable body so long
    // athkar are never truncated.
    x: 12
    y: 12
    width: parent ? parent.width - 24 : 440
    height: parent ? parent.height - 24 : 600
    modal: false
    closePolicy: Popup.CloseOnEscape
    padding: 16

    ThemeColors { id: theme }

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
        bodyScroll.contentY = 0
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
        color: theme.bgColor
        radius: 16
        border.color: theme.accentColor
        border.width: 2

        MouseArea {
            anchors.fill: parent
            onClicked: dismissPopup()
        }
    }

    contentItem: ColumnLayout {
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                id: titleText
                font.pixelSize: 22
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: theme.accentColor
            }

            Button {
                id: closeBtn
                text: "×"
                Layout.preferredWidth: 30
                Layout.preferredHeight: 28
                Layout.alignment: Qt.AlignTop
                background: Rectangle { color: theme.cardColor; border.color: theme.borderColor; border.width: 1; radius: 6 }
                contentItem: Text { text: parent.text; font.pixelSize: 16; font.bold: true; color: theme.textColor; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: dismissPopup()
            }
        }

        ScrollView {
            id: bodyScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Text {
                id: bodyText
                font.pixelSize: 20
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                width: bodyScroll.availableWidth
                color: theme.textColor
            }
        }
    }
}
