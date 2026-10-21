# نقاط Wayland — Athan Five Times

> سجل تحقق مؤقت. أُنشئ في 2026-10-19 (جلسة X11) لتوثيق كل ما يخص أيقونة الدرج
> على Wayland، لاختباره وإصلاحه عند فتح جلسة Wayland.
> المرجع الأساسي: `backend/tray_backend.py`.
> المصفوفة الكاملة لكل بيئات freedesktop: `docs/dev/FREEDESKTOP-TRAY-MATRIX.md`.

---

## ✅ ما أُصلح وأُثبت على X11 (سياق للرجوع)

1. **بوابة watcher على غير xcb** — `backend/tray_backend.py:86`:
   Qt يرجع `QSystemTrayIcon.isSystemTrayAvailable() == True` على أي منصة غير xcb حتى لو
   لا يوجد host إطلاقًا (`QGenericUnixTheme::shouldUseDBusTray()` ترجع true دائمًا هناك).
   لذلك صارت `qt_tray_available()` تطلب وجود `org.kde.StatusNotifierWatcher` على الناقل
   عندما لا تكون المنصة xcb (`SNI_WATCHER_NAME`، `_platform_name`، `_qt_reports_tray`،
   `sni_watcher_available` في الأسطر 39-110).
2. **`QtTrayBackend.is_hosted()`** — `backend/tray_backend.py:215`: يستخدم البوابة، فلا
   يُعتبر «مستضافًا» وهميًا على Wayland بدون host (يمنع إخفاء النافذة بلا أيقونة).
3. **اختبارات وحدة** — `tests/test_tray_backends.py::TestQtAvailability` + حالة
   `is_hosted` على Wayland بدون watcher.
4. **e2e** — `scripts/e2e-tray-envs.sh` صار كامل الأخضر على xcb (no-host / xapp / sni / xembed)،
   مع إصلاحين في الـharness:
   - mock watcher كان يفقد ملكية الاسم لأن مرجع `dbus.service.BusName` كان يُجمع (GC).
   - Qt 6.11 يسجّل أيقونة SNI باسم الاتصال الفريد (`:1.x`) وليس
     `org.kde.StatusNotifierItem-*`؛ الـharness الآن يقرأ الاسم من سطر `REGISTER_ITEM`.

---

## 🔍 نقاط تحتاج تحققًا على جلسة Wayland

### 1) الكشف عن الـhost
- [ ] KDE Plasma Wayland (plasmashell = watcher) → أيقونة ظاهرة.
- [ ] GNOME Wayland + AppIndicator extension → أيقونة ظاهرة.
- [ ] GNOME Wayland بدون extension → **لا** watcher: يجب أن يبقى
      `trayAvailable=false`، والإغلاق = خروج (وليس إخفاء)، بلا إعادة بناء backend مستمرة.
- [ ] sway / Hyprland + waybar → أيقونة ظاهرة.
- [ ] ظهور watcher متأخرًا (login بطيء): يلتقطه `_tray_retry_timer` (3 ثوان).
- [ ] إعادة تشغيل اللوحة/فقدان watcher: يعيد `_tray_watchdog` (10 ثوان) البناء.

كيف نتحقق: سجل التطبيق يطبع `System tray ready (qt backend)` عند النجاح،
`No system tray host detected yet` عند غياب host.

### 2) القائمة والمحتوى (SNI/DBusMenu)
- [ ] يمين/يسار انقر على الأيقونة يفتح القائمة (إظهار النافذة، الودجة المصغرة،
      معلومات الصلاة، خروج) — عبر DBusMenu في `_build_tray_menu` (backend/main.py:417).
- [ ] اتجاه RTL للقائمة العربية (`_apply_menu_direction`، backend/main.py:449).
- [ ] تحديث tooltip كل دقيقة (`tray_tooltip` → `_on_tray_info_changed`، main.py:583).
- [ ] وميض الأيقونة وقت الأذان (`_toggle_tray_icon`، main.py:653): بعض hosts تتعامل مع
      `IconName` مقابل `IconPixmap` بشكل مختلف — تحقق أن الوميض يعود ولا يختفي نهائيًا.

