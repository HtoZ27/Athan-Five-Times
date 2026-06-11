import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Dialog {
    id: root
    title: backendController.translate("عن البرنامج")

    width: 460
    height: 560
    modal: true

    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    property var __pal: Theme.resolvePalette(
        typeof themeController !== 'undefined' && themeController
            ? themeController.resolvedTheme : "light")

    property color bgColor: __pal.background
    property color cardColor: __pal.surface
    property color textColor: __pal.text
    property color accentColor: __pal.primary
    property color secondaryTextColor: __pal.textMuted
    property color borderColor: __pal.border

    Connections {
        target: themeController
        function onResolvedThemeChanged(resolvedTheme) {
            __pal = Theme.resolvePalette(resolvedTheme)
            bgColor = __pal.background
            cardColor = __pal.surface
            textColor = __pal.text
            accentColor = __pal.primary
            secondaryTextColor = __pal.textMuted
            borderColor = __pal.border
        }
    }

    background: Rectangle {
        color: bgColor
        radius: 16
        border.color: borderColor
        border.width: 1
    }

    header: Rectangle {
        color: "transparent"
        height: 140
        width: parent.width

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 8

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 72
                height: 72
                radius: 36
                color: accentColor

                Image {
                    anchors.centerIn: parent
                    width: 44
                    height: 44
                    source: "../assets/kaaba.svg"
                    fillMode: Image.PreserveAspectFit
                }
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: backendController.translate("أذان الصلاة")
                font.pixelSize: 22
                font.bold: true
                color: textColor
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: backendController.translate("تطبيق مفتوح المصدر لأوقات الصلاة والأذان")
                font.pixelSize: 13
                color: secondaryTextColor
            }
        }
    }

    contentItem: ColumnLayout {
        spacing: 0
        Layout.fillWidth: true
        Layout.fillHeight: true

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            height: 1
            color: borderColor
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: 12
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                spacing: 12

                Label {
                    Layout.fillWidth: true
                    text: backendController.translate("المكتبات المستخدمة")
                    font.pixelSize: 14
                    font.bold: true
                    color: accentColor
                }

                Text {
                    Layout.fillWidth: true
                    text: prayerEngine ? prayerEngine.getCreditsHtml() : ""
                    textFormat: Text.RichText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                    color: textColor
                    onLinkActivated: function(link) {
                        Qt.openUrlExternally(link)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            height: 1
            color: borderColor
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: 12
            Layout.bottomMargin: 4
            spacing: 4

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: backendController.translate("الإصدار") + " " + (typeof appVersion !== 'undefined' ? appVersion : "1.0.0")
                font.pixelSize: 13
                font.bold: true
                color: accentColor
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: "Created by H.Z.Tun"
                font.pixelSize: 12
                color: secondaryTextColor
            }
        }
    }

    footer: DialogButtonBox {
        standardButtons: Dialog.Ok
        background: Rectangle {
            color: "transparent"
        }
    }

    onAccepted: close()
}
