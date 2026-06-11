# PROJECT_CONTEXT.md

## هيكل المشروع

```
AthanFiveTimes/
├── backend/                    # كود Python الخلفي
│   ├── main.py                 # نقطة الدخول (PySide6 + QML)
│   ├── backend_controller.py   # Bridge بين Python و QML
│   ├── prayer_calc.py          # حساب مواقيت الصلاة (مكتبة adhan)
│   ├── countries_data.py       # بيانات 241 دولة + المدن
│   ├── settings.py             # إدارة الإعدادات (تحميل/حفظ)
│   ├── theme_controller.py     # إدارة الثيمات
│   ├── audio.py                # تشغيل الأذان (miniaudio)
│   ├── location.py             # تحديد الموقع عبر IP
│   ├── memory_profiler.py      # مراقبة الذاكرة (اختياري)
│   ├── i18n.py                 # الترجمة
│   ├── _constants.py           # الثوابت
│   ├── athkar_provider.py      # الأذكار
│   └── translations/           # ملفات JSON للترجمة (17 لغة)
├── qml/                        # واجهة المستخدم QML
│   ├── main.qml
│   ├── SettingsDialog.qml
│   ├── PrayerTimesTab.qml
│   ├── AthkarTab.qml
│   ├── Theme.qml
│   └── settings/
├── assets/                     # موارد (خطوط، صور، أذان MP3)
├── AppDir/                     # نسخة للتعبئة (AppImage)
│   └── usr/share/prayer_app/   # نسخة مطابقة من المصدر
├── tests/                      # اختبارات pytest (72 اختبار)
├── requirements.txt            # متطلبات Python
├── run.sh                      # سكربت التشغيل
└── clean-dev.sh                # سكربت تنظيف البيئة
```

## التقنيات المستخدمة

| التقنية | الإصدار | الاستخدام |
|---------|---------|-----------|
| Python  | 3.10+   | المنطق الخلفي |
| PySide6 | 6.x     | ربط Python مع QML |
| QML     | Qt6     | واجهة المستخدم |
| adhan   | latest  | حساب مواقيت الصلاة |
| miniaudio | latest | تشغيل الأذان |
| pytest  | latest  | الاختبارات |

## الإعدادات المهمة

- **ملف الإعدادات:** `~/.config/athan-five-times/settings.json`
- **طريقة الحساب الافتراضية:** وزارة الشؤون الدينية التونسية (18°/18°)
- **المذهب الافتراضي:** shafi
- **اللغة الافتراضية:** ar (العربية)
- **عدد طرق الحساب:** 27 (6 built-in + 21 custom)
- **عدد الدول:** 241

## آخر التعديلات

- إضافة أسماء طرق حساب كاملة للدول
- ترتيب `COUNTRY_METHODS` أبجدياً
- إضافة `getDefaultMethod()` في `backend_controller.py`
- تحديث تلقائي لطريقة الحساب عند اختيار دولة في QML
- إصلاح استهلاك الذاكرة (راجع المشاكل المصلحة)

## المشاكل التي تم إصلاحها

### 1. استهلاك الذاكرة (RAM)
| المشكلة | الملف | الإصلاح |
|---------|-------|---------|
| `PrayerEngine.cleanup()` لا تُستدعى عند الإغلاق | `main.py` | إضافة `self._prayer_engine.cleanup()` في `_quit()` |
| `_azan_flash_timer` لا يتوقف عند الإغلاق | `main.py` | إضافة `self._azan_flash_timer.stop()` في `_quit()` |
| `_snapshots` في memory_profiler غير محدود | `memory_profiler.py` | إضافة حد أقصى `max_frames` مع حذف القديم |
| Timers لا تُحرر عند الإغلاق | `backend_controller.py` | تحرير `_clock_timer`, `_prayer_timer`, `_dnd_timer` |
| ThemeController ي bypass cache settings | `theme_controller.py` | استخدام `load_settings()` بدلاً من قراءة JSON مباشرة |

### 2. أخطاء سابقة
- سطر مكرر في `countries_data.py` سبب `SyntaxError` (تم الإصلاح)

## المهام المفتوحة

- [x] إصلاح استهلاك الذاكرة (RAM)
- [x] إنشاء `clean-dev.sh`
- [x] تحسين ThemeController
- [x] إنشاء PROJECT_CONTEXT.md
- [ ] اختبار الأداء بعد الإصلاحات

## طريقة التشغيل

```bash
# تشغيل التطبيق
cd AthanFiveTimes
python3 -m backend.main

# تشغيل الاختبارات
python3 -m pytest tests/ -q --tb=short

# تنظيف البيئة
./clean-dev.sh
```
