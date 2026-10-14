# سجل الإصلاحات — Athan Five Times

> كل إصلاح مسجل بصيغة: **الملف** | **المشكلة** | **قبل** → **بعد**

---

## 1. 🔴 ثيم AppDir لا يتحدّث (5 ملفات QML)

### الملفات: `AppDir/.../qml/main.qml`, `PrayerTimesTab.qml`, `PrayerAthkarTab.qml`, `AthkarTab.qml`, `AthkarPopup.qml`

**المشكلة**: كانت كل خصائص `_pal` و الألوان معرفة كـ `readonly property`، ولا يوجد `Connections` لربط `onResolvedThemeChanged` — تغيير الثيم لا يؤثر على الواجهة خارج نافذة الإعدادات.

**قبل** (`main.qml`):
```qml
readonly property var _pal: Theme.resolvePalette(...)
readonly property color bgColor: _pal.background
// ...لا يوجد Connections block
```

**بعد**:
```qml
property var _pal: Theme.resolvePalette(...)
property color bgColor: _pal.background
// ...
Connections {
    target: themeController
    function onResolvedThemeChanged(resolvedTheme) {
        _pal = Theme.resolvePalette(resolvedTheme)
        bgColor = _pal.background
        // ...كل الألوان
    }
}
```

**التأثير**: ✅ الثيم يتحدّث فوراً في كل الواجهة.

---

## 2. 🔴 حفظ الثيم في AppDir لا يعمل

### الملف: `AppDir/.../backend/main.py`

**المشكلة**: خط 89 — ربط `themeChanged` بدالة `_on_theme_controller_changed` التي تسجّل فقط (`logger.info`) ولا تحفظ الثيم.

**قبل**:
```python
self._theme_controller.themeChanged.connect(self._on_theme_controller_changed)

def _on_theme_controller_changed(self, theme_id: str):
    logger.info("ThemeController applied: %s", theme_id)
```

**بعد**:
```python
self._theme_controller.themeChanged.connect(
    self._prayer_engine.saveTheme, Qt.ConnectionType.QueuedConnection)
# وإزالة الدالة _on_theme_controller_changed غير المستخدمة
```

**التأثير**: ✅ الثيم يُحفظ تلقائياً عند تغييره.

---

## 3. 🔴 `_pal` ثابت في SettingsField + SettingsGroupBox

### الملفات: `qml/settings/SettingsField.qml`, `qml/settings/SettingsGroupBox.qml` (كلا النسختين)

**المشكلة**: `readonly property var _pal` — لا يمكن إعادة تعيين القيمة، المكوّنات لا ترى تغييرات الثيم أبداً.

**قبل**:
```qml
readonly property var _pal: Theme.resolvePalette(...)
```

**بعد**:
```qml
property var _pal: Theme.resolvePalette(...)
```

**التأثير**: ✅ ألوان الـ Label و الـ background تتحدّث مع الثيم.

---

## 4. 🔴 انقسام مخزن الثيم (JSON vs QSettings)

### الملف: `AppDir/.../backend/theme_controller.py`

**المشكلة**: الـ AppDir يستخدم `QSettings("AthanPrayer", "Theme")` بينما الجذر يستخدم ملف JSON عبر `settings.py`.

**قبل**:
```python
self._settings = QSettings("AthanPrayer", "Theme")
theme = self._settings.value("theme", "dark")
self._settings.setValue("theme", theme_id)
```

**بعد** (متوافق مع الجذر):
```python
from .settings import get_setting, update_setting
# استيراد واستخدام SETTINGS_FILE عبر settings.py
theme = get_setting("theme", "dark")
update_setting("theme", theme_id)
```

**التأثير**: ✅ كلا النسختين يستخدمان نفس مخزن JSON — لا انقسام.

---

## 5. 🟡 `required property var modelData` للتكرارات المفقودة

### الملفات: `qml/SettingsDialog.qml`, `qml/settings/SettingsTabs.qml`

**المشكلة**: Repeater يستخدم `modelData` بدون `required property var modelData` — يعمل في Qt5 لكنه هش في Qt6 وقد ينكسر.

