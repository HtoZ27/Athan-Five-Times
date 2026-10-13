import QtQuick
import Theme 1.0

/*!
    \qmltype ThemeColors
    \inqmlmodule Theme
    \ingroup Theme
    \brief Reactive theme color properties for all QML components.

    Eliminates ~240 lines of duplicated boilerplate across 8 QML files.
    Each component instantiates one ThemeColors object and uses its color
    properties. Colors update automatically when themeController.resolvedTheme changes.

    Usage:
        \qml
        ThemeColors { id: theme }
        Rectangle { color: theme.bgColor }
        Text { color: theme.textColor }
        \endqml
*/
QtObject {
    id: root

    property var _pal: Theme.resolvePalette(
        typeof themeController !== 'undefined' && themeController
            ? themeController.resolvedTheme : "light")

    property color bgColor: _pal.background
    property color cardColor: _pal.surface
    property color textColor: _pal.text
    property color textMutedColor: _pal.textMuted
    property color accentColor: _pal.primary
    property color borderColor: _pal.border
    property color warningColor: _pal.warning
    property color dangerColor: _pal.error
    property color backgroundOverlay: _pal.backgroundOverlay
}
