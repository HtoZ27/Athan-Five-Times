import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Theme 1.0

/*!
    Compact always-on-top prayer card.

    Design concept: a miniature of the app's "next prayer" hero card —
    same theme palette, same prayer icons, same countdown typography —
    wrapped in a slim header (hijri date · clock · close) and a thin
    progress bar tracking the current segment (previous → next prayer).
    The layout mirrors with the app language (RTL).

    Header / body / footer hierarchy:
        🗓 5 جمادى الأولى 1448 هـ      09:54:51  ✕
        ────────────────────────────────────────
                     الصلاة القادمة
                    [icon]  الظهر
                      02:09:31
                 ▓▓▓▓▓▓▓▓░░░░░░░░░░░░
              المغرب 18:47 • العشاء 20:03
*/
Window {
    id: widgetWindow
    width: 300
    height: 158
    flags: Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
    color: "transparent"
    title: widgetWindow.tr("أذان الأوقات الخمس")

    /** Set from backend/main.py after component creation. */
    property var prayerEngine: null

    readonly property bool isRtl:
        (typeof l10n !== "undefined" && l10n) ? l10n.isRtl : true

    // --- live data ---------------------------------------------------------
    property string nextKey: "fajr"
    property string nextName: "--"
    property string clockText: ""
    property string countdownText: "--:--:--"
    property string hijriDate: ""
    property string hijriEvent: ""
    property string preAlert: ""
    property var following: []
    property real progress: 0.0

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function refresh() {
        if (!prayerEngine)
            return
        nextKey = prayerEngine.getNextPrayerKey()
        nextName = prayerEngine.getNextPrayerName()
        clockText = prayerEngine.getClockText()
        countdownText = prayerEngine.getCountdownText()
        hijriDate = prayerEngine.getHijriDate()
        hijriEvent = prayerEngine.getHijriEvent()
        preAlert = prayerEngine.getPreAlert()
        following = prayerEngine.getFollowingPrayers()
        progress = prayerEngine.getProgressToNext()
    }

    /** Footer line: pre-alert > today's hijri event > upcoming prayers. */
    function footerLabel() {
        if (preAlert.length > 0)
            return preAlert
        if (hijriEvent.length > 0)
            return hijriEvent
        var parts = []
        for (var i = 0; i < following.length && i < 2; ++i) {
            var item = following[i]
            parts.push(item.name + " " + item.time
                       + (item.tomorrow ? " (" + tr("غداً") + ")" : ""))
        }
        return parts.join(" • ")
    }

    function footerColor() {
        if (preAlert.length > 0)
            return theme.warningColor
        if (hijriEvent.length > 0)
            return theme.accentColor
        return theme.textMutedColor
    }

    function saveGeometry() {
        if (!prayerEngine)
            return
        prayerEngine.saveWidgetGeometry(widgetWindow.x, widgetWindow.y)
    }

    function closeWidget() {
        if (typeof backendController !== "undefined" && backendController !== null)
            backendController.setWidgetVisible(false)
    }

    onPrayerEngineChanged: refresh()
    onVisibleChanged: if (visible) refresh()

    Connections {
        target: widgetWindow.prayerEngine
        function onCountdownChanged(text) { widgetWindow.countdownText = text }
        function onClockChanged(text) { widgetWindow.clockText = text }
        function onPreAlertChanged(text) { widgetWindow.preAlert = text }
        function onNextPrayerChanged() { widgetWindow.refresh() }
        function onPrayerTimesChanged() { widgetWindow.refresh() }
        function onDateChanged() { widgetWindow.refresh() }
        function onLanguageChanged() { widgetWindow.refresh() }
    }

    // Safety net: keeps clock/countdown/progress moving even when the engine
    // clock runs slow (background mode without a fast timer).
    Timer {
        interval: 1000
        running: widgetWindow.visible && widgetWindow.prayerEngine !== null
        repeat: true
        onTriggered: widgetWindow.refresh()
    }

    ThemeColors { id: theme }

    Rectangle {
        id: card
        anchors.fill: parent
        radius: Theme.radiusLarge
        color: Qt.rgba(theme.cardColor.r, theme.cardColor.g, theme.cardColor.b, 0.96)
        border.width: 1
        border.color: theme.borderColor

        LayoutMirroring.enabled: widgetWindow.isRtl
        LayoutMirroring.childrenInherit: true

        // Drag anywhere to move (persisted); double-click closes.
        MouseArea {
            id: dragArea
            anchors.fill: parent
            property point clickPos: Qt.point(0, 0)
            onPressed: (mouse) => { clickPos = Qt.point(mouse.x, mouse.y) }
            onPositionChanged: (mouse) => {
                widgetWindow.x += mouse.x - clickPos.x
                widgetWindow.y += mouse.y - clickPos.y
            }
            onReleased: widgetWindow.saveGeometry()
            onDoubleClicked: widgetWindow.closeWidget()
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // ---------- header: hijri date · clock · close ----------
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                Layout.leftMargin: 12
                Layout.rightMargin: 8
                spacing: 8

                Text {
                    text: widgetWindow.hijriDate
                    color: theme.accentColor
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    text: widgetWindow.clockText
                    color: theme.textMutedColor
                    font.pixelSize: 11
                    font.family: "IBM Plex Sans Arabic"
                    Layout.alignment: Qt.AlignVCenter
                }
                Rectangle {
                    id: closeBtn
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    Layout.alignment: Qt.AlignVCenter
                    radius: width / 2
                    color: closeArea.containsMouse
                        ? Qt.rgba(theme.dangerColor.r, theme.dangerColor.g,
                                  theme.dangerColor.b, 0.92)
                        : Qt.rgba(theme.borderColor.r, theme.borderColor.g,
                                  theme.borderColor.b, 0.4)
                    Behavior on color { ColorAnimation { duration: 120 } }
                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: 10
                        color: closeArea.containsMouse ? "white" : theme.textMutedColor
                    }
                    MouseArea {
                        id: closeArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: widgetWindow.closeWidget()
                    }
                    ToolTip.visible: closeArea.containsMouse
                    ToolTip.text: widgetWindow.tr("إغلاق الودجة")
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Qt.rgba(theme.borderColor.r, theme.borderColor.g,
                               theme.borderColor.b, 0.7)
            }

            // ---------- body: next-prayer hero ----------
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.topMargin: 4
                Layout.bottomMargin: 8
                Layout.leftMargin: 14
                Layout.rightMargin: 14
                spacing: 3

                Item { Layout.fillHeight: true }

                Text {
                    text: widgetWindow.tr("الصلاة القادمة")
                    color: theme.textMutedColor
                    font.pixelSize: 10
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 8

                    PrayerIcon {
                        prayerKey: widgetWindow.nextKey
                        active: true
                        iconSize: 30
                        Layout.preferredWidth: 30
                        Layout.preferredHeight: 30
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Text {
                        text: widgetWindow.nextName
                        color: theme.accentColor
                        font.pixelSize: 20
                        font.bold: true
                        Layout.alignment: Qt.AlignVCenter
                    }
                }

                Text {
                    text: widgetWindow.countdownText
                    color: theme.textColor
                    font.pixelSize: 22
                    font.family: "IBM Plex Sans Arabic"
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }

                Item {
                    id: progressTrack
                    objectName: "progressTrack"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 4
                    Layout.topMargin: 2
                    // The fill position is computed manually for RTL below, so
                    // keep Qt's automatic layout mirroring out of this subtree.
                    LayoutMirroring.enabled: false

                    Rectangle {
                        anchors.fill: parent
                        radius: 2
                        color: Qt.rgba(theme.borderColor.r, theme.borderColor.g,
                                       theme.borderColor.b, 0.55)
                    }

                    Rectangle {
                        id: progressFill
                        objectName: "progressFill"
                        height: parent.height
                        width: parent.width * Math.max(0, Math.min(1, widgetWindow.progress))
                        // RTL: the bar fills from the start (right) edge.
                        x: widgetWindow.isRtl ? parent.width - width : 0
                        radius: 2
                        color: theme.accentColor
                        Behavior on width { NumberAnimation { duration: 900; easing.type: Easing.Linear } }
                    }
                }

                Text {
                    text: widgetWindow.footerLabel()
                    color: widgetWindow.footerColor()
                    font.pixelSize: 11
                    font.bold: widgetWindow.preAlert.length > 0
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
