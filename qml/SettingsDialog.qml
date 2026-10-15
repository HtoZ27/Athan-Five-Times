import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs as NativeDialogs
import Theme 1.0

Dialog {
    id: root

    title: tr("إعدادات التطبيق")
    width: Math.min(parent ? parent.width : 800, 800)
    height: Math.min(parent ? parent.height : 720, 720)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    modal: true
    closePolicy: Dialog.CloseOnEscape

    ThemeColors { id: theme }

    Connections {
        target: backendController
        function onLocationChanged() {
            locationTab.populate()
        }
        function onAutoLocationStatus(status) {
            detectingLocation = (status === "detecting")
            if (status === "detecting")
                locationStatusText = tr("جارٍ تحديد الموقع…")
            else if (status === "success")
                locationStatusText = tr("تم تحديد الموقع بنجاح")
            else if (status === "failed")
                locationStatusText = tr("تعذّر تحديد الموقع — تحقق من الاتصال بالإنترنت")
            else
                locationStatusText = ""
        }
    }

    property bool useCustomCoords: false
    property bool detectingLocation: false
    property string locationStatusText: ""
    property string searchText: ""
    property int currentTabIndex: 0
    property string _currentCountryCode: ""
    property bool _populating: true
    property bool _saving: false
    property var _tabLoaded: [false, false, false, false, false, false, false]

    onClosed: {
        if (!_saving) backendController.restoreSettingsSnapshot()
    }

    onCurrentTabIndexChanged: {
        if (_populating) return
        _ensureTabLoaded(currentTabIndex)
    }

    function _ensureTabLoaded(idx) {
        if (idx < 0 || idx > 6) return
        if (_tabLoaded[idx]) return
        _tabLoaded[idx] = true
        var tabs = [locationTab, offsetsTab, muezzinsTab, audioTab, notificationsTab, athkarTab, generalTab]
        tabs[idx].populate()
    }
    property var _pendingOffsets: ({})
    property Timer _offsetDebounce: Timer {
        interval: 300
        onTriggered: {
            var po = _pendingOffsets
            _pendingOffsets = ({})
            for (var k in po) backendController.setOffset(k, po[k])
        }
    }
    property Timer _filterTimer: Timer {
        interval: 150
        onTriggered: {
            var text = searchText
            var all = backendController.getCountryList()
            if (!text || text === "") {
                countryCombo.model = all
                return
            }
            var filtered = []
            for (var i = 0; i < all.length; i++) {
                var item = all[i]
                if (item.name && item.name.toLowerCase().indexOf(text.toLowerCase()) >= 0)
                    filtered.push(item)
            }
            countryCombo.model = filtered
        }
    }

    property var _tabNames: [
        tr("الموقع"),
        tr("الإزاحة"),
        tr("المؤذنون"),
        tr("الصوت"),
        tr("الإشعارات"),
        tr("الأذكار"),
        tr("عام")
    ]

    function tr(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translate(key)
    }

    function trPrayer(key) {
        if (typeof l10n === "undefined" || l10n === null
                || typeof backendController === "undefined" || backendController === null)
            return key
        var _ = l10n.currentLanguage
        return backendController.translatePrayer(key)
    }

    function retranslate() {
        root.title = tr("إعدادات التطبيق")
        _tabNames = [
            tr("الموقع"),
            tr("الإزاحة"),
            tr("المؤذنون"),
            tr("الصوت"),
            tr("الإشعارات"),
            tr("الأذكار"),
            tr("عام")
        ]
        saveBtn.text = tr("حفظ")
        cancelBtn.text = tr("إلغاء")
        resetConfirmDlg.title = tr("إعادة تعيين")
        if (resetConfirmDlgLabel) resetConfirmDlgLabel.text = tr("هل أنت متأكد من إعادة تعيين جميع الإعدادات؟")
        importDialog.title = tr("اختر ملف إعدادات")
        importDialog.nameFilters = [tr("ملفات JSON (*.json)")]
        _populating = true
        _tabLoaded = [false, false, false, false, false, false, false]
        _tabLoaded[0] = true
        locationTab.populate()
        _tabLoaded[6] = true
        generalTab.populate()
        _populating = false
    }

    Connections {
        target: l10n
        function onLanguageChanged() { retranslate() }
    }

    Component.onCompleted: {
        _populating = true
    }

    function browseMuezzinAudio(editIndex) {
        var path = backendController.openAudioFileDialog()
        if (path)
            muezzinsTab.addMuezzin(path, editIndex)
    }

    function browsePrayerAudio(prayerKey) {
        if (!prayerKey) return
        var path = backendController.openAudioFileDialog()
        if (path) {
            backendController.setPrayerAudio(prayerKey, path)
            audioTab.populate()
        }
    }

    background: Rectangle {
        color: theme.bgColor
        radius: 12
    }

    header: Rectangle {
        height: 48
        color: "transparent"
        radius: 12

        property point pressGlobal: Qt.point(0, 0)
        property point dlgPos: Qt.point(0, 0)

        MouseArea {
            anchors.fill: parent
            onPressed: {
                pressGlobal = mapToGlobal(mouse.x, mouse.y)
                dlgPos = Qt.point(root.x, root.y)
            }
            onPositionChanged: {
                if (pressed) {
                    var g = mapToGlobal(mouse.x, mouse.y)
                    root.x = dlgPos.x + g.x - pressGlobal.x
                    root.y = dlgPos.y + g.y - pressGlobal.y
                }
            }
        }

        Label {
            anchors.centerIn: parent
            text: root.title
            color: theme.textColor
            font.pixelSize: 16
            font.bold: true
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: theme.borderColor
        }
    }

    contentItem: Rectangle {
        color: "transparent"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 6

            RowLayout {
                id: tabBar
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                spacing: 2

                Item { Layout.fillWidth: true }

                Repeater {
                    id: tabRepeater
                    model: _tabNames

                    delegate: Rectangle {
                        id: tabRect
                        required property var modelData
                        required property int index
                        implicitWidth: tabLabel.implicitWidth + 20
                        implicitHeight: 36
                        color: currentTabIndex === index ? theme.accentColor : Qt.rgba(theme.cardColor.r, theme.cardColor.g, theme.cardColor.b, 0.55)
                        radius: 6

                        Label {
                            id: tabLabel
                            anchors.centerIn: parent
                            text: modelData
                            color: currentTabIndex === index ? "#fff" : theme.textColor
                            font.pixelSize: 12
                            font.bold: currentTabIndex === index
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: currentTabIndex = index
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }

            StackLayout {
                id: stack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: currentTabIndex

                    Item {
                        id: locationTab
                        function populate() {
                            _populating = true
                            try {
                                var s = backendController.getSettings()
                                useCustomCoords = s.custom_coords || false
                                _setCountryCombo(s.country)
                                _setCityCombo(s.country, s.city)
                                if (s.latitude) latField.text = String(s.latitude)
                                if (s.longitude) lonField.text = String(s.longitude)
                                methodCombo.model = backendController.getCalcMethods()
                                methodCombo.currentIndex = _findMethodIndex(s.method)
                                madhabCombo.model = backendController.getMadhabs()
                                madhabCombo.currentIndex = _findMadhabIndex(s.madhab)
                            } finally {
                                _populating = false
                            }
                        }

                    function _findMethodIndex(key) {
                        if (!key || !methodCombo.model) return 0
                        for (var i = 0; i < methodCombo.model.length; i++) {
                            if (methodCombo.model[i].key === key) return i
                        }
                        return 0
                    }

                    function _findMadhabIndex(key) {
                        if (!key || !madhabCombo.model) return 0
                        for (var i = 0; i < madhabCombo.model.length; i++) {
                            if (madhabCombo.model[i].key === key) return i
                        }
                        return 0
                    }

                    function _setCountryCombo(code) {
                        countryCombo.model = backendController.getCountryList()
                        if (code && code !== "none") {
                            for (var i = 0; i < countryCombo.model.length; i++) {
                                if (countryCombo.model[i].code === code) {
                                    countryCombo.currentIndex = i
                                    return
                                }
                            }
                        }
                    }

                    function _setCityCombo(countryCode, cityCode) {
                        if (countryCode && countryCode !== "none") {
                            _currentCountryCode = countryCode
                            cityPicker.setCity(cityCode)
                        }
                    }

                    function filterCountry(text) {
                        searchText = text
                        _filterTimer.restart()
                    }

                    function onCountryChanged() {
                        var code = backendController.getSetting("country")
                        if (code) {
                            _currentCountryCode = code
                            _setCountryCombo(code)
                        }
                    }

                    ScrollView {
                        anchors.fill: parent
                        clip: true
                        contentWidth: availableWidth

                            ColumnLayout {
                                width: parent.width
                                spacing: 6

                                GroupBox {
                                    Layout.fillWidth: true
                                    label: Label { text: tr("تحديد الموقع تلقائياً"); color: theme.textColor; font.bold: true; ToolTip.text: tr("تحديد موقعك الحالي عبر الإنترنت") }
                                    background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                    ColumnLayout { width: parent.width; spacing: 6
                                        Button {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 40
                                            text: tr("تحديد موقعي تلقائياً عبر الإنترنت")
                                            enabled: !useCustomCoords && !detectingLocation
                                            onClicked: {
                                                if (useCustomCoords) {
                                                    customCoordsCheck.checked = false
                                                }
                                                backendController.resetToAutoCoordinates()
                                            }
                                        }
                                        Label {
                                            visible: locationStatusText !== ""
                                            text: locationStatusText
                                            color: theme.textColor
                                            font.italic: true
                                            wrapMode: Text.Wrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                }

                                GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("الموقع"); color: theme.textColor; font.bold: true }

                                background: Rectangle {
                                    color: theme.cardColor
                                    radius: 8
                                    border.color: theme.borderColor
                                    border.width: 1
                                }

                                ColumnLayout {
                                    width: parent.width
                                    spacing: 6

                                    ComboBox {
                                        id: countryCombo
                                        Layout.fillWidth: true
                                        editable: true
                                        textRole: "name"

                                        onCurrentIndexChanged: {
                                            if (_populating || currentIndex < 0 || currentIndex >= model.length) return
                                            var item = model[currentIndex]
                                            _currentCountryCode = item.code
                                            backendController.updateSetting("country", item.code)
                                            var defaultMethod = backendController.getDefaultMethod(item.code)
                                            if (defaultMethod) {
                                                methodCombo.currentIndex = _findMethodIndex(defaultMethod)
                                            }
                                        }
                                        onAccepted: {
                                            if (editText && currentIndex < 0) {
                                                var q = editText.toLowerCase()
                                                var hit = -1
                                                for (var i = 0; i < model.length; i++) {
                                                    var it = model[i]
                                                    if (it.code === editText
                                                            || (it.name && it.name.toLowerCase() === q)) {
                                                        hit = i
                                                        break
                                                    }
                                                }
                                                if (hit >= 0) {
                                                    currentIndex = hit
                                                } else {
                                                    _setCountryCombo(backendController.getSetting("country"))
                                                }
                                            }
                                        }
                                    }

                                    VirtualCityPicker {
                                        id: cityPicker
                                        countryCode: _currentCountryCode
                                        onCitySelected: function(engName, displayName) {
                                            if (_populating) return
                                            backendController.updateSetting("city", engName)
                                            var coords = backendController.getCityCoords(_currentCountryCode, engName)
                                            if (coords && coords.lat) backendController.updateSetting("latitude", coords.lat)
                                            if (coords && coords.lon) backendController.updateSetting("longitude", coords.lon)
                                        }
                                        onAccepted: function(text) {
                                            if (_populating) return
                                            backendController.updateSetting("city", text)
                                        }
                                    }

                                    CheckBox {
                                        id: customCoordsCheck
                                        text: tr("استخدام إحداثيات مخصصة")
                                        checked: useCustomCoords
                                        onCheckedChanged: {
                                            if (_populating) return
                                            useCustomCoords = checked
                                            backendController.updateSetting("custom_coords", checked)
                                            if (!checked) {
                                                backendController.resetToAutoCoordinates()
                                                var s = backendController.getSettings()
                                                _currentCountryCode = s.country
                                                _setCountryCombo(s.country)
                                                cityPicker.setCity(s.city)
                                                if (s.latitude) latField.text = String(s.latitude)
                                                if (s.longitude) lonField.text = String(s.longitude)
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        visible: customCoordsCheck.checked

                                        TextField {
                                            id: latField
                                            Layout.fillWidth: true
                                            placeholderText: tr("العرض (Latitude)")
                                            color: theme.textColor
                                            placeholderTextColor: theme.textMutedColor
                                            validator: DoubleValidator { bottom: -90; top: 90; decimals: 6 }
                                            background: Rectangle {
                                                color: theme.bgColor; radius: 6
                                                border.color: theme.borderColor; border.width: 1
                                            }
                                            onEditingFinished: {
                                                var v = parseFloat(text)
                                                if (!isNaN(v)) {
                                                    backendController.updateSetting("latitude", v)
                                                    backendController.updateSetting("custom_coords", true)
                                                }
                                            }
                                        }
                                        TextField {
                                            id: lonField
                                            Layout.fillWidth: true
                                            placeholderText: tr("الطول (Longitude)")
                                            color: theme.textColor
                                            placeholderTextColor: theme.textMutedColor
                                            validator: DoubleValidator { bottom: -180; top: 180; decimals: 6 }
                                            background: Rectangle {
                                                color: theme.bgColor; radius: 6
                                                border.color: theme.borderColor; border.width: 1
                                            }
                                            onEditingFinished: {
                                                var v = parseFloat(text)
                                                if (!isNaN(v)) {
                                                    backendController.updateSetting("longitude", v)
                                                    backendController.updateSetting("custom_coords", true)
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("طريقة الحساب"); color: theme.textColor; font.bold: true }
                                background: Rectangle {
                                    color: theme.cardColor; radius: 8
                                    border.color: theme.borderColor; border.width: 1
                                }
                                ColumnLayout {
                                    width: parent.width
                                    ComboBox {
                                        id: methodCombo
                                        Layout.fillWidth: true
                                        textRole: "display"
                                        onCurrentIndexChanged: {
                                            if (_populating || currentIndex < 0 || currentIndex >= model.length) return
                                            backendController.updateSetting("method", model[currentIndex].key)
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("المذهب"); color: theme.textColor; font.bold: true }
                                background: Rectangle {
                                    color: theme.cardColor; radius: 8
                                    border.color: theme.borderColor; border.width: 1
                                }
                                ColumnLayout {
                                    width: parent.width
                                    ComboBox {
                                        id: madhabCombo
                                        Layout.fillWidth: true
                                        textRole: "display"
                                        onCurrentIndexChanged: {
                                            if (_populating || currentIndex < 0 || currentIndex >= model.length) return
                                            backendController.updateSetting("madhab", model[currentIndex].key)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: offsetsTab
                    function populate() {
                        _populating = true
                        try {
                            var s = backendController.getSettings()
                            var o = s.offsets || {}
                            fajrSp.value = o.fajr !== undefined ? o.fajr : 0
                            sunriseSp.value = o.sunrise !== undefined ? o.sunrise : 0
                            dhuhrSp.value = o.dhuhr !== undefined ? o.dhuhr : 0
                            asrSp.value = o.asr !== undefined ? o.asr : 0
                            maghribSp.value = o.maghrib !== undefined ? o.maghrib : 0
                            ishaSp.value = o.isha !== undefined ? o.isha : 0
                            hijriSp.value = s.hijri_day_offset !== undefined ? s.hijri_day_offset : 0
                        } finally {
                            _populating = false
                        }
                    }

                    function resetOffsets() {
                        var keys = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
                        for (var i = 0; i < keys.length; i++)
                            _pendingOffsets[keys[i]] = 0
                        _offsetDebounce.restart()
                        fajrSp.value = sunriseSp.value = dhuhrSp.value = 0
                        asrSp.value = maghribSp.value = ishaSp.value = 0
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("إزاحة أوقات الصلاة (دقائق)"); color: theme.textColor }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: tr("الفجر"); color: theme.textColor; Layout.fillWidth: true }
                                        SpinBox { id: fajrSp; from: -60; to: 60
                                            onValueChanged: { if (_populating) return; _pendingOffsets["fajr"] = value; _offsetDebounce.restart() } }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: tr("الشروق"); color: theme.textColor; Layout.fillWidth: true }
                                        SpinBox { id: sunriseSp; from: -60; to: 60
                                            onValueChanged: { if (_populating) return; _pendingOffsets["sunrise"] = value; _offsetDebounce.restart() } }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: tr("الظهر"); color: theme.textColor; Layout.fillWidth: true }
                                        SpinBox { id: dhuhrSp; from: -60; to: 60
                                            onValueChanged: { if (_populating) return; _pendingOffsets["dhuhr"] = value; _offsetDebounce.restart() } }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: tr("العصر"); color: theme.textColor; Layout.fillWidth: true }
                                        SpinBox { id: asrSp; from: -60; to: 60
                                            onValueChanged: { if (_populating) return; _pendingOffsets["asr"] = value; _offsetDebounce.restart() } }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: tr("المغرب"); color: theme.textColor; Layout.fillWidth: true }
                                        SpinBox { id: maghribSp; from: -60; to: 60
                                            onValueChanged: { if (_populating) return; _pendingOffsets["maghrib"] = value; _offsetDebounce.restart() } }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: tr("العشاء"); color: theme.textColor; Layout.fillWidth: true }
                                        SpinBox { id: ishaSp; from: -60; to: 60
                                            onValueChanged: { if (_populating) return; _pendingOffsets["isha"] = value; _offsetDebounce.restart() } }
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36; Layout.topMargin: 4
                                        text: tr("إعادة تعيين جميع الإزاحات")
                                        onClicked: resetOffsets()
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("إزاحة التاريخ الهجري"); color: theme.textColor }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    SpinBox {
                                        id: hijriSp; Layout.fillWidth: true; from: -5; to: 5
                                        onValueChanged: { if (_populating) return; backendController.updateSetting("hijri_day_offset", value) }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: muezzinsTab
                    ListModel { id: muezzinsModel }

                    property string defaultPath: ""

                    function populate() {
                        muezzinsModel.clear()
                        defaultPath = backendController.getNestedSetting("audio.default") || ""
                        var list = backendController.getMuezzins()
                        for (var i = 0; i < list.length; i++) {
                            var item = list[i]
                            muezzinsModel.append({ name: item.name, path: item.path })
                        }
                    }

                    function addMuezzin(fileUrl, editIndex) {
                        var path = String(fileUrl).replace("file://", "")
                        var name = path.split("/").pop().split(".")[0]
                        var oldName = ""
                        if (editIndex >= 0 && editIndex < muezzinsModel.count) {
                            var old = muezzinsModel.get(editIndex)
                            if (old) oldName = old.name
                            muezzinsModel.set(editIndex, { name: name, path: path })
                        } else {
                            muezzinsModel.append({ name: name, path: path })
                        }
                        backendController.addMuezzin(name, path)
                        if (oldName && oldName !== name) backendController.removeMuezzin(oldName)
                    }

                    function previewMuezzin(idx) {
                        var m = muezzinsModel.get(idx)
                        if (m && m.path) backendController.previewAudio(m.path)
                    }

                    function removeMuezzin(idx) {
                        var m = muezzinsModel.get(idx)
                        if (m) { muezzinsModel.remove(idx); backendController.removeMuezzin(m.name) }
                    }

                    function duplicateMuezzin(idx) {
                        var m = muezzinsModel.get(idx)
                        if (!m) return
                        var newName = m.name + tr(" (نسخة)")
                        var counter = 2
                        while (counter < 1000) {
                            var exists = false
                            for (var i = 0; i < muezzinsModel.count; i++) {
                                if (muezzinsModel.get(i).name === newName) { exists = true; break }
                            }
                            if (!exists) break
                            newName = m.name + tr(" (نسخة)") + " " + counter
                            counter++
                        }
                        muezzinsModel.append({ name: newName, path: m.path })
                        backendController.addMuezzin(newName, m.path)
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 6

                                    Repeater {
                                        model: muezzinsModel
                                        delegate: Rectangle {
                                            required property var modelData
                                            required property int index
                                            Layout.fillWidth: true; Layout.preferredHeight: 56
                                            color: theme.cardColor; radius: 8
                                            border.color: theme.borderColor; border.width: 1

                                             RowLayout {
                                                 anchors.fill: parent; anchors.margins: 8; spacing: 6
                                                 ColumnLayout {
                                                     Layout.fillWidth: true; Layout.fillHeight: true; spacing: 2
                                                     Label { text: modelData.name; color: theme.textColor; font.bold: true }
                                                     Label { text: modelData.path; color: theme.textMutedColor; font.pixelSize: 11
                                                         elide: Text.ElideMiddle; Layout.fillWidth: true }
                                                 }
                                                  Button {
                                                      text: tr("🔊"); implicitWidth: 36; implicitHeight: 36
                                                       enabled: modelData && modelData.path !== ""
                                                      onClicked: muezzinsTab.previewMuezzin(index)
                                                  }
                                                 Button {
                                                     text: tr("⏹"); implicitWidth: 36; implicitHeight: 36
                                                     ToolTip.text: tr("إيقاف المعاينة")
                                                     onClicked: backendController.stopPreview()
                                                 }
                                                  Button {
                                                       text: modelData.path === muezzinsTab.defaultPath ? "⭐" : "☆"
                                                       implicitWidth: 36; implicitHeight: 36
                                                       ToolTip.text: modelData.path === muezzinsTab.defaultPath ? tr("المؤذن الافتراضي") : tr("تعيين كافتراضي")
                                                       onClicked: {
                                                           if (modelData.path) {
                                                               backendController.setDefaultMuezzin(modelData.path)
                                                               muezzinsTab.populate()
                                                           }
                                                       }
                                                   }
                                                  Button {
                                                      text: tr("📋"); implicitWidth: 36; implicitHeight: 36
                                                      ToolTip.text: tr("نسخ المؤذن")
                                                      onClicked: muezzinsTab.duplicateMuezzin(index)
                                                  }
                                                  Button {
                                                      text: tr("📁"); implicitWidth: 36; implicitHeight: 36
                                                      onClicked: browseMuezzinAudio(index)
                                                  }
                                                  Button {
                                                      text: tr("❌"); implicitWidth: 36; implicitHeight: 36
                                                      onClicked: removeMuezzin(index)
                                                  }
                                             }
                                        }
                                    }

                            Button {
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                text: tr("إضافة مؤذن")
                                onClicked: browseMuezzinAudio(-1)
                            }
                        }
                    }
                }

                Item {
                    id: audioTab
                    ListModel { id: audioFilesModel }

                    function populate() {
                        _populating = true
                        try {
                            audioFilesModel.clear()
                            var list = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
                            for (var i = 0; i < list.length; i++) {
                                var p = backendController.getPrayerAudio(list[i])
                                audioFilesModel.append({ prayer: list[i], path: p || "" })
                            }
                            var s = backendController.getSettings()
                            volumeSp.value = s.volume !== undefined ? s.volume : 1.0
                            fadeInCb.checked = s.fade_in !== false
                            fadeDurSp.value = s.fade_in_duration !== undefined ? s.fade_in_duration : 3
                            takbeerCb.checked = s.takbeer_only || false
                        } finally {
                            _populating = false
                        }
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 6

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("ملفات الصوت لكل صلاة"); color: theme.textColor; font.bold: true }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    Repeater {
                                        model: audioFilesModel
                                        delegate: RowLayout {
                                            required property var modelData
                                            required property int index
                                            Layout.fillWidth: true
                                            Label { 
                                                text: modelData && modelData.prayer ? trPrayer(modelData.prayer) : ""
                                                color: theme.textColor
                                                Layout.preferredWidth: 60
                                                font.bold: true
                                            }
                                            Label {
                                                text: modelData && modelData.path ? modelData.path : tr("(غير محدد)")
                                                color: modelData && modelData.path ? theme.textColor : theme.textMutedColor
                                                elide: Text.ElideMiddle; Layout.fillWidth: true
                                                font.pixelSize: 12
                                            }
                                            Button {
                                                text: tr("🔊"); implicitWidth: 36; implicitHeight: 36
                                                enabled: modelData && modelData.path !== ""
                                                onClicked: backendController.previewAudio(modelData.path)
                                            }
                                            Button {
                                                text: tr("⏹"); implicitWidth: 36; implicitHeight: 36
                                                ToolTip.text: tr("إيقاف المعاينة")
                                                onClicked: backendController.stopPreview()
                                            }
                                            Button {
                                                text: tr("📁"); implicitWidth: 36; implicitHeight: 36
                                                onClicked: browsePrayerAudio(modelData.prayer)
                                            }
                                        }
                                    }

                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36; Layout.topMargin: 4
                                        text: tr("اختبار الأذان الافتراضي")
                                        onClicked: {
                                            var s = backendController.getSettings()
                                            var path = s.audio?.default || s.muezzins?.["افتراضي"] || ""
                                            if (path) backendController.previewAudio(path)
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("الصوت العام"); color: theme.textColor; font.bold: true; ToolTip.text: tr("إعدادات الصوت العامة للأذان") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: tr("مستوى الصوت:"); color: theme.textColor; ToolTip.text: tr("ضبط مستوى صوت الأذان (0-100%)") }
                                        Slider {
                                            id: volumeSp; Layout.fillWidth: true; from: 0; to: 1; stepSize: 0.05
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("volume", value) }
                                        }
                                        Label { text: Math.round(volumeSp.value * 100) + "%"; color: theme.textColor; Layout.preferredWidth: 50 }
                                    }

                                    CheckBox {
                                        id: fadeInCb; text: tr("تلاشي الدخول (Fade In)")
                                        ToolTip.text: tr("يبدأ الأذان بصوت منخفض ويزداد تدريجياً")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("fade_in", checked) }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true; visible: fadeInCb.checked
                                        Label { text: tr("مدة التلاشي (ثوانٍ):"); color: theme.textColor; Layout.fillWidth: true; ToolTip.text: tr("مدة الزيادة التدريجية للصوت عند بداية الأذان") }
                                        SpinBox { id: fadeDurSp; from: 1; to: 10
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("fade_in_duration", value) } }
                                    }

                                    CheckBox {
                                        id: takbeerCb; text: tr("تكبير فقط (بدون أذان كامل)")
                                        ToolTip.text: tr("يشغل التكبير فقط بدلاً من الأذان الكامل")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("takbeer_only", checked) }
                                    }

                                    Label {
                                        text: tr("ملاحظة: تفعيل \"تكبير فقط\" يشغل التكبير بدلاً من الأذان الكامل")
                                        color: theme.textMutedColor; font.pixelSize: 11; wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("تفعيل الأذان لكل صلاة"); color: theme.textColor; font.bold: true; ToolTip.text: tr("تفعيل/إيقاف الأذان لكل صلاة على حدة") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4

                                    Repeater {
                                        model: ["fajr", "dhuhr", "asr", "maghrib", "isha"]
                                        delegate: CheckBox {
                                            text: trPrayer(modelData)
                                            checked: backendController ? backendController.getNestedSetting("azan_enabled." + modelData) !== false : true
                                            ToolTip.text: tr("تفعيل الأذان لصلاة ") + trPrayer(modelData)
                                            onCheckedChanged: backendController.updateSetting("azan_enabled." + modelData, checked)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: notificationsTab
                    function populate() {
                        _populating = true
                        try {
                            var s = backendController.getSettings()
                            preAzanCb.checked = s.pre_azan_enabled !== false
                            preAzanSp.value = s.pre_azan_minutes !== undefined ? s.pre_azan_minutes : 10
                            dndCb.checked = s.dnd_enabled !== undefined ? s.dnd_enabled : false
                            dndFromSp.value = s.dnd_from !== undefined ? s.dnd_from : 22
                            dndToSp.value = s.dnd_to !== undefined ? s.dnd_to : 6
                            dndDurSp.value = s.dnd_duration !== undefined ? s.dnd_duration : 20
                            silentCb.checked = s.silent_mode || false
                            showTrayCb.checked = s.show_tray !== undefined ? s.show_tray : true
                        } finally {
                            _populating = false
                        }
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("الأذان المبكر"); color: theme.textColor; font.bold: true; ToolTip.text: tr("إعدادات التنبيه المبكر قبل الأذان") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    CheckBox { id: preAzanCb; text: tr("تفعيل التنبيه المبكر")
                                        ToolTip.text: tr("تفعيل التنبيه المبكر قبل الأذان بالدقائق المحددة")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("pre_azan_enabled", checked) } }
                                    RowLayout {
                                        Layout.leftMargin: 20; visible: preAzanCb.checked
                                        Label { text: tr("دقائق قبل الأذان:"); color: theme.textColor; ToolTip.text: tr("عدد الدقائق قبل الأذان للتنبيه المبكر") }
                                        SpinBox { id: preAzanSp; from: 1; to: 60
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("pre_azan_minutes", value) } }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("عدم الإزعاج (DND)"); color: theme.textColor; font.bold: true; ToolTip.text: tr("إيقاف الإشعارات النظامية في أوقات محددة") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    CheckBox { id: dndCb; text: tr("تفعيل DND")
                                        ToolTip.text: tr("إيقاف إشعارات النظام خلال فترة DND")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("dnd_enabled", checked) } }
                                    RowLayout {
                                        Layout.leftMargin: 20; visible: dndCb.checked
                                        Label { text: tr("من الساعة:"); color: theme.textColor; ToolTip.text: tr("ساعة بداية فترة DND") }
                                        SpinBox { id: dndFromSp; from: 0; to: 23
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("dnd_from", value) } }
                                        Label { text: tr("إلى الساعة:"); color: theme.textColor; ToolTip.text: tr("ساعة نهاية فترة DND") }
                                        SpinBox { id: dndToSp; from: 0; to: 23
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("dnd_to", value) } }
                                    }
                                    RowLayout {
                                        Layout.leftMargin: 20; visible: dndCb.checked
                                        Label { text: tr("مدة بعد الصلاة (دقيقة):"); color: theme.textColor; ToolTip.text: tr("مدة تفعيل DND بعد كل صلاة") }
                                        SpinBox { id: dndDurSp; from: 5; to: 120
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("dnd_duration", value) } }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("الوضع الصامت"); color: theme.textColor; font.bold: true; ToolTip.text: tr("كتم جميع الأصوات والتنبيهات") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: silentCb; text: tr("الوضع الصامت")
                                        ToolTip.text: tr("كتم جميع أصوات الأذان والإشعارات")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("silent_mode", checked) } }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("شريط النظام"); color: theme.textColor; font.bold: true; ToolTip.text: tr("إعدادات أيقونة شريط النظام") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: showTrayCb; text: tr("إظهار أيقونة شريط النظام")
                                        ToolTip.text: tr("إظهار أو إخفاء أيقونة التطبيق في شريط النظام")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("show_tray", checked) } }
                                }
                            }

                        }
                    }
                }

                Item {
                    id: athkarTab
                    function populate() {
                        _populating = true
                        try {
                            var s = backendController.getSettings()
                            athkarCountSp.value = s.athkarCount !== undefined ? s.athkarCount : 33
                            var m = s.athkarMethod || "after_prayer"
                            var opts = ["after_prayer", "specific_time", "both"]
                            var idx = opts.indexOf(m)
                            athkarMethodCb.currentIndex = idx >= 0 ? idx : 0
                            popupEnabledCb.checked = s.athkar_popup_enabled !== false
                            popupDurSp.value = s.athkar_popup_duration !== undefined ? s.athkar_popup_duration : 300
                            popupDelaySp.value = s.athkar_popup_delay !== undefined ? s.athkar_popup_delay : 60
                        } finally {
                            _populating = false
                        }
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("الأذكار"); color: theme.textColor; font.bold: true; ToolTip.text: tr("إعدادات الأذكار بعد الصلاة") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: tr("عدد مرات التكرار:"); color: theme.textColor; ToolTip.text: tr("عدد مرات تكرار كل ذكر") }
                                        SpinBox { id: athkarCountSp; from: 1; to: 99
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("athkarCount", value) } }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: tr("طريقة العرض:"); color: theme.textColor; ToolTip.text: tr("متى تظهر الأذكار: بعد كل صلاة، في وقت محدد، أو كلاهما") }
                                        ComboBox {
                                            id: athkarMethodCb; Layout.fillWidth: true
                                            model: [tr("بعد الصلاة"), tr("وقت محدد"), tr("كلاهما")]
                                            onCurrentIndexChanged: {
                                                if (_populating) return
                                                var opts = ["after_prayer", "specific_time", "both"]
                                                if (currentIndex >= 0) backendController.updateSetting("athkarMethod", opts[currentIndex])
                                            }
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("النافذة المنبثقة للأذكار"); color: theme.textColor; font.bold: true; ToolTip.text: tr("إعدادات النافذة المنبثقة التي تظهر الأذكار") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6
                                    CheckBox { id: popupEnabledCb; text: tr("تفعيل النافذة المنبثقة")
                                        ToolTip.text: tr("عرض نافذة منبثقة بالأذكار بعد كل صلاة")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("athkar_popup_enabled", checked) } }
                                    RowLayout {
                                        Layout.fillWidth: true; visible: popupEnabledCb.checked
                                        Label { text: tr("مدة العرض (ثوانٍ):"); color: theme.textColor; ToolTip.text: tr("مدة بقاء النافذة المنبثقة ظاهرة قبل الإغلاق التلقائي") }
                                        SpinBox { id: popupDurSp; from: 5; to: 600
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("athkar_popup_duration", value) } }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true; visible: popupEnabledCb.checked
                                        Label { text: tr("تأخير الظهور (ثوانٍ):"); color: theme.textColor; ToolTip.text: tr("تأخير ظهور النافذة بعد انتهاء الصلاة") }
                                        SpinBox { id: popupDelaySp; from: 0; to: 300
                                            onValueChanged: { if (_populating) return; backendController.updateSetting("athkar_popup_delay", value) } }
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36; Layout.topMargin: 4; visible: popupEnabledCb.checked
                                        text: tr("اختبار النافذة المنبثقة")
                                        onClicked: {
                                            var provider = prayerEngine ? prayerEngine.getAthkarProvider() : null
                                            if (provider) {
                                                provider.setPrayerAthkar("fajr", tr("اختبار الأذكار"))
                                                prayerEngine.athkarShown("fajr", tr("اختبار الأذكار"), 5000, tr("هذا اختبار للنافذة المنبثقة للأذكار"), true)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                    Item {
                        id: generalTab
                            function populate() {
                                _populating = true
                                try {
                                    var s = backendController.getSettings()
                                    langCombo.model = l10n ? l10n.languages : []
                                    var langIdx = -1
                                    for (var i = 0; i < langCombo.model.length; i++) {
                                        if (langCombo.model[i].code === (l10n ? l10n.currentLanguage : s.language)) {
                                            langIdx = i
                                            break
                                        }
                                    }
                                    langCombo.currentIndex = langIdx >= 0 ? langIdx : 0
                                    var theme = s.theme || "dark"
                                    var themeModel = backendController.getThemes()
                                    themeCombo.model = themeModel
                                    var themeIdx = -1
                                    for (var i = 0; i < themeModel.length; i++) {
                                        if (themeModel[i].code === theme) {
                                            themeIdx = i
                                            break
                                        }
                                    }
                                    themeCombo.currentIndex = themeIdx >= 0 ? themeIdx : 0
                                    timezoneCombo.model = backendController.getTimezones()
                                    var tzIdx = -1
                                    for (var i = 0; i < timezoneCombo.model.length; i++) {
                                        if (timezoneCombo.model[i].code === s.timezone) {
                                            tzIdx = i
                                            break
                                        }
                                    }
                                    timezoneCombo.currentIndex = tzIdx >= 0 ? tzIdx : 0
                                    var rbCodes = ["auto", "opengl", "software"]
                                    var rbIdx = rbCodes.indexOf(s.render_backend)
                                    renderBackendCb.currentIndex = rbIdx >= 0 ? rbIdx : 0
                                    var rlCodes = ["auto", "threaded", "basic"]
                                    var rlIdx = rlCodes.indexOf(s.render_loop)
                                    renderLoopCb.currentIndex = rlIdx >= 0 ? rlIdx : 0
                                    autostartCb.checked = s.autostart || false
                                    sleepModeCbGeneral.checked = s.sleep_mode !== false
                                    backgroundEnabledCb.checked = s.background_enabled !== false
                                } finally {
                                    _populating = false
                                }
                            }

                        function resetAllSettings() {
                            resetConfirmDlg.open()
                        }

                        function exportSettings() {
                            backendController.exportSettings()
                        }

                        function importSettings() {
                            importDialog._callback = function(fileUrl) {
                                var path = String(fileUrl).replace("file://", "")
                                backendController.importSettings(path)
                                populate()
                            }
                            importDialog.nameFilters = [tr("ملفات JSON (*.json)")]
                            importDialog.open()
                        }

                        ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("اللغة"); color: theme.textColor; font.bold: true; ToolTip.text: tr("اختيار لغة واجهة التطبيق") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                    ComboBox { id: langCombo; Layout.fillWidth: true
                        model: l10n ? l10n.languages : []
                        textRole: "name"
                        onCurrentIndexChanged: {
                            if (_populating) return
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                var langCode = model[currentIndex].code
                                l10n.setLanguage(langCode)
                                backendController.updateSetting("language", langCode)
                            }
                        }
                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("المظهر"); color: theme.textColor; font.bold: true; ToolTip.text: tr("اختيار سمة ألوان التطبيق") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    ComboBox { id: themeCombo; Layout.fillWidth: true
                                        model: backendController ? backendController.getThemes() : []
                                        textRole: "name"
                                        onActivated: {
                                            if (index >= 0 && index < model.length) {
                                                var themeCode = model[index].code
                                                if (themeController) themeController.setTheme(themeCode)
                                            }
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("العرض"); color: theme.textColor; font.bold: true; ToolTip.text: tr("اختيار محرك العرض") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    Label { text: tr("محرك العرض:"); color: theme.textColor }
                                    ComboBox { id: renderBackendCb; Layout.fillWidth: true
                                        model: [tr("تلقائي"), "OpenGL", tr("برمجي")]
                                        onActivated: {
                                            var codes = ["auto", "opengl", "software"]
                                            if (index >= 0 && index < 3)
                                                backendController.updateSetting("render_backend", codes[index])
                                        }
                                    }
                                    Label { text: tr("حلقة العرض:"); color: theme.textColor }
                                    ComboBox { id: renderLoopCb; Layout.fillWidth: true
                                        model: [tr("تلقائي"), "threaded", "basic"]
                                        onActivated: {
                                            var codes = ["auto", "threaded", "basic"]
                                            if (index >= 0 && index < 3)
                                                backendController.updateSetting("render_loop", codes[index])
                                        }
                                    }
                                    Label { text: tr("تغيير العرض يتطلب إعادة تشغيل التطبيق"); color: theme.textMutedColor; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("بدء التشغيل التلقائي"); color: theme.textColor; font.bold: true; ToolTip.text: tr("تشغيل التطبيق تلقائياً عند بدء تشغيل النظام") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: autostartCb; text: tr("تشغيل التطبيق تلقائياً عند بدء النظام")
                                        ToolTip.text: tr("إضافة التطبيق لبرامج بدء التشغيل")
                                        onCheckedChanged: { if (_populating) return; backendController.setAutostart(checked) } }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("وضع النوم"); color: theme.textColor; font.bold: true; ToolTip.text: tr("تقليل نشاط التطبيق في الخلفية") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: sleepModeCbGeneral; text: tr("وضع السكون (فحص أقل في الخلفية)")
                                        ToolTip.text: tr("تقليل تكرار فحص الأوقات لتوفير البطارية والمعالج")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("sleep_mode", checked) } }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("صورة الخلفية"); color: theme.textColor; font.bold: true; ToolTip.text: tr("تفعيل أو تعطيل صورة الخلفية في الواجهة الرئيسية") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: backgroundEnabledCb; text: tr("إظهار صورة الخلفية")
                                        ToolTip.text: tr("تفعيل/تعطيل صورة المسجد النبوي في الخلفية")
                                        onCheckedChanged: { if (_populating) return; backendController.updateSetting("background_enabled", checked) } }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("المنطقة الزمنية"); color: theme.textColor; font.bold: true; ToolTip.text: tr("اختيار المنطقة الزمنية لحساب مواقيت الصلاة") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    ComboBox { id: timezoneCombo; Layout.fillWidth: true
                                        model: backendController ? backendController.getTimezones() : []
                                        textRole: "name"
                                        valueRole: "code"
                                        ToolTip.text: tr("اختيار المنطقة الزمنية لحساب مواقيت الصلاة بدقة")
                                        onCurrentIndexChanged: {
                                            if (_populating || currentIndex < 0 || currentIndex >= model.length) return
                                            var tz = model[currentIndex]
                                            backendController.updateSetting("timezone", tz.code)
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: tr("إدارة الإعدادات"); color: theme.textColor; font.bold: true; ToolTip.text: tr("استيراد/تصدير/إعادة تعيين الإعدادات") }
                                background: Rectangle { color: theme.cardColor; radius: 8; border.color: theme.borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36
                                        text: tr("تصدير الإعدادات")
                                        onClicked: exportSettings()
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36
                                        text: tr("استيراد الإعدادات")
                                        onClicked: importSettings()
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36
                                        text: tr("إعادة تعيين للإعدادات الافتراضية")
                                        onClicked: resetAllSettings()
                                    }
                                }
                            }

                        }
                    }
                }
            }
        }
    }

    footer: Rectangle {
        height: 52
        color: theme.cardColor
        radius: 12

        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 8

            Item { Layout.fillWidth: true }

            Button {
                id: saveBtn
                text: tr("حفظ")
                Layout.preferredHeight: 36
                onClicked: {
                    _saving = true
                    backendController.commitSettings()
                    root.close()
                }
            }

            Button {
                id: cancelBtn
                text: tr("إلغاء")
                Layout.preferredHeight: 36
                onClicked: root.close()
            }
        }
    }

    Dialog {
        id: resetConfirmDlg
        title: tr("إعادة تعيين")
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        width: 420
        implicitWidth: 420
        implicitHeight: 160
        x: Math.round((parent ? parent.width : 800) / 2 - width / 2)
        y: Math.round((parent ? parent.height : 720) / 2 - height / 2)
        Label {
            id: resetConfirmDlgLabel
            width: 380
            text: tr("هل أنت متأكد من إعادة تعيين جميع الإعدادات؟")
            color: theme.textColor
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }
        onAccepted: {
            backendController.resetAllSettings()
            backendController.storeSettingsSnapshot()
            _tabLoaded = [true, true, true, true, true, true, true]
            locationTab.populate()
            offsetsTab.populate()
            muezzinsTab.populate()
            audioTab.populate()
            notificationsTab.populate()
            athkarTab.populate()
            generalTab.populate()
        }
    }

    NativeDialogs.FileDialog {
        id: importDialog
        title: tr("اختر ملف إعدادات")
        nameFilters: [tr("ملفات JSON (*.json)")]
        fileMode: NativeDialogs.FileDialog.OpenFile
        property var _callback: null
        onAccepted: {
            if (_callback) { _callback(selectedFile); _callback = null }
        }
        onRejected: _callback = null
    }

    onVisibleChanged: {
        if (visible) {
            _saving = false
            _populating = true
            _tabLoaded = [false, false, false, false, false, false, false]
            backendController.storeSettingsSnapshot()
            _tabLoaded[0] = true
            locationTab.populate()
            _populating = false
        }
    }
}
