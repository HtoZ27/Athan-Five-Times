import QtQuick
import QtQuick.Controls

ComboBox {
    id: control

    ThemeColors { id: theme }

    implicitHeight: 34
    implicitWidth: 160
    font.pixelSize: 13

    background: Rectangle {
        color: theme.bgColor
        radius: 6
        border.color: control.activeFocus ? theme.accentColor : theme.borderColor
        border.width: 1
    }

    contentItem: TextInput {
        leftPadding: control.mirrored ? 28 : 10
        rightPadding: control.mirrored ? 10 : 28
        text: control.editable ? control.editText : control.displayText
        font: control.font
        color: control.enabled ? theme.textColor : theme.textMutedColor
        selectionColor: theme.accentColor
        selectedTextColor: "#ffffff"
        verticalAlignment: Text.AlignVCenter
        enabled: control.editable
        autoScroll: control.editable
        readOnly: control.down
        inputMethodHints: control.inputMethodHints
        validator: control.validator
        selectByMouse: control.selectTextByMouse
        onTextEdited: control.editText = text
    }

    indicator: Text {
        x: control.mirrored ? 9 : control.width - width - 9
        y: control.topPadding + (control.availableHeight - height) / 2
        text: "▾"
        color: theme.textMutedColor
        font.pixelSize: 12
    }

    delegate: ItemDelegate {
        id: item

        required property var modelData
        required property int index

        width: control.width - 8
        highlighted: control.highlightedIndex === index
        hoverEnabled: true

        contentItem: Text {
            text: control.textRole !== "" && modelData && typeof modelData === "object"
                ? modelData[control.textRole]
                : String(modelData)
            color: item.highlighted ? theme.accentColor : theme.textColor
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            leftPadding: 10
            rightPadding: 10
        }

        background: Rectangle {
            radius: 4
            color: item.highlighted
                ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.22)
                : item.hovered
                    ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.1)
                    : "transparent"
        }
    }

    popup: Popup {
        y: control.height + 2
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 320)
        padding: 4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: theme.cardColor
            radius: 8
            border.color: theme.borderColor
            border.width: 1
        }

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollIndicator.vertical: ScrollIndicator { }
        }
    }
}
