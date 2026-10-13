import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Qt5Compat.GraphicalEffects
import Theme 1.0

ApplicationWindow {
    id: appWindow
    visible: true
    minimumWidth: 460
    minimumHeight: 795
    maximumWidth: 1590
    maximumHeight: 1080
    width: 500
    height: 840

    title: tr("أذان الأوقات الخمس")
    flags: Qt.FramelessWindowHint | Qt.Window
    color: "transparent"

    property bool isRtl: l10n ? l10n.isRtl : true
    LayoutMirroring.enabled: isRtl
    LayoutMirroring.childrenInherit: true

    property bool backgroundEnabled: true

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    Connections {
        target: prayerEngine
        function onBackgroundEnabledChanged(enabled) {
            backgroundEnabled = enabled
        }
    }

    ThemeColors { id: theme }
    readonly property int rMed: Theme.radiusMedium
    readonly property int rLrg: Theme.radiusLarge
    readonly property int af: Theme.animFast
    readonly property int am: Theme.animMedium

    onClosing: {
        saveGeometry()
        if (prayerEngine) prayerEngine.quitApp()
    }

    function saveGeometry() {
        try {
            prayerEngine.updateSetting("window_geometry",
                [appWindow.x, appWindow.y, appWindow.width, appWindow.height])
        } catch (e) {}
    }

    property bool backgroundMode: false

    onVisibilityChanged: {
        var bg = (appWindow.visibility === Window.Hidden
            || appWindow.visibility === Window.Minimized)
        if (bg !== backgroundMode) {
            backgroundMode = bg
            if (prayerEngine) prayerEngine.setBackgroundMode(bg)
        }
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            saveGeometry()
            var showTray = prayerEngine ? prayerEngine.getSetting("show_tray") : true
            if (showTray === undefined || showTray === null) showTray = true
            var trayOk = (typeof trayAvailable !== "undefined") && trayAvailable
            if (trayOk && showTray) appWindow.hide()
            else appWindow.showMinimized()
        }
    }

    Shortcut {
        sequence: "Ctrl+Q"
        onActivated: {
            saveGeometry()
            if (prayerEngine) prayerEngine.quitApp()
            else Qt.quit()
        }
    }

    AthkarPopup { id: athkarPopup }

    Connections {
        target: prayerEngine
        function onAthkarShown(prayerKey, title, durationMs, text, isDark) {
            athkarPopup.showPopup(prayerKey, title, durationMs, text, isDark)
        }
    }

    function retranslate() {
        title = tr("أذان الأوقات الخمس")
        tab0.text = tr("أوقات الصلاة")
        tab0.ToolTip.text = tr("أوقات الصلاة")
        tab1.text = tr("أذكار الصلاة")
        tab1.ToolTip.text = tr("أذكار الصلاة")
        tab2.text = tr("الأذكار العامة")
        tab2.ToolTip.text = tr("الأذكار العامة")
        titleText.text = tr("أذان الأوقات الخمس")
        nextPrayerLabel.text = tr("الصلاة القادمة")
        azanStopBtn.text = tr("إيقاف الأذان")
        creditsBtn.text = tr("عن البرنامج")
        settingsBtn.text = tr("الإعدادات")
    }

    Connections {
        target: l10n
        function onLanguageChanged() { retranslate() }
    }

    CreditsDialog { id: creditsDialog }

    Rectangle {
        id: windowBackground
        anchors.fill: parent
        radius: 20
        color: theme.bgColor
        clip: true

        // Full-bleed static layers clipped to the same rounded shape as
        // the window background (like the compositor-side rounded rect of
        // COSMIC panels): without this mask the square photo/gradient
        // would paint over the rounded outer corners. Static content, so
        // the layer is cached and costs nothing per frame.
        Item {
            anchors.fill: parent
            layer.enabled: true
            layer.smooth: true
            layer.effect: OpacityMask {
                maskSource: Rectangle {
                    width: windowBackground.width
                    height: windowBackground.height
                    radius: windowBackground.radius
                }
            }

            Image {
                anchors.fill: parent
                source: backgroundEnabled ? "../assets/nabawi.webp" : ""
                fillMode: Image.PreserveAspectCrop
                mipmap: false
                sourceSize.width: 640
                sourceSize.height: 373
                cache: true
                asynchronous: true
            }

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Qt.rgba(theme.bgColor.r, theme.bgColor.g, theme.bgColor.b, 0.55) }
                    GradientStop { position: 1.0; color: Qt.rgba(theme.bgColor.r, theme.bgColor.g, theme.bgColor.b, 0.25) }
                }
                visible: backgroundEnabled
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 30
                Layout.minimumHeight: 30
                Layout.maximumHeight: 30
                spacing: 4

                MouseArea {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    acceptedButtons: Qt.LeftButton
                    property point pressGlobal: Qt.point(0, 0)
                    property point winPos: Qt.point(0, 0)
                    onPressed: {
                        pressGlobal = mapToGlobal(mouse.x, mouse.y)
                        winPos = Qt.point(appWindow.x, appWindow.y)
                    }
                    onPositionChanged: {
                        if (pressed) {
                            var g = mapToGlobal(mouse.x, mouse.y)
                            appWindow.x = winPos.x + g.x - pressGlobal.x
                            appWindow.y = winPos.y + g.y - pressGlobal.y
                        }
                    }
                }

                Image {
                    source: "../assets/kaaba.svg"
                    sourceSize.width: 18
                    sourceSize.height: 18
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    id: titleText
                    text: tr("أذان الأوقات الخمس")
                    font.pixelSize: 15
                    font.bold: true
                    color: theme.textMutedColor
                    verticalAlignment: Text.AlignVCenter
                    Layout.alignment: Qt.AlignVCenter
                }

                Item { Layout.fillWidth: true }

                Button {
                    id: minimizeBtn
                    width: 26; height: 22
                    background: Rectangle { color: theme.cardColor; border.color: theme.borderColor; border.width: 1; radius: 4 }
                    contentItem: Text { text: "—"; font.pixelSize: 12; font.bold: true; color: theme.textMutedColor; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: appWindow.showMinimized()
                }

                Button {
                    id: maxRestoreBtn
                    width: 26; height: 22
                    background: Rectangle { color: theme.cardColor; border.color: theme.borderColor; border.width: 1; radius: 4 }
                    contentItem: Text { id: maxRestoreText; text: "□"; font.pixelSize: 12; font.bold: true; color: theme.textMutedColor; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: {
                        if (appWindow.visibility === Window.Maximized) {
                            appWindow.showNormal()
                        } else {
                            appWindow.showMaximized()
                        }
                    }
                }

                Button {
                    id: closeBtn
                    width: 26; height: 22
                    background: Rectangle { color: theme.dangerColor; radius: 4 }
                    contentItem: Text { text: "×"; font.pixelSize: 14; font.bold: true; color: "#fff"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { saveGeometry(); appWindow.close() }
                }
            }

            Rectangle {
                id: headerBg
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                radius: rLrg
                border.color: theme.borderColor
                border.width: 1
                color: "transparent"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 4

                    Text {
                        id: clockText
                        text: prayerEngine ? prayerEngine.getClockText() : ""
                        font.pixelSize: 44
                        font.family: "IBM Plex Sans Arabic"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: theme.accentColor
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.3)
                        Layout.margins: 8
                    }

                    Text {
                        id: dateText
                        text: prayerEngine ? prayerEngine.getGregorianDate() : ""
                        font.pixelSize: 16
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: theme.textColor
                    }

                    Text {
                        id: hijriText
                        text: prayerEngine ? prayerEngine.getHijriDate() : ""
                        font.pixelSize: 16
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: theme.accentColor
                    }

                    Text {
                        id: locationText
                        text: prayerEngine ? prayerEngine.getLocationText() : ""
                        font.pixelSize: 14
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: theme.textMutedColor
                        visible: text.length > 0
                    }
                }

                Connections {
                    target: prayerEngine
                    function onClockChanged(text) { clockText.text = text }
                    function onDateChanged() {
                        dateText.text = prayerEngine.getGregorianDate()
                        hijriText.text = prayerEngine.getHijriDate()
                    }
                    function onLocationChanged() {
                        locationText.text = prayerEngine.getLocationText()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: nextPrayerBox.height + 24
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.topMargin: 8
                color: Qt.rgba(theme.cardColor.r, theme.cardColor.g, theme.cardColor.b, 0.55)
                radius: 14
                border.color: theme.accentColor
                border.width: 1

                Rectangle {
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 60
                    height: 3
                    radius: 2
                    color: theme.accentColor
                    anchors.topMargin: -1
                }

                ColumnLayout {
                    id: nextPrayerBox
                    anchors.centerIn: parent
                    spacing: 2

                    Text {
                        id: nextPrayerLabel
                        text: tr("الصلاة القادمة")
                        font.pixelSize: 12
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: theme.textMutedColor
                    }

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 10

                        PrayerIcon {
                            id: nextPrayerIcon
                            prayerKey: prayerEngine ? prayerEngine.getNextPrayerKey() : "fajr"
                            active: true
                            iconSize: 44
                            Layout.preferredWidth: 44
                            Layout.preferredHeight: 44
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Text {
                            id: nextNameText
                            text: prayerEngine ? prayerEngine.getNextPrayerName() : "--"
                            font.pixelSize: 18
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignVCenter
                            color: theme.accentColor
                            Behavior on opacity { NumberAnimation { duration: 200 } }
                        }
                    }

                    Text {
                        id: countdownText
                        text: prayerEngine ? prayerEngine.getCountdownText() : "--:--:--"
                        font.pixelSize: 20
                        font.family: "IBM Plex Sans Arabic"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: theme.textColor
                    }

                    Text {
                        id: preAlertText
                        text: prayerEngine ? prayerEngine.getPreAlert() : ""
                        font.pixelSize: 12
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: theme.warningColor
                        visible: text.length > 0
                    }
                }

                Connections {
                    target: prayerEngine
                    function onNextPrayerChanged() {
                        nextNameText.text = prayerEngine.getNextPrayerName()
                        nextPrayerIcon.prayerKey = prayerEngine.getNextPrayerKey()
                        nextNameText.opacity = 0.0
                        nextNameText.opacity = 1.0
                    }
                    function onCountdownChanged(text) { countdownText.text = text }
                    function onPreAlertChanged(text) {
                        preAlertText.text = text
                    }
                }
            }

            TabBar {
                id: mainTabBar
                Layout.fillWidth: true
                Layout.topMargin: 8
                Layout.preferredHeight: 38
                background: Rectangle { color: Qt.rgba(theme.cardColor.r, theme.cardColor.g, theme.cardColor.b, 0.55); radius: rMed; border.color: theme.borderColor; border.width: 1 }

                TabButton {
                    id: tab0
                    text: tr("أوقات الصلاة")
                    font.pixelSize: 13
                    hoverEnabled: true
                    ToolTip.text: tr("أوقات الصلاة")
                    ToolTip.visible: hovered
                    background: Rectangle { color: mainTabBar.currentIndex === 0 ? theme.accentColor : "transparent"; radius: rMed }
                    contentItem: Text {
                        text: parent.text
                        color: mainTabBar.currentIndex === 0 ? "#fff" : theme.textColor
                        font.pixelSize: 13
                        font.bold: mainTabBar.currentIndex === 0
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                TabButton {
                    id: tab1
                    text: tr("أذكار الصلاة")
                    font.pixelSize: 13
                    hoverEnabled: true
                    ToolTip.text: tr("أذكار الصلاة")
                    ToolTip.visible: hovered
                    background: Rectangle { color: mainTabBar.currentIndex === 1 ? theme.accentColor : "transparent"; radius: rMed }
                    contentItem: Text {
                        text: parent.text
                        color: mainTabBar.currentIndex === 1 ? "#fff" : theme.textColor
                        font.pixelSize: 13
                        font.bold: mainTabBar.currentIndex === 1
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                TabButton {
                    id: tab2
                    text: tr("الأذكار العامة")
                    font.pixelSize: 13
                    hoverEnabled: true
                    ToolTip.text: tr("الأذكار العامة")
                    ToolTip.visible: hovered
                    background: Rectangle { color: mainTabBar.currentIndex === 2 ? theme.accentColor : "transparent"; radius: rMed }
                    contentItem: Text {
                        text: parent.text
                        color: mainTabBar.currentIndex === 2 ? "#fff" : theme.textColor
                        font.pixelSize: 13
                        font.bold: mainTabBar.currentIndex === 2
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 150
                currentIndex: mainTabBar.currentIndex

                PrayerTimesTab {}
                PrayerAthkarTab {}
                AthkarTab {}
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                color: Qt.rgba(theme.bgColor.r, theme.bgColor.g, theme.bgColor.b, 0.55)
                radius: rMed

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16

                    Item { Layout.fillWidth: true }

                    Button {
                        id: azanStopBtn
                        text: tr("إيقاف الأذان")
                        visible: false
                        onClicked: prayerEngine.stopAzan()
                        font.pixelSize: 14
                        background: Rectangle { color: theme.dangerColor; radius: 8 }
                        contentItem: Text { text: parent.text; color: "#fff"; font.pixelSize: 14; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }

                    Button {
                        id: creditsBtn
                        text: tr("عن البرنامج")
                        onClicked: creditsDialog.open()
                        font.pixelSize: 14
                        background: Rectangle { color: "transparent"; border.color: theme.accentColor; border.width: 1; radius: 8 }
                        contentItem: Text { text: parent.text; color: theme.accentColor; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }

                    Button {
                        id: settingsBtn
                        text: tr("الإعدادات")
                        onClicked: settingsDialog.open()
                        font.pixelSize: 14
                        background: Rectangle { color: theme.accentColor; radius: 8 }
                        contentItem: Text { text: parent.text; color: "#fff"; font.pixelSize: 14; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }

                Connections {
                    target: prayerEngine
                    function onAzanPlayingChanged(playing) { azanStopBtn.visible = playing }
                }
            }
        }
    }

    SettingsDialog { id: settingsDialog }

    Component.onCompleted: {
        if (prayerEngine) {
            backgroundEnabled = prayerEngine.getSetting("background_enabled") !== false
        }
    }

    Item {
        id: resizeHandles
        anchors.fill: parent
        z: 99
        LayoutMirroring.enabled: false

        readonly property int hs: 8

        MouseArea { LayoutMirroring.enabled: false; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: resizeHandles.hs; cursorShape: Qt.SizeVerCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.TopEdge) }
        MouseArea { LayoutMirroring.enabled: false; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: resizeHandles.hs; cursorShape: Qt.SizeVerCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.BottomEdge) }
        MouseArea { LayoutMirroring.enabled: false; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.left: parent.left; width: resizeHandles.hs; cursorShape: Qt.SizeHorCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.LeftEdge) }
        MouseArea { LayoutMirroring.enabled: false; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right; width: resizeHandles.hs; cursorShape: Qt.SizeHorCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.RightEdge) }
        MouseArea { LayoutMirroring.enabled: false; anchors.top: parent.top; anchors.left: parent.left; width: resizeHandles.hs * 2; height: resizeHandles.hs * 2; cursorShape: Qt.SizeFDiagCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.TopEdge | Qt.LeftEdge) }
        MouseArea { LayoutMirroring.enabled: false; anchors.top: parent.top; anchors.right: parent.right; width: resizeHandles.hs * 2; height: resizeHandles.hs * 2; cursorShape: Qt.SizeBDiagCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.TopEdge | Qt.RightEdge) }
        MouseArea { LayoutMirroring.enabled: false; anchors.bottom: parent.bottom; anchors.left: parent.left; width: resizeHandles.hs * 2; height: resizeHandles.hs * 2; cursorShape: Qt.SizeBDiagCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.BottomEdge | Qt.LeftEdge) }
        MouseArea { LayoutMirroring.enabled: false; anchors.bottom: parent.bottom; anchors.right: parent.right; width: resizeHandles.hs * 2; height: resizeHandles.hs * 2; cursorShape: Qt.SizeFDiagCursor; hoverEnabled: true; onPressed: appWindow.startSystemResize(Qt.BottomEdge | Qt.RightEdge) }
    }
}
