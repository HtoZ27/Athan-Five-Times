import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Theme 1.0

ApplicationWindow {
    id: appWindow
    visible: true
    minimumWidth: 459
    minimumHeight: 795
    maximumWidth: 1590
    maximumHeight: 1080
    width: 500
    height: 800

    title: tr("أذان الأوقات الخمس")
    flags: Qt.FramelessWindowHint | Qt.Window
    color: "transparent"

    property bool isRtl: l10n ? l10n.isRtl : true
    LayoutMirroring.enabled: isRtl
    LayoutMirroring.childrenInherit: true

    property bool backgroundEnabled: true

    function tr(key) {
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function trPrayer(key) {
        var _ = l10n.currentLanguage
        return backendController.translatePrayer(key)
    }

    Connections {
        target: prayerEngine
        function onBackgroundEnabledChanged(enabled) {
            backgroundEnabled = enabled
        }
    }

    // Reactive palette - updates when themeController.resolvedTheme changes
    property var _pal: Theme.resolvePalette(themeController ? themeController.resolvedTheme : "light")

    // Color properties - updated when theme changes
    property color bgColor: _pal.background
    property color cardColor: _pal.surface
    property color textColor: _pal.text
    property color textMutedColor: _pal.textMuted
    property color accentColor: _pal.primary
    property color borderColor: _pal.border
    property color warningColor: _pal.warning
    property color dangerColor: _pal.error

    // Force _pal and colors update when themeController.resolvedTheme changes
    Connections {
        target: themeController
        function onResolvedThemeChanged(resolvedTheme) {
            _pal = Theme.resolvePalette(resolvedTheme)
            bgColor = _pal.background
            cardColor = _pal.surface
            textColor = _pal.text
            textMutedColor = _pal.textMuted
            accentColor = _pal.primary
            borderColor = _pal.border
            warningColor = _pal.warning
            dangerColor = _pal.error
        }
    }
    readonly property int rMed: Theme.radiusMedium
    readonly property int rLrg: Theme.radiusLarge
    readonly property int af: Theme.animFast
    readonly property int am: Theme.animMedium

    onClosing: function(close) {
        close.accepted = false
        saveGeometry()
        hide()
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
            appWindow.hide()
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
        color: bgColor
        clip: true

        Image {
            anchors.fill: parent
            source: "../assets/nabawi.webp"
            fillMode: Image.PreserveAspectCrop
            mipmap: false
            sourceSize.width: 960
            sourceSize.height: 560
            cache: false
            visible: backgroundEnabled
        }

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(bgColor.r, bgColor.g, bgColor.b, 0.55) }
                GradientStop { position: 1.0; color: Qt.rgba(bgColor.r, bgColor.g, bgColor.b, 0.25) }
            }
            visible: backgroundEnabled
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 0

            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 30
                spacing: 4

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    property point clickPos: Qt.point(0, 0)
                    onPressed: clickPos = Qt.point(mouse.x, mouse.y)
                    onPositionChanged: {
                        appWindow.x += mouse.x - clickPos.x
                        appWindow.y += mouse.y - clickPos.y
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
                    color: textMutedColor
                    verticalAlignment: Text.AlignVCenter
                    Layout.alignment: Qt.AlignVCenter
                }

                Item { Layout.fillWidth: true }

                Button {
                    id: minimizeBtn
                    width: 26; height: 22
                    background: Rectangle { color: cardColor; border.color: borderColor; border.width: 1; radius: 4 }
                    contentItem: Text { text: "—"; font.pixelSize: 12; font.bold: true; color: textMutedColor; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: appWindow.showMinimized()
                }

                Button {
                    id: closeBtn
                    width: 26; height: 22
                    background: Rectangle { color: dangerColor; radius: 4 }
                    contentItem: Text { text: "×"; font.pixelSize: 14; font.bold: true; color: "#fff"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { saveGeometry(); appWindow.close() }
                }
            }

            Rectangle {
                id: headerBg
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                radius: rLrg
                border.color: borderColor
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
                        color: accentColor
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.3)
                        Layout.margins: 8
                    }

                    Text {
                        id: dateText
                        text: prayerEngine ? prayerEngine.getGregorianDate() : ""
                        font.pixelSize: 16
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: textColor
                    }

                    Text {
                        id: hijriText
                        text: prayerEngine ? prayerEngine.getHijriDate() : ""
                        font.pixelSize: 16
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: accentColor
                    }

                    Text {
                        id: locationText
                        text: prayerEngine ? prayerEngine.getLocationText() : ""
                        font.pixelSize: 14
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: textMutedColor
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
                color: Qt.rgba(cardColor.r, cardColor.g, cardColor.b, 0.55)
                radius: 14
                border.color: accentColor
                border.width: 1

                Rectangle {
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 60
                    height: 3
                    radius: 2
                    color: accentColor
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
                        color: textMutedColor
                    }

                    Text {
                        id: nextNameText
                        text: prayerEngine ? prayerEngine.getNextPrayerName() : "--"
                        font.pixelSize: 16
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: accentColor
                    }

                    Text {
                        id: countdownText
                        text: prayerEngine ? prayerEngine.getCountdownText() : "--:--:--"
                        font.pixelSize: 20
                        font.family: "IBM Plex Sans Arabic"
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: textColor
                    }

                    Text {
                        id: preAlertText
                        text: prayerEngine ? prayerEngine.getPreAlert() : ""
                        font.pixelSize: 12
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        color: warningColor
                        visible: text.length > 0
                    }
                }

                Connections {
                    target: prayerEngine
                    function onNextPrayerChanged() {
                        nextNameText.text = prayerEngine.getNextPrayerName()
                        nextNameText.opacity = 0.0
                        nextNameText.opacity = 1.0
                    }
                    function onCountdownChanged(text) { countdownText.text = text }
                    function onPreAlertChanged(text) {
                        preAlertText.text = text
                        preAlertText.visible = text.length > 0
                    }
                }
            }

            TabBar {
                id: mainTabBar
                Layout.fillWidth: true
                Layout.topMargin: 8
                Layout.preferredHeight: 38
                background: Rectangle { color: Qt.rgba(cardColor.r, cardColor.g, cardColor.b, 0.55); radius: rMed; border.color: borderColor; border.width: 1 }

                TabButton {
                    id: tab0
                    text: tr("أوقات الصلاة")
                    font.pixelSize: 13
                    hoverEnabled: true
                    ToolTip.text: tr("أوقات الصلاة")
                    ToolTip.visible: hovered
                    background: Rectangle { color: mainTabBar.currentIndex === 0 ? accentColor : "transparent"; radius: rMed }
                    contentItem: Text {
                        text: parent.text
                        color: mainTabBar.currentIndex === 0 ? "#fff" : textColor
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
                    background: Rectangle { color: mainTabBar.currentIndex === 1 ? accentColor : "transparent"; radius: rMed }
                    contentItem: Text {
                        text: parent.text
                        color: mainTabBar.currentIndex === 1 ? "#fff" : textColor
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
                    background: Rectangle { color: mainTabBar.currentIndex === 2 ? accentColor : "transparent"; radius: rMed }
                    contentItem: Text {
                        text: parent.text
                        color: mainTabBar.currentIndex === 2 ? "#fff" : textColor
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
                currentIndex: mainTabBar.currentIndex

                PrayerTimesTab {}
                PrayerAthkarTab {}
                AthkarTab {}
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                color: Qt.rgba(bgColor.r, bgColor.g, bgColor.b, 0.55)
                radius: rMed

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16

                    Item { Layout.fillWidth: true }

                    Button {
                        id: azanStopBtn
                        text: tr("إيقاف الأذان")
                        visible: prayerEngine ? prayerEngine.isAzanPlaying() : false
                        onClicked: prayerEngine.stopAzan()
                        font.pixelSize: 14
                        background: Rectangle { color: dangerColor; radius: 8 }
                        contentItem: Text { text: parent.text; color: "#fff"; font.pixelSize: 14; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }

                    Button {
                        id: creditsBtn
                        text: tr("عن البرنامج")
                        onClicked: creditsDialog.open()
                        font.pixelSize: 14
                        background: Rectangle { color: "transparent"; border.color: accentColor; border.width: 1; radius: 8 }
                        contentItem: Text { text: parent.text; color: accentColor; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }

                    Button {
                        id: settingsBtn
                        text: tr("الإعدادات")
                        onClicked: settingsDialog.open()
                        font.pixelSize: 14
                        background: Rectangle { color: accentColor; radius: 8 }
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
