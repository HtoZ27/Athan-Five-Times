import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Dialog {
    id: root
    title: tr("عن البرنامج")

    width: Math.min(460, parent ? parent.width * 0.95 : 460)
    height: Math.min(560, parent ? parent.height * 0.9 : 560)
    modal: true

    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    ThemeColors { id: theme }

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function retranslate() {
        root.title = tr("عن البرنامج")
        appNameLabel.text = tr("أذان الصلاة")
        appDescLabel.text = tr("تطبيق مفتوح المصدر لأوقات الصلاة والأذان")
        libsLabel.text = tr("المكتبات المستخدمة")
        versionLabel.text = tr("الإصدار") + " " + (typeof appVersion !== 'undefined' ? appVersion : "1.0.0")
    }

    Connections {
        target: l10n
        function onLanguageChanged() { retranslate() }
    }

    background: Rectangle {
        color: theme.bgColor
        radius: 16
        border.color: theme.borderColor
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
                Layout.preferredWidth: 72
                Layout.preferredHeight: 72
                radius: 36
                color: theme.accentColor

                Image {
                    anchors.centerIn: parent
                    width: 44
                    height: 44
                    source: "../assets/kaaba.svg"
                    fillMode: Image.PreserveAspectFit
                }
            }

            Label {
                id: appNameLabel
                Layout.alignment: Qt.AlignHCenter
                text: tr("أذان الصلاة")
                font.pixelSize: 22
                font.bold: true
                color: theme.textColor
            }

            Label {
                id: appDescLabel
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                text: tr("تطبيق مفتوح المصدر لأوقات الصلاة والأذان")
                font.pixelSize: 13
                color: theme.textMutedColor
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
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
            Layout.preferredHeight: 1
            color: theme.borderColor
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
                    id: libsLabel
                    Layout.fillWidth: true
                    text: tr("المكتبات المستخدمة")
                    font.pixelSize: 14
                    font.bold: true
                    color: theme.accentColor
                }

                Text {
                    Layout.fillWidth: true
                    text: prayerEngine ? prayerEngine.getCreditsHtml() : ""
                    textFormat: Text.RichText
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                    color: theme.textColor
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
            Layout.preferredHeight: 1
            color: theme.borderColor
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: 12
            Layout.bottomMargin: 4
            spacing: 4

            Label {
                id: versionLabel
                Layout.alignment: Qt.AlignHCenter
                text: tr("الإصدار") + " " + (typeof appVersion !== 'undefined' ? appVersion : "1.0.0")
                font.pixelSize: 13
                font.bold: true
                color: theme.accentColor
            }

            Label {
                Layout.alignment: Qt.AlignHCenter
                text: tr("تطوير") + ": H.Z.Tun"
                font.pixelSize: 12
                color: theme.textMutedColor
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