**قبل**:
```qml
Repeater {
    model: tabsModel
    delegate: TabButton {
        text: modelData.label  // معتمد على الـ scope فقط
    }
}
```

**بعد**:
```qml
Repeater {
    model: tabsModel
    delegate: TabButton {
        required property var modelData
        text: modelData.label  // explicit binding
    }
}
```

**التأثير**: ✅ مستقر في Qt6.

---

## 6. 🟡 مزامنة `settings.py` مع الجذر

### الملف: `AppDir/.../backend/settings.py`

**المشكلة**: لا يوجد `_SETTINGS_LOCK`، استثناءات عامة `Exception`، لا `invalidate_cache` تستدعي `invalidate_muezzin_cache()`.

**قبل**: قفل مفقود، `except Exception` بدون تحديد.

**بعد**: إضافة `_SETTINGS_LOCK = RLock()`، استثناءات محددة (`KeyError`, `ValueError`، إلخ)، `invalidate_cache` تستدعي جميع دوال الإبطال.

**التأثير**: ✅ سلامة الخيوط، رسائل خطأ دقيقة.

---

## 7. 🟡 مزامنة `audio.py` مع الجذر

### الملف: `AppDir/.../backend/audio.py`

**المشكلة**: لا `@lru_cache` على `_init_player`، إدارة الأجهزة يدوية.

**قبل**: cache يدوي `dict`، `Lock` بسيط.

**بعد**: `@lru_cache(maxsize=2)` مع `device._device` للمقارنة وإعادة استخدام الجهاز، `RLock`.

**التأثير**: ✅ أداء أفضل، إعادة استخدام الأجهزة.

---

## 8. 🟡 مزامنة `location.py` مع الجذر

### الملف: `AppDir/.../backend/location.py`

**المشكلة**: لا `retries` parameter، مهلة 3s فقط.

**قبل**: مهلة 3 ثوانٍ، لا retries، `except Exception`.

**بعد**: مهلة 10 ثوانٍ، retries=1، معالجة 0,0 بشكل صحيح.

**التأثير**: ✅ تحديد موقع أكثر متانة.

---

## 9. 🟡 مزامنة `prayer_calc.py` مع الجذر

### الملف: `AppDir/.../backend/prayer_calc.py`

**المشكلة**: لا `_OFFSETS_CACHE`، مقارنة floats خام.

**قبل**: حساب الإزاحات من دون cache، مفاتيح float raw.

**بعد**: `_OFFSETS_CACHE` بسعة 32، تقريب لـ 6 منازل عشرية.

**التأثير**: ✅ أداء أفضل للحسابات المتكررة.

---

## 10. 🟡 مزامنة `main.py` مع الجذر

### الملف: `AppDir/.../backend/main.py`

**المشكلة**: نقص `gc` import، إعدادات QT، `cleanup()` عند الخروج.

**قبل**:
```python
# لا gc import
# لا QT_AUTO_SCREEN_SCALE_FACTOR
# لا cleanup()
```

**بعد**:
```python
import gc
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_QPA_PLATFORMTHEME"] = "qt6ct"

def _quit(self):
    self._theme_controller.cleanup()
    self._prayer_engine.stopAzan()
    QApplication.quit()
```

**التأثير**: ✅ تطابق تام مع الجذر، تنظيف صحيح عند الخروج.

---

## Adhkar library completion (azkar-db merge)

**الملفات**: `assets/adhkar/*` (140 ملفاً), `backend/adhkar_repo.py`, `tests/test_adhkar_repo.py`

**المصدر**: azkar-db (345 صفاً) + مكتبة Dart الأساسية (74 عنصراً).
**النتيجة**: 140 تصنيفاً / 382 عنصراً، 37 مكرراً حُذف، 6 تعارضات أعداد أُبقي فيها على نسختنا.
**السياسة**: عند التعارض تُحفظ نسختنا (روايات متعددة مشروعة)؛ الغائب عدده يُفترض 1؛ المرجع الغائب يبقى غائباً.
