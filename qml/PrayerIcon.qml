import QtQuick

Item {
    id: root
    property string prayerKey: "fajr"
    property bool active: false
    property int iconSize: 32

    width: iconSize
    height: iconSize
    clip: false
    Accessible.name: prayerKey

    function _key() {
        var k = (prayerKey || "fajr").toLowerCase()
        if (k !== "fajr" && k !== "sunrise" && k !== "dhuhr"
                && k !== "asr" && k !== "maghrib" && k !== "isha"
                && k !== "imsak")
            k = "fajr"
        return k
    }

    function _src() {
        return "../assets/prayer_icons/" + _key()
                + (active ? "_active.png" : "_inactive.png")
    }

    Image {
        id: img
        anchors.centerIn: parent
        width: root.iconSize * 1.125
        height: root.iconSize * 1.125
        source: root._src()
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: false
        asynchronous: false
        cache: true
        sourceSize.width: 128
        sourceSize.height: 128
    }

    onPrayerKeyChanged: img.source = _src()
    onActiveChanged: img.source = _src()
}