### 3) التفعيل والعودة من الدرج
- [ ] نقرة يسار تعيد النافذة: `_show_window` (main.py:664) يستخدم
      `showNormal/raise_/requestActivate` — Wayland يتجاهل raise/activate غالبًا؛
      إن لم تُنشَّط النافذة قد نحتاج `QWindow::alert` أو xdg-activation.
- [ ] close-to-tray في `qml/main.qml` يعتمد `trayAvailable` — تأكد أن
      `_refresh_tray_context` (main.py:550) يحدّث القيمة لحظيًا عند ظهور/اختفاء الدرج.
- [ ] `_popup_tray_menu` (main.py:529) يستخدم `QCursor.pos()` — غير موثوق على Wayland
      (يهم فقط لو أضفنا backend غير SNI على Wayland؛ XApp خاص بـMint/X11).

### 4) الإشعارات
- [ ] `show_message` عبر Qt SNI على Wayland يمر عبر `org.freedesktop.Notifications`
      (xdg-desktop-portal على GNOME) — تحقق من وصولها، ومن سلسلة fallback إلى
      `notify-send` في `backend_controller._notify_os`.

### 5) عام
- [ ] لا نجبر `QT_QPA_PLATFORM`؛ التطبيق يختار wayland تلقائيًا (`./run.sh`).
- [ ] استرجاع موضع الودجة يتخطى الإحداثيات على Wayland (`isWaylandRuntime`) — تحقق.
- [ ] XWayland (platformName=xcb) بدون host: لا أيقونة وهمية (البوابة تعتمد Qt هنا).

---

## 🧪 أوامر جمع الأدلة على Wayland

```bash
echo "$XDG_SESSION_TYPE / $WAYLAND_DISPLAY / $QT_QPA_PLATFORM"
python3 scripts/tray-probe.py                    # فحص ثابت: الناقل + Qt + XEmbed
python3 scripts/tray-probe.py --live 20          # أيقونة حقيقية + أحداث النقر/القائمة
busctl --user list | grep -i statusnotifier      # من يملك org.kde.StatusNotifierWatcher
QT_LOGGING_RULES="qt.qpa.*=true" ./run.sh 2>&1 | tee /tmp/athan-wayland.log
# ابحث في السجل عن:
#   "System tray ready (qt backend)"            → نجح التسجيل
#   "No system tray host detected yet"          → لا host (retry كل 3 ثوان)
#   'qt.qpa.menu: failed to find service "org.kde.StatusNotifierWatcher"' → لا watcher
```

### اختبارات الاستمرارية (تعمل الآن على X11 فقط)
```bash
python3 -m pytest tests/test_tray_backends.py tests/test_tray.py -q
bash scripts/e2e-tray-envs.sh        # no-host / xapp / sni / xembed (xcb + Xephyr)
```
> ملاحظة: لا يوجد سيناريو e2e على Wayland بعد؛ يمكن إضافة compositor هيدلس
> (weston/labwc) داخل `scripts/e2e-tray-envs.sh` لاحقًا.

---

## ✅ تحقق تنفيذي على GNOME Wayland 46 (جلسة حقيقية، بلا extension) — 2026-10-21

الجلسة: `systemctl --user show-environment` → `XDG_SESSION_TYPE=wayland`,
`WAYLAND_DISPLAY=wayland-0`, `XDG_CURRENT_DESKTOP=GNOME`. ملاحظة بيئية: بلا
إضافات مثبتة (`gsettings get org.gnome.shell enabled-extensions` = `[]`)، والـshell
يظهر له `XDG_SESSION_TYPE=x11` تحملته البيئة من الجلسة السابقة — لا يؤثر: كل
القرارات المؤثرة تعتمد `QGuiApplication.platformName()` (= `wayland`).

