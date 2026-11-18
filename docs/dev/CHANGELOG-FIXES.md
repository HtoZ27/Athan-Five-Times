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

---

## أيقونة الدرج — تغطية freedesktop + أداة تشخيص (2026-10-19)

**الملفات**: `backend/tray_backend.py`, `backend/main.py`, `qml/main.qml`, `scripts/e2e-tray.py`, `scripts/e2e-tray-mocks.py`, `scripts/e2e-tray-xembed.py`, `scripts/e2e-tray-envs.sh`, `scripts/tray-probe.py`, `tests/test_tray_backends.py`, `docs/dev/FREEDESKTOP-TRAY-MATRIX.md`, `docs/dev/WAYLAND-NOTES.md`

**المشكلة**: على غير xcb (Wayland) يرجع Qt `isSystemTrayAvailable() == True` دائمًا حتى بلا host → خطر إخفاء النافذة بلا أيقونة. لا سيناريو e2e لـXEmbed. لا أداة تحقق ميدانية على GNOME/MATE.

**قبل**: بوابة التوفر تعتمد Qt فقط على غير xcb؛ 11 فحص e2e (no-host/xapp/sni) بلا XEmbed.

**بعد**:
- بوابة `qt_tray_available()` تشترط `org.kde.StatusNotifierWatcher` على غير xcb (`SNI_WATCHER_NAME`)؛ `QtTrayBackend.is_hosted()` يستخدم البوابة → لا إخفاء وهمي.
- e2e XEmbed حقيقي: مدير وهمي `scripts/e2e-tray-xembed.py` (libX11 عبر ctypes) + سيناريو في `scripts/e2e-tray-envs.sh` → **14/14** خضراء (no-host 1 / xapp 6 / sni 4 / xembed 3)، وأثبت `DOCK window=...` من Qt.
- أداة `scripts/tray-probe.py` (ثابت + `--live N` بأيقونة وقائمة وأحداث) للتحقق على GNOME X11/Wayland وMATE؛ مُثبتة معزولًا على مساري SNI وXEmbed.
- توثيق: `FREEDESKTOP-TRAY-MATRIX.md` (مصفوفة كاملة + قسم تحقق GNOME/MATE) + تحديث `WAYLAND-NOTES.md`.

**التأثير**: ✅ pytest 34، ruff نظيف، `git diff --check` نظيف، بلا عمليات متروكة.

**غير مشمول**: التحقق على جلسات Wayland/GNOME/MATE الحقيقية (يُنفَّذ بـprobe من المستخدم)؛ سيناريو host متأخر بعد رفض XEmbed الأول (`_tray_retry_timer`).

---

## المنطقة الزمنية للمدينة + عرض الإعدادات (2026-11-17)

**الملفات**: `backend/location.py`, `backend/backend_controller.py`, `qml/SettingsDialog.qml`, `qml/ThemedButton.qml`, `qml/VirtualCityPicker.qml`, `tests/test_timezone_resolution.py`, `scripts/e2e-features.py`, `packaging/*`

**المشكلة**: بعد اختيار مدينة، كانت المنطقة الزمنية تُشتق من **أول صف** في جداول النظام أو تفشل كليًا، فيبقى توقيت أجنبي قديم. الأمثلة الحقيقية: لوس أنجلوس كانت تُحسب بتوقيت نيويورك (فرق 3 ساعات)، بروكسل بقيت على `Australia/Lord_Howe` (فرق 8.5 ساعات)، وبعد تحويل لغة الواجهة من العربية كان البحث بالاسم المترجم يفشل لأن الجداول تُعرَّف برمز ISO فقط.

**قبل** (`location.py`):
```python
table.setdefault(parts[0].upper(), []).append(parts[2])  # "SA,AQ,KW,YE" مفتاح حرفي
zones = ...; return zones[0]                             # أول منطقة لا الأقرب
return COUNTRY_TZ.get(name, "")                          # اسم مترجم
```
```python
tz = _tz_for_country(country_name(country), country)
if tz:                                                    # يفشل => يبقى القديم
    updates["timezone"] = tz
```

**بعد**:
- دمج `zone.tab` + `zone1970.tab` وتقسيم أكواد الدول المفصولة بفواصل (`SA,AQ,KW,YE` → أربع دول).
- اختيار **أقرب** منطقة بإحداثيات الجدول (مسافة equirectangular)؛ `(0,0)` تعني «لا تحديد» فتبقى المنطقة التمثيلية.
- البحث برمز ISO أولًا (مستقل عن اللغة)، وعند غياب الدولة من tzdb سقوط إلى `Etc/GMT±N` (بإشارة IANA المعكوسة) أو `UTC` بدل إبقاء منطقة أجنبية.
- وحدة التحكم تستبدل المنطقة دائمًا عند تغيير المدينة/الدولة/الموقع التلقائي، وإلغاء تحديد «إحداثيات مخصصة» يعيد إحداثيات المدينة ويجدول إعادة الحساب فورًا.
- قائمة الإعدادات تعرض المنطقة المحلولة حتى لو لم تكن ضمن الـ36 الشائعة (بيرث، فلاديفوستوك، فانكوفر…)، وتتزامن عند `locationChanged` دون إعادة فتح النافذة؛ وتُصحح تسمية `Etc/GMT-1` إلى `UTC+1`.
- زر «عرض المزيد» المدمج يأخذ عرض نصه بدل 32px الثابتة.

