import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Item {
    id: root

    objectName: "cityPicker"

    property string countryCode: ""
    property string selectedEngName: ""
    property string selectedDisplayName: ""
    property bool _populating: false
    property bool _settingCity: false
    property var _allCities: []
    property int _searchOffset: 0

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }
    property int _searchTotal: 0
    property string _pendingQuery: ""
    property bool _searching: false
    property bool _hasMore: false
    readonly property int _pageSize: 50

    signal citySelected(string engName, string displayName)
    signal accepted(string text)

    ThemeColors { id: theme }

    // Arrow side follows LayoutMirroring; padding must follow it too
    // (Qt mirrors anchors but not padding).
    property bool isRtl: l10n ? l10n.isRtl : true
    property string languageCode: l10n ? l10n.currentLanguage : ""

    onLanguageCodeChanged: reloadCities()

    function reloadCities() {
        if (!countryCode || countryCode === "none")
            return
        if (typeof backendController === "undefined" || backendController === null)
            return
        _allCities = backendController.getCityNamesForCountry(countryCode)
        _applyFilter("")
        setCity(selectedEngName)
    }

    implicitHeight: 40
    Layout.fillWidth: true

    onCountryCodeChanged: {
        if (_settingCity) return
        _allCities = []
        listViewModel.clear()
        searchField.text = ""
        _searchOffset = 0
        _searchTotal = 0
        _hasMore = false
        _pendingQuery = ""
        if (!countryCode || countryCode === "none") return
        _allCities = backendController.getCityNamesForCountry(countryCode)
        _applyFilter("")
    }

    Timer {
        id: _searchDebounce
        interval: 200
        onTriggered: _doSearch()
    }

    function _doSearch() {
        if (!countryCode || countryCode === "none") return
        var q = _pendingQuery
        _searching = true
        var result = backendController.searchCitiesPaginated(countryCode, q, 0, _pageSize)
        _searchOffset = result.offset + result.limit
        _searchTotal = result.total
        _hasMore = _searchOffset < _searchTotal
        if (q === _pendingQuery) {
            listViewModel.clear()
            for (var i = 0; i < result.items.length; i++)
                listViewModel.append(result.items[i])
            _searching = false
        }
    }

    function _loadMore() {
        if (_searching || !_hasMore || !countryCode) return
        _searching = true
        var result = backendController.searchCitiesPaginated(
            countryCode, _pendingQuery, _searchOffset, _pageSize)
        _searchOffset = result.offset + result.limit
        _hasMore = _searchOffset < _searchTotal
        if (!_pendingQuery || _pendingQuery === searchField.text) {
            for (var i = 0; i < result.items.length; i++)
                listViewModel.append(result.items[i])
            _searching = false
        }
    }

    function setCity(engName) {
        _settingCity = true
        if (engName && _allCities) {
            for (var i = 0; i < _allCities.length; i++) {
                if (_allCities[i].engName === engName) {
                    selectedEngName = engName
                    selectedDisplayName = _allCities[i].name
                    searchField.text = _allCities[i].name
                    _settingCity = false
                    return
                }
            }
        }
        searchField.text = engName || ""
        selectedEngName = engName || ""
        selectedDisplayName = engName || ""
        _settingCity = false
    }

    function _applyFilter(text) {
        if (!text || text === "") {
            listViewModel.clear()
            for (var i = 0; i < _allCities.length; i++)
                listViewModel.append(_allCities[i])
            _hasMore = false
            if (popup.opened)
                listView.currentIndex = listViewModel.count > 0 ? 0 : -1
            return
        }
        _pendingQuery = text
        _searchDebounce.restart()
    }

    ListModel { id: listViewModel }

    ThemedTextField {
        id: searchField
        objectName: "citySearchField"
        anchors.fill: parent
        font.pixelSize: 13
        rightPadding: isRtl ? 10 : 30
        leftPadding: isRtl ? 30 : 10

        Keys.onDownPressed: {
            if (!popup.opened && countryCode) {
                popup.open()
                listView.currentIndex = listViewModel.count > 0 ? 0 : -1
            } else if (popup.opened && _hasMore && listView.currentIndex >= listViewModel.count - 3) {
                _loadMore()
            } else if (popup.opened) {
                listView.incrementCurrentIndex()
            }
        }
        Keys.onUpPressed: {
            if (popup.opened) listView.decrementCurrentIndex()
        }
        Keys.onReturnPressed: {
            if (popup.opened && listViewModel.count > 0) {
                var idx = listView.currentIndex < 0 ? 0 : listView.currentIndex
                var sel = listViewModel.get(idx)
                if (sel)
                    _selectCity(sel.engName, sel.name)
            } else if (text) {
                var q = text.toLowerCase()
                var hit = null
                for (var i = 0; i < _allCities.length; i++) {
                    var c = _allCities[i]
                    if (c.engName === text || (c.name && c.name.toLowerCase() === q)) {
                        hit = c
                        break
                    }
                }
                if (hit) {
                    _selectCity(hit.engName, hit.name)
                } else {
                    searchField.text = selectedDisplayName
                    if (popup.opened) popup.close()
                }
            }
        }
        Keys.onEscapePressed: popup.close()

        onTextChanged: {
            if (_populating || _settingCity) return
            if (!countryCode || countryCode === "none") return
            _applyFilter(text)
            if (text.length > 0 && !popup.opened)
                popup.open()
            else if (text.length === 0 && popup.opened)
                listView.positionViewAtBeginning()
        }

        onActiveFocusChanged: {
            if (activeFocus && countryCode && countryCode !== "none" && !popup.opened && listViewModel.count > 0)
                popup.open()
        }
    }

    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: 8
        width: 20
        height: 20
        radius: 4
        color: popup.opened ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.2) : "transparent"

        Text {
            anchors.centerIn: parent
            text: popup.opened ? "▲" : "▼"
            font.pixelSize: 10
            color: theme.textMutedColor
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (!countryCode || countryCode === "none") return
                if (popup.opened) popup.close()
                else popup.open()
            }
        }
    }

    Popup {
        id: popup
        objectName: "cityPopup"
        // Flip above the field when the space below cannot fit a short list.
        y: {
            var win = root.Window.window
            if (!win)
                return root.height + 4
            var top = root.mapToItem(null, 0, 0).y
            var below = win.height - (top + root.height) - 8
            return below >= Math.min(height, 120) ? root.height + 4
                                                    : -height - 4
        }
        width: parent.width
        // Never collapse to a 12px strip: empty state still needs a row.
        height: Math.max(56, Math.min(300, listView.contentHeight + 12))
        padding: 6
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        onOpened: listView.currentIndex = listViewModel.count > 0 ? 0 : -1

        background: Rectangle {
            color: theme.cardColor
            radius: 8
            border.color: theme.borderColor
            border.width: 1
        }

        ListView {
            id: listView
            objectName: "cityListView"
            anchors.fill: parent
            clip: true
            spacing: 2
            model: listViewModel
            currentIndex: -1
            ScrollIndicator.vertical: ScrollIndicator { }
            boundsBehavior: Flickable.StopAtBounds

            onMovementEnded: {
                if (atYEnd && _hasMore && !_searching)
                    _loadMore()
            }

            delegate: Rectangle {
                required property var modelData
                required property int index
                width: listView.width
                height: 34
                color: index === listView.currentIndex
                    ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.25)
                    : (mouse.containsMouse ? Qt.rgba(theme.accentColor.r, theme.accentColor.g, theme.accentColor.b, 0.12) : "transparent")
                radius: 4

                Label {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    text: modelData ? modelData.name : ""
                    color: index === listView.currentIndex ? theme.accentColor : theme.textColor
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 13
                    font.bold: index === listView.currentIndex
                    elide: Text.ElideRight
                }

                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (modelData)
                            _selectCity(modelData.engName, modelData.name)
                    }
                }
            }

            footer: _hasMore && !_searching ? loadMoreButton : null

            Component {
                id: loadMoreButton
                Rectangle {
                    width: listView.width
                    height: 36
                    color: "transparent"
                    ThemedButton {
                        anchors.centerIn: parent
                        text: tr("عرض المزيد") + " (" + (_searchTotal - _searchOffset) + ")"
                        compact: true
                        onClicked: _loadMore()
                        font.pixelSize: 12
                    }
                }
            }
        }

        Label {
            objectName: "cityEmptyLabel"
            anchors.centerIn: parent
            visible: listViewModel.count === 0
            text: tr("لا توجد مدن مطابقة")
            color: theme.textMutedColor
            font.pixelSize: 13
        }

        onClosed: {
            if (searchField.activeFocus)
                searchField.focus = false
        }
    }

    function _selectCity(engName, displayName) {
        selectedEngName = engName
        selectedDisplayName = displayName
        searchField.text = displayName
        citySelected(engName, displayName)
        popup.close()
    }
}
