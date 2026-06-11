// Theme.qml
// Fusion-compatible theme singleton with static design tokens
pragma Singleton
import QtQuick

QtObject {
    // Design Tokens - Static, zero-cost abstractions
    readonly property int radiusSmall: 6
    readonly property int radiusMedium: 10
    readonly property int radiusLarge: 16
    readonly property int radiusXLarge: 20

    readonly property int space1: 8
    readonly property int space2: 16
    readonly property int space3: 24
    readonly property int space4: 32

    readonly property int animFast: 120
    readonly property int animMedium: 200
    readonly property int animSlow: 300

    // Static color palettes - Fusion compatible (readonly for zero-copy)
    readonly property var darkPalette: {
        "background": "#1a1a1e",
        "surface": "#2c2c30",
        "surfaceVariant": "#3a3a40",
        "backgroundOverlay": "rgba(0,0,0,0.5)",
        "primary": "#c8a849",
        "primaryVariant": "#b89839",
        "onPrimary": "#1a1a1e",
        "text": "#e5e5ea",
        "textMuted": "#a0a0a5",
        "textDisabled": "#6a6a72",
        "border": "#3a3a40",
        "borderLight": "#4a4a50",
        "divider": "#3a3a40",
        "shadow": "rgba(0,0,0,0.3)",
        "shadowStrong": "rgba(0,0,0,0.5)",
        "error": "#dc5050",
        "errorContainer": "#3a1a1a",
        "success": "#4ecdc4",
        "warning": "#e8a030",
        "info": "#4F46E5"
    }

    readonly property var lightPalette: {
        "background": "#f5f5f7",
        "surface": "#ffffff",
        "surfaceVariant": "#e8e8ec",
        "backgroundOverlay": "rgba(255,255,255,0.9)",
        "primary": "#8b6914",
        "primaryVariant": "#7a5c11",
        "onPrimary": "#ffffff",
        "text": "#1a1a1e",
        "textMuted": "#505055",
        "textDisabled": "#8a8a90",
        "border": "#b8b8be",
        "borderLight": "#ccccd2",
        "divider": "#d8d8de",
        "shadow": "rgba(0,0,0,0.1)",
        "shadowStrong": "rgba(0,0,0,0.15)",
        "error": "#c03030",
        "errorContainer": "#fdeaea",
        "success": "#4ecdc4",
        "warning": "#c88010",
        "info": "#4F46E5"
    }

    readonly property var catppuccinMochaPalette: {
        "background": "#1e1e2e",
        "surface": "#313244",
        "surfaceVariant": "#181825",
        "backgroundOverlay": "rgba(0,0,0,0.5)",
        "primary": "#cba6f7",
        "primaryVariant": "#b4befe",
        "onPrimary": "#1e1e2e",
        "text": "#cdd6f4",
        "textMuted": "#a6adc8",
        "textDisabled": "#585b70",
        "border": "#45475a",
        "borderLight": "#585b70",
        "divider": "#45475a",
        "shadow": "rgba(0,0,0,0.3)",
        "shadowStrong": "rgba(0,0,0,0.5)",
        "error": "#f38ba8",
        "errorContainer": "#3a1a2a",
        "success": "#a6e3a1",
        "warning": "#f9e2af",
        "info": "#89b4fa"
    }

    readonly property var catppuccinLattePalette: {
        "background": "#eff1f5",
        "surface": "#ccd0da",
        "surfaceVariant": "#e6e9ef",
        "backgroundOverlay": "rgba(255,255,255,0.9)",
        "primary": "#8839ef",
        "primaryVariant": "#7287fd",
        "onPrimary": "#ffffff",
        "text": "#4c4f69",
        "textMuted": "#6c6f85",
        "textDisabled": "#9ca0b0",
        "border": "#bcc0cc",
        "borderLight": "#ccd0da",
        "divider": "#bcc0cc",
        "shadow": "rgba(0,0,0,0.1)",
        "shadowStrong": "rgba(0,0,0,0.15)",
        "error": "#d20f39",
        "errorContainer": "#fdeaea",
        "success": "#40a02b",
        "warning": "#df8e1d",
        "info": "#1e66f5"
    }

    readonly property var ottomanGoldPalette: {
        "background": "#1a1816",
        "surface": "#252220",
        "surfaceVariant": "#2f2a25",
        "backgroundOverlay": "rgba(0,0,0,0.5)",
        "primary": "#d4a030",
        "primaryVariant": "#c49028",
        "onPrimary": "#1a1816",
        "text": "#ffffff",
        "textMuted": "#d4c5a0",
        "textDisabled": "#8a7a5a",
        "border": "#4a4035",
        "borderLight": "#5a4a3d",
        "divider": "#4a4035",
        "shadow": "rgba(0,0,0,0.5)",
        "shadowStrong": "rgba(0,0,0,0.7)",
        "error": "#e05050",
        "errorContainer": "#3a1a16",
        "success": "#4ecdc4",
        "warning": "#e8c55a",
        "info": "#4F46E5"
    }

    // Internal cache for resolved palettes - initialized to empty object
    property var _paletteCache: ({})

    // Resolved palette getter with caching and robust undefined handling
    function resolvePalette(themeId) {
        // Handle undefined/null themeId - default to dark
        var tid = (themeId === undefined || themeId === null) ? "dark" : themeId
        
        var cache = _paletteCache
        // Ensure cache is an object
        if (cache === undefined || cache === null) {
            cache = {}
        }
        
        if (cache[tid] !== undefined) {
            return cache[tid]
        }
        
        var palette
        switch (tid) {
            case "light":
                palette = lightPalette
                break
            case "catppuccin_mocha":
                palette = catppuccinMochaPalette
                break
            case "catppuccin_latte":
                palette = catppuccinLattePalette
                break
            case "ottoman_gold":
                palette = ottomanGoldPalette
                break
            case "dark":
            default:
                palette = darkPalette
                break
        }
        cache[tid] = palette
        return palette
    }
}