**قبل → بعد (قياس)**:
| الحالة | قبل | بعد |
|---|---|---|
| لوس أنجلوس، 21 يونيو | فجر 06:43 (نيويورك) | فجر 03:43 |
| بروكسل، 21 يونيو | فجر 11:29 (Lord Howe) | فجر 02:59 |
| بيرث في قائمة الإعدادات | الرياض/تونس (عنصر خاطئ) | Australia/Perth |
| إلغاء الإحداثيات المخصصة | معاينة سيدني تبقى | عودة فجر تونس فورًا |

**الأدلة**:
- `tests/test_timezone_resolution.py`: **34** اختبارًا (أكواد مفصولة بفواصل، أقرب منطقة، مصفوفة 17 لغة، رموز غائبة، استبدال المنطقة القديمة، تسميات GMT، إلغاء الإحداثيات).
- `pytest`: **660** اختبارًا ناجحًا، و`ruff check`/`format` نظيفان.
- إثبات معزول `/tmp/opencode/tz-fixed-proof.py`: **0 فشل** — 241/241 مدينة/دولة تحل منطقة، 4 رموز غائبة عن tzdb تسقط إلى `Etc/GMT-N` (XG/XK/XR/XW)، 204 زوج (17 لغة × 12 دولة) ناجح.
- e2e معزول: **254/254** فحصًا و0 أخطاء QML، منها أقرب منطقة لـUS/RU/AU/CA/BR، وست لغات مع السعودية، وعنصر بيرث في القائمة، وعرض زر «عرض المزيد»، وإلغاء حقيقي لمربع الإحداثيات مع إعادة الحساب.

**الحزم**: أُضيفت تبعية `tzdata` إلى deb/rpm/Arch، لأن التطبيق المبني لا يستخدم `pytz` ويعتمد على جداول `/usr/share/zoneinfo`.

---

## تجاوز التخطيط الهندي/البنجابي + ثبات CI (2026-11-18)

**الملفات**: `qml/SettingsDialog.qml`, `.github/workflows/ci.yml`, `packaging/rpm/athan-five-times.spec`

**المشكلة**: في نافذة الإعدادات بعرض 460×680 كانت تبويبات الصوت/الإشعارات تخرج عن الإطار في اللغتين الهندية `hi` والبنجابية `pa` (نصوص أطول من العربية)، فسجّل e2e في CI:

| اللغة | الفحص | القياس من CI |
|---|---|---|
| `pa` | tab4 | `QQuickRowLayout w=433` مقابل `tabW=408`، و`ThemedSpinBox w=104` |
| `hi` | tab3 | `Label w=456` مقابل `tabW=408` |
| `hi` | tab4 | `QQuickRowLayout w=409` مقابل `tabW=408` |

**السبب**: عناوين `GroupBox` كانت بحجم نصها الكامل دون قص أو التفاف، وصفوف «مدة التلاشي» و«التنبيه المبكر» و«DND» كانت تضع التسمية و`ThemedSpinBox` في صف واحد دون السماح للتسمية بالتقلّص، وسطرا «من الساعة/إلى الساعة» كانا في صف واحد فيتجاوزان العرض.

**قبل** (`SettingsDialog.qml`):
```qml
label: Label { z: 2; text: tr("الصوت العام"); ... }          // بلا width ولا wrap
Label { text: tr("مدة التلاشي (ثوانٍ):"); Layout.fillWidth: true }  // تُقصّ لا تلتف
RowLayout { Label { text: tr("من الساعة:") } ThemedSpinBox{} Label { text: tr("إلى الساعة:") } ThemedSpinBox{} }
```

**بعد**:
```qml
label: Label { width: parent ? Math.max(120, parent.width - 28) : implicitWidth
               wrapMode: Text.WordWrap; ... }                 // كل العناوين الـ25
Label { Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.WordWrap }
RowLayout { Layout.fillWidth: true; ... }                     // «من/إلى» في صفّين مستقلّين
```

**الأدلة**:
- e2e معزول على **PySide6 6.12.0** (نفس نسخة CI): **254/254** فحصًا، **0** أخطاء QML، ومنها `ui-lang-pa` و`ui-lang-hi`.
- مسح تخطيط لكل اللغات الـ17 × 8 تبويبات عند كثافات خط 96/102/108/114: **17/17 نظيفة** في كل كثافة.
- `pytest`: **660** اختبارًا ناجحًا، و`ruff check`/`format` نظيفان على `backend/` و`tests/`.

**CI**: كان فشل `test (3.10)` مركّبًا من مشكلتين: تجاوز التخطيط أعلاه، ثم انهيار `Fatal Python error: none_dealloc: deallocating None`. أُعيد إنتاجه محليًا على Python 3.10.22 و3.11.18 مع PySide6 6.12.0 (نفس الشيفرة تنجح على 3.12.3)، فالخلل في shiboken 6.12.0: يخفض عدّاد `None` مرة إضافية، ولا يكون قاتلًا إلا قبل Python 3.12 حيث `None` خالد. لذلك:
- e2e الواجهة يُشغَّل مرة واحدة على **3.12** (اختبار سلوك تطبيق لا اختبار مفسّر)، و`pytest` يبقى على 3.10/3.11/3.12، و`smoke-qml` يغطي QML على 3.11.
- `fail-fast: false` حتى لا يُلغي فشل 3.10 مهمة 3.12 قبل انتهائها.