| النقطة الموثقة | النتيجة | الدليل |
|---|---|---|
| بلا extension → لا أيقونة ولا إخفاء وهمي | ✅ | probe: `qt-platform=wayland`, `sni_watcher=False`, `detect=none`; سجل التطبيق بلا "System tray ready" |
| ظهور watcher متأخرًا → retry (3 ثوان) | ✅ | `scripts/e2e-tray-mocks.py --watcher` → التقاط خلال ~2 ثانية: `System tray ready (qt backend)` |
| تسجيل عنصر SNI على Wayland | ✅ | `REGISTER_ITEM :1.60559 /StatusNotifierItem`؛ المشروع الكامل: `/MenuBar` + `/StatusNotifierItem` |
| خصائص SNI + القائمة (DBusMenu) | ✅ | `Id/Title=أذان الصلاة`, `Status=Active`, `Menu=/MenuBar`, `ToolTip` (صلاة قادمة حيّة)؛ `GetLayout`: إظهار النافذة/الودجة المصغرة/معلومات الصلاة/خروج |
| فقدان watcher → watchdog (10 ثوان) | ✅ | سطران `Tray host container disappeared — rebuilding the icon` (02:04:05, 02:05:04) والتطبيق حي، بلا انهيار |
| عودة watcher → إعادة البناء | ✅ | `System tray ready (qt backend)` للمرة الثانية (02:04:24)، ثم فقد ثالث عولج بدورة retry/rebuild |
| Activate (تفعيل) | ✅ | `org.kde.StatusNotifierItem.Activate(0,0)` أُرسل بلا خطأ (التركيز المرئي: فحص بشري) |
| XWayland (`QT_QPA_PLATFORM=xcb`) بلا إيجابية كاذبة | ✅ | probe: `qt-platform=xcb`, `qt_reports=False`, `detect=none` |
| بلا إجبار منصة | ✅ | qpa=`wayland;xcb` → Qt اختار `wayland` تلقائيًا |
| خدمة الإشعارات | ⚠️ ملاحظة | `org.freedesktop.Notifications` يملكه في هذه الجلسة `xfce4-notifyd` (بيئة مركّبة زیر قبضته) — الخدمة موجودة ويعرضها |

خاتمة: كل السلوكات المؤتمتة الموثقة أعلاه مُثبتة على جلسة Wayland حقيقية.
المتبقي مرئي فقط: نجوم RTL ووميض الأيقونة وشكل النافذة العائمة، وتحقق
المستخدم من تركيز النافذة عند Activate، وإغلاق النافذة أثناء غياب الـhost = خروج.
سيناريو GNOME + AppIndicator extension يبقى مطلوبًا إن ثُبّتت الإضافة لاحقًا.

---

## ✅ تحقق GNOME Wayland + AppIndicator extension (2026-10-21، بعد تثبيت الإضافة)

الحزمة: `gnome-shell-extension-appindicator 58-1ubuntu24.04.1` (Mint 22.3 / Ubuntu
noble، GNOME Shell 46). بعد تثبيتها **يلزم خروج/دخول** — لا تكتشف قشرة Wayland
الإضافة المثبّتة أثناء التشغيل. بعد الدخول: `org.kde.StatusNotifierWatcher` يملكه
`gnome-shell`، و`gnome-extensions list` قد يبقى فارغًا رغم عمل الإضافة (تحقق
بالناقل لا بالأداة).

| النقطة | النتيجة | الدليل |
|---|---|---|
| الكشف | ✅ | probe: `qt-platform=wayland`, `qt_reports=True`, `sni_watcher=True` (owner=gnome-shell), `detect=qt` |
| تسجيل حي | ✅ | `--live 20` → `backend=qt`, `live-hosted=True` |
| الأيقونة في الشريط العلوي | ✅ (بشري) | ظهرت أيقونة "أذان الصلاة" |
| القائمة العربية عبر DBusMenu | ✅ (بشري) | النقر يفتح: إظهار النافذة / الودجة المصغرة / الصلاة القادمة / خروج |
| close-to-tray | ✅ | إغلاق النافذة X → العملية بقيت حيّة (تحقق آلي بـpid) |
| Activate يعيد النافذة | ✅ | `Activate(0,0)` على `:1.3284` → النافذة عادت (تأكيد بشري) |
| خروج من القائمة | ✅ (بشري) | "خروج" أنهى العملية |
| التلميحات | ⚠️ غير مدعومة | إضافة GNOME لا تعرض ToolTip (موثق في المصفوفة) |

ملاحظات تشغيلية:

- شكل عنصر الـwatcher في GNOME للاتصالات الفريدة هو `:1.x@/StatusNotifierItem`
  (اسم@مسار) وليس `org.kde.StatusNotifierItem-*` — عند الفحص اليدوي فكّ السلسلة
  على `@` أولًا.
- في هذه الجلسة `org.freedesktop.Notifications` يملكه `xfce4-notifyd` وليس
  gnome-shell (تداخل حزم Mint)؛ يعمل الإشعار عبره.
