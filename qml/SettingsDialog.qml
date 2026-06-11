import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

Dialog {
    id: root

    title: qsTr("إعدادات التطبيق")
    width: Math.min(parent ? parent.width : 800, 800)
    height: Math.min(parent ? parent.height : 720, 720)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    modal: true
    closePolicy: Dialog.CloseOnEscape

    // Reactive palette - updates when themeController.resolvedTheme changes
    property var _pal: Theme.resolvePalette(
        typeof themeController !== 'undefined' && themeController
            ? themeController.resolvedTheme : "light")

    // Color properties - updated when theme changes
    property color backgroundColor: _pal.background
    property color cardColor: _pal.surface
    property color textColor: _pal.text
    property color secondaryTextColor: _pal.textMuted
    property color accentColor: _pal.primary
    property color borderColor: _pal.border

    // Force _pal and colors update when themeController.resolvedTheme changes
    Connections {
        target: themeController
        function onResolvedThemeChanged(resolvedTheme) {
            _pal = Theme.resolvePalette(resolvedTheme)
            backgroundColor = _pal.background
            cardColor = _pal.surface
            textColor = _pal.text
            secondaryTextColor = _pal.textMuted
            accentColor = _pal.primary
            borderColor = _pal.border
        }
    }

    Connections {
        target: backendController
        function onLocationChanged() {
            locationTab.populate()
        }
    }

    property bool useCustomCoords: false
    property string searchText: ""
    property int currentTabIndex: 0
    property bool _populating: true

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
        color: "transparent"
        radius: 12
    }

    header: Rectangle {
        height: 48
        color: "transparent"
        radius: 12

        property point dragStart: Qt.point(0, 0)

        MouseArea {
            anchors.fill: parent
            onPressed: {
                dragStart = Qt.point(mouse.x, mouse.y)
            }
            onPositionChanged: {
                if (pressed) {
                    root.x += mouse.x - dragStart.x
                    root.y += mouse.y - dragStart.y
                }
            }
        }

        Label {
            anchors.centerIn: parent
            text: root.title
            color: textColor
            font.pixelSize: 16
            font.bold: true
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: borderColor
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
                    model: [
                        qsTr("الموقع"),
                        qsTr("الإزاحة"),
                        qsTr("المؤذنون"),
                        qsTr("الصوت"),
                        qsTr("الإشعارات"),
                        qsTr("الأذكار"),
                        qsTr("عام")
                    ]

                    delegate: Rectangle {
                        id: tabRect
                        implicitWidth: tabLabel.implicitWidth + 20
                        implicitHeight: 36
                        color: currentTabIndex === index ? accentColor : Qt.rgba(cardColor.r, cardColor.g, cardColor.b, 0.55)
                        radius: 6

                        Label {
                            id: tabLabel
                            anchors.centerIn: parent
                            text: modelData
                            color: currentTabIndex === index ? "#fff" : textColor
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
                            var s = backendController.getSettings()
                            useCustomCoords = s.custom_coords || false
                            _setCountryCombo(s.country)
                            _setCityCombo(s.country, s.city)
                            if (s.latitude) latField.text = String(s.latitude)
                            if (s.longitude) lonField.text = String(s.longitude)
                            methodCombo.model = backendController.getCalcMethods()
                            methodCombo.currentIndex = Math.max(0, methodCombo.find(s.method))
                            madhabCombo.model = backendController.getMadhabs()
                            madhabCombo.currentIndex = Math.max(0, madhabCombo.find(s.madhab))
                            _populating = false
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
                            cityCombo.model = backendController.getCitiesForCountry(countryCode)
                            if (cityCode) {
                                for (var i = 0; i < cityCombo.model.length; i++) {
                                    if (cityCombo.model[i].engName === cityCode) {
                                        cityCombo.currentIndex = i
                                        return
                                    }
                                }
                            }
                        }
                    }

                    function filterCountry(text) {
                        searchText = text
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

                    function onCountryChanged() {
                        var code = backendController.getSetting("country")
                        if (code) _setCountryCombo(code)
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
                                    label: Label { text: qsTr("تحديد الموقع تلقائياً"); color: textColor; font.bold: true; ToolTip.text: qsTr("تحديد موقعك الحالي عبر الإنترنت") }
                                    background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                    ColumnLayout { width: parent.width; spacing: 6
                                        Button {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 40
                                            text: qsTr("🌍 تحديد موقعي تلقائياً عبر الإنترنت")
                                            enabled: !useCustomCoords || true
                                            onClicked: {
                                                if (useCustomCoords) {
                                                    customCoordsCheck.checked = false
                                                }
                                                backendController.resetToAutoCoordinates()
                                            }
                                        }
                                    }
                                }

                                GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("الموقع"); color: textColor; font.bold: true }

                                background: Rectangle {
                                    color: cardColor
                                    radius: 8
                                    border.color: borderColor
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
                                            backendController.updateSetting("country", item.code)
                                            cityCombo.model = backendController.getCitiesForCountry(item.code)
                                            cityCombo.currentIndex = -1
                                        }
                                        onAccepted: {
                                            if (editText && currentIndex < 0)
                                                backendController.updateSetting("country", editText)
                                        }
                                    }

                    ComboBox {
                        id: cityCombo
                        Layout.fillWidth: true
                        editable: true
                        textRole: "name"
                        onCurrentIndexChanged: {
                            if (_populating || currentIndex < 0 || currentIndex >= model.length) return
                            var item = model[currentIndex]
                            backendController.updateSetting("city", item.engName)
                            if (item.lat) backendController.updateSetting("latitude", item.lat)
                            if (item.lon) backendController.updateSetting("longitude", item.lon)
                        }
                        onAccepted: {
                            if (editText && currentIndex < 0) {
                                var match = cityCombo.model.find(function(it) { return it.name === editText || it.engName === editText })
                                if (match >= 0) {
                                    var matchedItem = cityCombo.model[match]
                                    backendController.updateSetting("city", matchedItem.engName)
                                    if (matchedItem.lat) backendController.updateSetting("latitude", matchedItem.lat)
                                    if (matchedItem.lon) backendController.updateSetting("longitude", matchedItem.lon)
                                } else {
                                    backendController.updateSetting("city", editText)
                                }
                            }
                        }
                    }

                                    CheckBox {
                                        id: customCoordsCheck
                                        text: qsTr("🌐 استخدام إحداثيات مخصصة")
                                        checked: useCustomCoords
                                        onCheckedChanged: {
                                            if (_populating) return
                                            useCustomCoords = checked
                                            backendController.updateSetting("custom_coords", checked)
                                            if (!checked) {
                                                backendController.resetToAutoCoordinates()
                                                var s = backendController.getSettings()
                                                _setCountryCombo(s.country)
                                                _setCityCombo(s.country, s.city)
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
                                            placeholderText: qsTr("العرض (Latitude)")
                                            color: textColor
                                            placeholderTextColor: secondaryTextColor
                                            validator: DoubleValidator { bottom: -90; top: 90; decimals: 6 }
                                            background: Rectangle {
                                                color: backgroundColor; radius: 6
                                                border.color: borderColor; border.width: 1
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
                                            placeholderText: qsTr("الطول (Longitude)")
                                            color: textColor
                                            placeholderTextColor: secondaryTextColor
                                            validator: DoubleValidator { bottom: -180; top: 180; decimals: 6 }
                                            background: Rectangle {
                                                color: backgroundColor; radius: 6
                                                border.color: borderColor; border.width: 1
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
                                label: Label { text: qsTr("طريقة الحساب"); color: textColor; font.bold: true }
                                background: Rectangle {
                                    color: cardColor; radius: 8
                                    border.color: borderColor; border.width: 1
                                }
                                ColumnLayout {
                                    width: parent.width
                                    ComboBox {
                                        id: methodCombo
                                        Layout.fillWidth: true
                                        onCurrentIndexChanged: {
                                            if (_populating || currentIndex < 0 || !currentText) return
                                            backendController.updateSetting("method", currentText)
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("المذهب"); color: textColor; font.bold: true }
                                background: Rectangle {
                                    color: cardColor; radius: 8
                                    border.color: borderColor; border.width: 1
                                }
                                ColumnLayout {
                                    width: parent.width
                                    ComboBox {
                                        id: madhabCombo
                                        Layout.fillWidth: true
                                        onCurrentIndexChanged: {
                                            if (_populating || currentIndex < 0 || !currentText) return
                                            backendController.updateSetting("madhab", currentText)
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
                        var s = backendController.getSettings()
                        var o = s.offsets || {}
                        fajrSp.value = o.fajr || 0
                        sunriseSp.value = o.sunrise || 0
                        dhuhrSp.value = o.dhuhr || 0
                        asrSp.value = o.asr || 0
                        maghribSp.value = o.maghrib || 0
                        ishaSp.value = o.isha || 0
                        hijriSp.value = s.hijri_day_offset || 0
                        _populating = false
                    }

                    function resetOffsets() {
                        var keys = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
                        for (var i = 0; i < keys.length; i++) {
                            backendController.setOffset(keys[i], 0)
                        }
                        fajrSp.value = sunriseSp.value = dhuhrSp.value = 0
                        asrSp.value = maghribSp.value = ishaSp.value = 0
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("إزاحة أوقات الصلاة (دقائق)"); color: textColor }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: qsTr("الفجر"); color: textColor; Layout.fillWidth: true }
                                        SpinBox { id: fajrSp; from: -60; to: 60
                                            onValueChanged: backendController.setOffset("fajr", value) }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: qsTr("الشروق"); color: textColor; Layout.fillWidth: true }
                                        SpinBox { id: sunriseSp; from: -60; to: 60
                                            onValueChanged: backendController.setOffset("sunrise", value) }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: qsTr("الظهر"); color: textColor; Layout.fillWidth: true }
                                        SpinBox { id: dhuhrSp; from: -60; to: 60
                                            onValueChanged: backendController.setOffset("dhuhr", value) }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: qsTr("العصر"); color: textColor; Layout.fillWidth: true }
                                        SpinBox { id: asrSp; from: -60; to: 60
                                            onValueChanged: backendController.setOffset("asr", value) }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: qsTr("المغرب"); color: textColor; Layout.fillWidth: true }
                                        SpinBox { id: maghribSp; from: -60; to: 60
                                            onValueChanged: backendController.setOffset("maghrib", value) }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Label { text: qsTr("العشاء"); color: textColor; Layout.fillWidth: true }
                                        SpinBox { id: ishaSp; from: -60; to: 60
                                            onValueChanged: backendController.setOffset("isha", value) }
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36; Layout.topMargin: 4
                                        text: qsTr("🔄 إعادة تعيين جميع الإزاحات")
                                        onClicked: resetOffsets()
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("إزاحة التاريخ الهجري"); color: textColor }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    SpinBox {
                                        id: hijriSp; Layout.fillWidth: true; from: -5; to: 5
                                        onValueChanged: backendController.updateSetting("hijri_day_offset", value)
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
                        if (editIndex >= 0 && editIndex < muezzinsModel.count) {
                            muezzinsModel.set(editIndex, { name: name, path: path })
                        } else {
                            muezzinsModel.append({ name: name, path: path })
                        }
                        backendController.addMuezzin(name, path)
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
                        var newName = m.name + " (نسخة)"
                        var counter = 2
                        while (true) {
                            var exists = false
                            for (var i = 0; i < muezzinsModel.count; i++) {
                                if (muezzinsModel.get(i).name === newName) { exists = true; break }
                            }
                            if (!exists) break
                            newName = m.name + " (نسخة " + counter + ")"
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
                                            color: cardColor; radius: 8
                                            border.color: borderColor; border.width: 1

                                             RowLayout {
                                                 anchors.fill: parent; anchors.margins: 8; spacing: 6
                                                 ColumnLayout {
                                                     Layout.fillWidth: true; Layout.fillHeight: true; spacing: 2
                                                     Label { text: modelData.name; color: textColor; font.bold: true }
                                                     Label { text: modelData.path; color: secondaryTextColor; font.pixelSize: 11
                                                         elide: Text.ElideMiddle; Layout.fillWidth: true }
                                                 }
                                                  Button {
                                                      text: qsTr("🔊"); implicitWidth: 36; implicitHeight: 36
                                                       enabled: modelData && modelData.path !== ""
                                                      onClicked: muezzinsTab.previewMuezzin(index)
                                                  }
                                                 Button {
                                                     text: qsTr("⏹"); implicitWidth: 36; implicitHeight: 36
                                                     ToolTip.text: qsTr("إيقاف المعاينة")
                                                     onClicked: backendController.stopPreview()
                                                 }
                                                  Button {
                                                       text: modelData.path === muezzinsTab.defaultPath ? "⭐" : "☆"
                                                       implicitWidth: 36; implicitHeight: 36
                                                       ToolTip.text: modelData.path === muezzinsTab.defaultPath ? qsTr("المؤذن الافتراضي") : qsTr("تعيين كافتراضي")
                                                       onClicked: {
                                                           if (modelData.path) {
                                                               backendController.setDefaultMuezzin(modelData.path)
                                                               muezzinsTab.populate()
                                                           }
                                                       }
                                                   }
                                                  Button {
                                                      text: qsTr("📋"); implicitWidth: 36; implicitHeight: 36
                                                      ToolTip.text: qsTr("نسخ المؤذن")
                                                      onClicked: muezzinsTab.duplicateMuezzin(index)
                                                  }
                                                  Button {
                                                      text: qsTr("📁"); implicitWidth: 36; implicitHeight: 36
                                                      onClicked: browseMuezzinAudio(index)
                                                  }
                                                  Button {
                                                      text: qsTr("❌"); implicitWidth: 36; implicitHeight: 36
                                                      onClicked: removeMuezzin(index)
                                                  }
                                             }
                                        }
                                    }

                            Button {
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                text: qsTr("➕ إضافة مؤذن")
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
                        audioFilesModel.clear()
                        var list = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
                        for (var i = 0; i < list.length; i++) {
                            var p = backendController.getPrayerAudio(list[i])
                            audioFilesModel.append({ prayer: list[i], path: p || "" })
                        }
                        var s = backendController.getSettings()
                        volumeSp.value = s.volume || 1.0
                        fadeInCb.checked = s.fade_in !== false
                        fadeDurSp.value = s.fade_in_duration || 3
                        takbeerCb.checked = s.takbeer_only || false
                        _populating = false
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 6

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("ملفات الصوت لكل صلاة"); color: textColor; font.bold: true }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    Repeater {
                                        model: audioFilesModel
                                        delegate: RowLayout {
                                            required property var modelData
                                            required property int index
                                            Layout.fillWidth: true
                                            Label { 
                                                text: modelData && modelData.prayer ? qsTr(modelData.prayer) : ""
                                                color: textColor
                                                Layout.preferredWidth: 60
                                                font.bold: true
                                            }
                                            Label {
                                                text: modelData && modelData.path ? modelData.path : qsTr("(غير محدد)")
                                                color: modelData && modelData.path ? textColor : secondaryTextColor
                                                elide: Text.ElideMiddle; Layout.fillWidth: true
                                                font.pixelSize: 12
                                            }
                                            Button {
                                                text: qsTr("🔊"); implicitWidth: 36; implicitHeight: 36
                                                enabled: modelData && modelData.path !== ""
                                                onClicked: backendController.previewAudio(modelData.path)
                                            }
                                            Button {
                                                text: qsTr("⏹"); implicitWidth: 36; implicitHeight: 36
                                                ToolTip.text: qsTr("إيقاف المعاينة")
                                                onClicked: backendController.stopPreview()
                                            }
                                            Button {
                                                text: qsTr("📁"); implicitWidth: 36; implicitHeight: 36
                                                onClicked: browsePrayerAudio(modelData.prayer)
                                            }
                                        }
                                    }

                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36; Layout.topMargin: 4
                                        text: qsTr("🔊 اختبار الأذان الافتراضي")
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
                                label: Label { text: qsTr("الصوت العام"); color: textColor; font.bold: true; ToolTip.text: qsTr("إعدادات الصوت العامة للأذان") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: qsTr("مستوى الصوت:"); color: textColor; ToolTip.text: qsTr("ضبط مستوى صوت الأذان (0-100%)") }
                                        Slider {
                                            id: volumeSp; Layout.fillWidth: true; from: 0; to: 1; stepSize: 0.05
                                            onValueChanged: backendController.updateSetting("volume", value)
                                        }
                                        Label { text: Math.round(volumeSp.value * 100) + "%"; color: textColor; Layout.preferredWidth: 50 }
                                    }

                                    CheckBox {
                                        id: fadeInCb; text: qsTr("تلاشي الدخول (Fade In)")
                                        ToolTip.text: qsTr("يبدأ الأذان بصوت منخفض ويزداد تدريجياً")
                                        onCheckedChanged: backendController.updateSetting("fade_in", checked)
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true; visible: fadeInCb.checked
                                        Label { text: qsTr("مدة التلاشي (ثوانٍ):"); color: textColor; Layout.fillWidth: true; ToolTip.text: qsTr("مدة الزيادة التدريجية للصوت عند بداية الأذان") }
                                        SpinBox { id: fadeDurSp; from: 1; to: 10
                                            onValueChanged: backendController.updateSetting("fade_in_duration", value) }
                                    }

                                    CheckBox {
                                        id: takbeerCb; text: qsTr("تكبير فقط (بدون أذان كامل)")
                                        ToolTip.text: qsTr("يشغل التكبير فقط بدلاً من الأذان الكامل")
                                        onCheckedChanged: backendController.updateSetting("takbeer_only", checked)
                                    }

                                    Label {
                                        text: qsTr("ملاحظة: تفعيل \"تكبير فقط\" يشغل التكبير بدلاً من الأذان الكامل")
                                        color: secondaryTextColor; font.pixelSize: 11; wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("تفعيل الأذان لكل صلاة"); color: textColor; font.bold: true; ToolTip.text: qsTr("تفعيل/إيقاف الأذان لكل صلاة على حدة") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4

                                    Repeater {
                                        model: ["fajr", "dhuhr", "asr", "maghrib", "isha"]
                                        delegate: CheckBox {
                                            text: qsTr(modelData)
                                            checked: backendController.getNestedSetting("azan_enabled." + modelData) !== false
                                            ToolTip.text: qsTr("تفعيل الأذان لصلاة ") + qsTr(modelData)
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
                        var s = backendController.getSettings()
                        preAzanCb.checked = s.pre_azan_enabled !== false
                        preAzanSp.value = s.pre_azan_minutes || 10
                        dndCb.checked = s.dnd_enabled || false
                        dndFromSp.value = s.dnd_from || 22
                        dndToSp.value = s.dnd_to || 6
                        dndDurSp.value = s.dnd_duration || 20
                        silentCb.checked = s.silent_mode || false
                        _populating = false
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("الأذان المبكر"); color: textColor; font.bold: true; ToolTip.text: qsTr("إعدادات التنبيه المبكر قبل الأذان") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    CheckBox { id: preAzanCb; text: qsTr("تفعيل التنبيه المبكر")
                                        ToolTip.text: qsTr("تفعيل التنبيه المبكر قبل الأذان بالدقائق المحددة")
                                        onCheckedChanged: backendController.updateSetting("pre_azan_enabled", checked) }
                                    RowLayout {
                                        Layout.leftMargin: 20; visible: preAzanCb.checked
                                        Label { text: qsTr("دقائق قبل الأذان:"); color: textColor; ToolTip.text: qsTr("عدد الدقائق قبل الأذان للتنبيه المبكر") }
                                        SpinBox { id: preAzanSp; from: 1; to: 60
                                            onValueChanged: backendController.updateSetting("pre_azan_minutes", value) }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("عدم الإزعاج (DND)"); color: textColor; font.bold: true; ToolTip.text: qsTr("إيقاف الإشعارات النظامية في أوقات محددة") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 4
                                    CheckBox { id: dndCb; text: qsTr("تفعيل DND")
                                        ToolTip.text: qsTr("إيقاف إشعارات النظام خلال فترة DND")
                                        onCheckedChanged: backendController.updateSetting("dnd_enabled", checked) }
                                    RowLayout {
                                        Layout.leftMargin: 20; visible: dndCb.checked
                                        Label { text: qsTr("من الساعة:"); color: textColor; ToolTip.text: qsTr("ساعة بداية فترة DND") }
                                        SpinBox { id: dndFromSp; from: 0; to: 23
                                            onValueChanged: backendController.updateSetting("dnd_from", value) }
                                        Label { text: qsTr("إلى الساعة:"); color: textColor; ToolTip.text: qsTr("ساعة نهاية فترة DND") }
                                        SpinBox { id: dndToSp; from: 0; to: 23
                                            onValueChanged: backendController.updateSetting("dnd_to", value) }
                                    }
                                    RowLayout {
                                        Layout.leftMargin: 20; visible: dndCb.checked
                                        Label { text: qsTr("مدة بعد الصلاة (دقيقة):"); color: textColor; ToolTip.text: qsTr("مدة تفعيل DND بعد كل صلاة") }
                                        SpinBox { id: dndDurSp; from: 5; to: 120
                                            onValueChanged: backendController.updateSetting("dnd_duration", value) }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("الوضع الصامت"); color: textColor; font.bold: true; ToolTip.text: qsTr("كتم جميع الأصوات والتنبيهات") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: silentCb; text: qsTr("الوضع الصامت")
                                        ToolTip.text: qsTr("كتم جميع أصوات الأذان والإشعارات")
                                        onCheckedChanged: backendController.updateSetting("silent_mode", checked) }
                                }
                            }

                        }
                    }
                }

                Item {
                    id: athkarTab
                    function populate() {
                        _populating = true
                        var s = backendController.getSettings()
                        athkarCountSp.value = s.athkarCount || 33
                        var m = s.athkarMethod || "after_prayer"
                        var opts = ["after_prayer", "specific_time", "both"]
                        var idx = opts.indexOf(m)
                        athkarMethodCb.currentIndex = idx >= 0 ? idx : 0
                        popupEnabledCb.checked = s.athkar_popup_enabled !== false
                        popupDurSp.value = s.athkar_popup_duration || 300
                        popupDelaySp.value = s.athkar_popup_delay || 600
                        _populating = false
                    }

                    ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("الأذكار"); color: textColor; font.bold: true; ToolTip.text: qsTr("إعدادات الأذكار بعد الصلاة") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: qsTr("عدد مرات التكرار:"); color: textColor; ToolTip.text: qsTr("عدد مرات تكرار كل ذكر") }
                                        SpinBox { id: athkarCountSp; from: 1; to: 99
                                            onValueChanged: backendController.updateSetting("athkarCount", value) }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: qsTr("طريقة العرض:"); color: textColor; ToolTip.text: qsTr("متى تظهر الأذكار: بعد كل صلاة، في وقت محدد، أو كلاهما") }
                                        ComboBox {
                                            id: athkarMethodCb; Layout.fillWidth: true
                                            model: [qsTr("بعد الصلاة"), qsTr("وقت محدد"), qsTr("كلاهما")]
                                            onCurrentIndexChanged: {
                                                var opts = ["after_prayer", "specific_time", "both"]
                                                if (currentIndex >= 0) backendController.updateSetting("athkarMethod", opts[currentIndex])
                                            }
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("النافذة المنبثقة للأذكار"); color: textColor; font.bold: true; ToolTip.text: qsTr("إعدادات النافذة المنبثقة التي تظهر الأذكار") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6
                                    CheckBox { id: popupEnabledCb; text: qsTr("تفعيل النافذة المنبثقة")
                                        ToolTip.text: qsTr("عرض نافذة منبثقة بالأذكار بعد كل صلاة")
                                        onCheckedChanged: backendController.updateSetting("athkar_popup_enabled", checked) }
                                    RowLayout {
                                        Layout.fillWidth: true; visible: popupEnabledCb.checked
                                        Label { text: qsTr("مدة العرض (ثوانٍ):"); color: textColor; ToolTip.text: qsTr("مدة بقاء النافذة المنبثقة ظاهرة قبل الإغلاق التلقائي") }
                                        SpinBox { id: popupDurSp; from: 5; to: 600
                                            onValueChanged: backendController.updateSetting("athkar_popup_duration", value) }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true; visible: popupEnabledCb.checked
                                        Label { text: qsTr("تأخير الظهور (ثوانٍ):"); color: textColor; ToolTip.text: qsTr("تأخير ظهور النافذة بعد انتهاء الصلاة") }
                                        SpinBox { id: popupDelaySp; from: 0; to: 300
                                            onValueChanged: backendController.updateSetting("athkar_popup_delay", value) }
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36; Layout.topMargin: 4; visible: popupEnabledCb.checked
                                        text: qsTr("🧪 اختبار النافذة المنبثقة")
                                        onClicked: {
                                            var provider = prayerEngine ? prayerEngine.getAthkarProvider() : null
                                            if (provider) {
                                                provider.setPrayerAthkar("fajr", qsTr("اختبار الأذكار"))
                                                prayerEngine.athkarShown("fajr", qsTr("اختبار الأذكار"), 5000, qsTr("هذا اختبار للنافذة المنبثقة للأذكار"), true)
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
                                var s = backendController.getSettings()
                                langCombo.model = backendController.getLanguages()
                                var langIdx = -1
                                for (var i = 0; i < langCombo.model.length; i++) {
                                    if (langCombo.model[i].code === s.language) {
                                        langIdx = i
                                        break
                                    }
                                }
                                langCombo.currentIndex = langIdx >= 0 ? langIdx : 0
                                var theme = s.theme || "dark"
                                var themeModel = backendController.getThemes()
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
                                autostartCb.checked = s.autostart || false
                                sleepModeCbGeneral.checked = s.sleep_mode !== false
                                backgroundEnabledCb.checked = s.background_enabled !== false
                                _populating = false
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
                            importDialog.nameFilters = [qsTr("ملفات JSON (*.json)")]
                            importDialog.open()
                        }

                        ScrollView {
                        anchors.fill: parent; clip: true; contentWidth: availableWidth

                        ColumnLayout { width: parent.width; spacing: 8

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("اللغة"); color: textColor; font.bold: true; ToolTip.text: qsTr("اختيار لغة واجهة التطبيق") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                    ComboBox { id: langCombo; Layout.fillWidth: true
                        model: backendController.getLanguages()
                        textRole: "name"
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                var langCode = model[currentIndex].code
                                backendController.updateSetting("language", langCode)
                            }
                        }
                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("المظهر"); color: textColor; font.bold: true; ToolTip.text: qsTr("اختيار سمة ألوان التطبيق") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    ComboBox { id: themeCombo; Layout.fillWidth: true
                                        model: backendController.getThemes()
                                        textRole: "name"
                                        onActivated: {
                                            if (index >= 0 && index < model.length) {
                                                var themeCode = model[index].code
                                                if (themeController) themeController.setTheme(themeCode)
                                                backendController.updateSetting("theme", themeCode)
                                            }
                                        }
                                    }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("بدء التشغيل التلقائي"); color: textColor; font.bold: true; ToolTip.text: qsTr("تشغيل التطبيق تلقائياً عند بدء تشغيل النظام") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: autostartCb; text: qsTr("تشغيل التطبيق تلقائياً عند بدء النظام")
                                        ToolTip.text: qsTr("إضافة التطبيق لبرامج بدء التشغيل")
                                        onCheckedChanged: backendController.setAutostart(checked) }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("وضع النوم"); color: textColor; font.bold: true; ToolTip.text: qsTr("إعدادات وضع النوم عند الإغلاق") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: sleepModeCbGeneral; text: qsTr("العمل في الخلفية عند الإغلاق (Sleep Mode)")
                                        ToolTip.text: qsTr("إبقاء التطبيق يعمل في علبة النظام عند إغلاق النافذة")
                                        onCheckedChanged: backendController.updateSetting("sleep_mode", checked) }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("صورة الخلفية"); color: textColor; font.bold: true; ToolTip.text: qsTr("تفعيل أو تعطيل صورة الخلفية في الواجهة الرئيسية") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    CheckBox { id: backgroundEnabledCb; text: qsTr("إظهار صورة الخلفية")
                                        ToolTip.text: qsTr("تفعيل/تعطيل صورة المسجد النبوي في الخلفية")
                                        onCheckedChanged: backendController.updateSetting("background_enabled", checked) }
                                }
                            }

                            GroupBox {
                                Layout.fillWidth: true
                                label: Label { text: qsTr("المنطقة الزمنية"); color: textColor; font.bold: true; ToolTip.text: qsTr("اختيار المنطقة الزمنية لحساب مواقيت الصلاة") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width
                                    ComboBox { id: timezoneCombo; Layout.fillWidth: true
                                        model: backendController.getTimezones()
                                        textRole: "name"
                                        valueRole: "code"
                                        ToolTip.text: qsTr("اختيار المنطقة الزمنية لحساب مواقيت الصلاة بدقة")
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
                                label: Label { text: qsTr("إدارة الإعدادات"); color: textColor; font.bold: true; ToolTip.text: qsTr("استيراد/تصدير/إعادة تعيين الإعدادات") }
                                background: Rectangle { color: cardColor; radius: 8; border.color: borderColor; border.width: 1 }
                                ColumnLayout { width: parent.width; spacing: 6
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36
                                        text: qsTr("📤 تصدير الإعدادات")
                                        onClicked: exportSettings()
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36
                                        text: qsTr("📥 استيراد الإعدادات")
                                        onClicked: importSettings()
                                    }
                                    Button {
                                        Layout.fillWidth: true; Layout.preferredHeight: 36
                                        text: qsTr("🔄 إعادة تعيين للإعدادات الافتراضية")
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
        color: cardColor
        radius: 12

        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 8

            Item { Layout.fillWidth: true }

            Button {
                text: qsTr("💾 حفظ")
                Layout.preferredHeight: 36
                onClicked: {
                    backendController.commitSettings()
                    root.close()
                }
            }

            Button {
                text: qsTr("❌ إلغاء")
                Layout.preferredHeight: 36
                onClicked: root.close()
            }
        }
    }

    Dialog {
        id: resetConfirmDlg
        title: qsTr("🔄 إعادة تعيين")
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        anchors.centerIn: parent
        Label { text: qsTr("هل أنت متأكد من إعادة تعيين جميع الإعدادات؟"); color: _pal.text }
        onAccepted: {
            backendController.resetAllSettings()
            populate()
        }
    }

    FileDialog {
        id: importDialog
        title: qsTr("اختر ملف إعدادات")
        nameFilters: [qsTr("ملفات JSON (*.json)")]
        fileMode: FileDialog.OpenFile
        property var _callback: null
        onAccepted: {
            if (_callback) { _callback(Qt.urlToLocalFile(selectedFile)); _callback = null }
        }
        onRejected: _callback = null
    }

    onVisibleChanged: {
        if (visible) {
            _populating = true
            backendController.storeSettingsSnapshot()
            locationTab.populate()
            offsetsTab.populate()
            muezzinsTab.populate()
            audioTab.populate()
            notificationsTab.populate()
            athkarTab.populate()
            generalTab.populate()
            _populating = false
        }
    }
}
