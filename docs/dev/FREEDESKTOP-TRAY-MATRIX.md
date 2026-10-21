# مصفوفة بيئات freedesktop — أيقونة الدرج (Athan Five Times)

> النطاق: كل بيئات سطح المكتب القياسية على X11 وWayland. الهدف: أيقونة درج تعمل
> (أو يُعطَّل close-to-tray بأمان عند غياب host). أُنشئ في 2026-10-19.
> المرجع البرمجي: `backend/tray_backend.py`؛ نقاط Wayland التفصيلية:
> `docs/dev/WAYLAND-NOTES.md`.

---

## كيف يُختار الـbackend

`detect_tray_kind()` يجرّب بالترتيب:

1. **Qt** — `QSystemTrayIcon`:
   - على xcb: SNI إن وُجد `org.kde.StatusNotifierWatcher`، وإلا XEmbed عبر
     `_NET_SYSTEM_TRAY_S<screen>`.
   - على غير xcb (Wayland): SNI فقط، وبوابة `qt_tray_available()` تشترط وجود watcher
     (Qt يبلّغ `isSystemTrayAvailable()==True` وهميًا بدون host).
2. **XApp** — `org.x.StatusIcon` + `org.x.StatusIconMonitor` (Mint/XApp).
3. **None** — لا host: `trayAvailable=false`، إعادة محاولة كل 3 ثوان، ولا إخفاء للنافذة.

---

## المصفوفة

| البيئة | الجلسة | host الدرج | البروتوكول | المسار المتوقع | التغطية |
|---|---|---|---|---|---|
| KDE Plasma | Wayland / X11 | plasmashell | SNI | Qt | يلزم جهاز/VM |
| GNOME | Wayland | AppIndicator extension | SNI (+XEmbed legacy) | Qt | ✅ فحص حي + بصري (Wayland 46) |
| GNOME | Xorg | AppIndicator extension | SNI (+XEmbed legacy) | Qt | probe جاهز |
| GNOME بدون extension | Wayland | — | — | None | ✅ فحص حي (GNOME 46) |
| GNOME بدون extension | Xorg | — | — | None | متوقع: لا أيقونة، إغلاق = خروج |
| XFCE | X11 | xfce4-panel systray | XEmbed (وSNI مع `xfce4-statusnotifier-plugin`) | Qt | محاكى في e2e |
| XFCE (Mint) | X11 | xapp-status-plugin | XApp | XApp | ✅ فحص حي (هذا الجهاز) |
| Cinnamon | X11 | xapp-sn-watcher + applet | SNI | Qt | يلزم جهاز/VM |
| MATE | X11 | notification area (XEmbed) أو xapp/applet | XEmbed / SNI / XApp | Qt ثم XApp | probe جاهز |
| LXQt | X11 / Wayland | lxqt-panel | SNI (وXEmbed قديمًا) | Qt | يلزم جهاز/VM |
| Budgie | Wayland / X11 | budgie-panel | SNI | Qt | يلزم جهاز/VM |
| COSMIC | Wayland | cosmic-panel | SNI | Qt | يلزم جهاز/VM |
| Pantheon | X11 | wingpanel | SNI | Qt | يلزم جهاز/VM |
| i3 / Openbox / bspwm | X11 | stalonetray / trayer / tint2 | XEmbed | Qt | محاكى في e2e |
| sway / Hyprland | Wayland | waybar | SNI | Qt | يلزم جهاز/VM |
| بدون host | أي | — | — | None | e2e |

---

## التغطية المخبرية الحالية (2026-10-19)

```bash
python3 -m pytest tests/test_tray_backends.py tests/test_tray.py -q   # 34 passed
bash scripts/e2e-tray-envs.sh                                        # 14 checks, rc=0
```

| السيناريو | المحاكي | الفحوص |
|---|---|---|
| no-host | ناقل خاص بلا watcher/monitor | 1 |
| xapp | `org.x.StatusIconMonitor.e2e` | 6 |
| sni | Xephyr + watcher DBus | 4 |
| **xembed** | Xephyr + `scripts/e2e-tray-xembed.py` (libX11 عبر ctypes) | 3 |

- سيناريو XEmbed الجديد: المدير يملك `_NET_SYSTEM_TRAY_S0`، يعلن نفسه برسالة
  `MANAGER`، ويستقبل طلب `_NET_SYSTEM_TRAY_OPCODE` (dock) من Qt — أي أن مسار
  XEmbed الكامل مُثبت، وليس الكشف فقط.
- لا سيناريو Wayland آلي بعد (يلزم compositor هيدلس: weston/labwc).

### فحص حي في جلسة المستخدم الحقيقية (XFCE Mint X11، 2026-10-19)

`python3 scripts/tray-probe.py` في الجلسة الفعلية أنتج:

```
qt-platform=xcb  qt_reports=False  sni_watcher=False  xembed-owner=(none)
checks=... xapp_monitor=True xapp_runtime=True
detect=xapp
```

- اللوحة تشغّل `libxapp-status-plugin.so` وتملك `org.x.StatusIconMonitor.wrapper_2_0_0`
  (مالك حقيقي: pid 1516)، فعلى هذه الجلسة المسار **XApp** وليس XEmbed/Qt.
- `org.x.StatusIcon.tray_py` ملك `mintreport-tray` (تطبيق نظام Mint) — ليس منا؛
  أسماءنا لا تتصادم: التطبيق يسجّل `org.x.StatusIcon.athan<pid>` والـmock يستخدم
  `org.x.StatusIconMonitor.e2e`.
- لا بقايا عمليات من الـharness على الجلسة الحقيقية (pgrep نظيف).
- **فحص حي للتسجيل الفعلي**: `python3 scripts/tray-probe.py --live 8` →
  `live: backend=xapp` و`live-hosted=True` و`rc=0` — أي أن مسار XApp سجّل الأيقونة
  فعلًا في لوحة XFCE الحقيقية (ظهرت أيقونة مؤقتة 8 ثوانٍ ثم أُزيلت).
- **تفاعل مؤكد ميدانيًا**: `--live 20` أنتج `EVENT menu-requested` (نقرة يمين) →
  قائمة XApp تصل من اللوحة إلى الـbackend، و`live-done hosted=True`.

### GNOME Wayland 46 — جلسة حقيقية (2026-10-21)

بلا إضافة AppIndicator: `detect=none` ولا أيقونة ولا إخفاء وهمي ✅. أُثبت بمحاكي
watcher داخل الجلسة: التقاط مؤجل (~2 ثانية عبر retry)، تسجيل عنصر SNI كامل
(`/StatusNotifierItem` + قائمة `GetLayout` سليمة بالعربية)، فقدان watcher مرتين →
watchdog يعيد البناء بلا انهيار، وعودته → `System tray ready` ثانيةً. `Activate`
بلا خطأ. XWayland: `detect=none` بلا إيجابية كاذبة. تفاصيل الأدلة الكاملة:
`docs/dev/WAYLAND-NOTES.md` (قسم التحقق التنفيذي).

**مع الإضافة** (`gnome-shell-extension-appindicator 58`): بعد خروج/دخول، قشرة GNOME
تملك الـwatcher → `detect=qt`, `live-hosted=True`، الأيقونة ظهرت في الشريط العلوي،
القائمة العربية تعمل، close-to-tray يُخفي والعملية تبقى، `Activate` يعيد النافذة،
و"خروج" ينهي التطبيق — كلها مؤكدة حيًّا (2026-10-21). التلميحات غير مدعومة من
الإضافة (مقصود). صيغة عنصر الـwatcher للاتصالات الفريدة: `:1.x@/StatusNotifierItem`.

---

## التحقق على GNOME (X11/Wayland) وMATE (X11) — بيئات المستخدم

لا حاجة لتثبيت كل البيئات؛ شغّل الأداة داخل كل جلسة وأرسل الناتج:

```bash
python3 scripts/tray-probe.py             # فحص ثابت: الناقل + Qt + XEmbed (بلا أيقونة)
python3 scripts/tray-probe.py --live 20   # أيقونة حقيقية 20 ثانية + أحداث النقر/القائمة
./run.sh                                  # التطبيق الكامل بعد نجاح الـprobe
```

يسار = Activate، ويمين = القائمة (على SNI ترسمها القشرة عبر DBusMenu، وعلى XEmbed يرسمها Qt).

| البيئة | watcher | xembed-owner | detect | الأيقونة |
|---|---|---|---|---|
| GNOME + AppIndicator extension (X11/Wayland) | ✅ | قد يوجد (legacy) | qt | تظهر |
| GNOME بلا extension (X11) | ❌ | ❌ | none | لا تظهر (إغلاق = خروج) |
| GNOME بلا extension (Wayland) | ❌ | — | none | لا تظهر (إغلاق = خروج) |
| MATE بنقطة الإشعارات | ❌ غالبًا | ✅ | qt | تظهر |
| MATE + SNI مفعّل أو xapp status applet | ✅ | ✅ | qt (أو xapp) | تظهر |

ملاحظات مؤكدة من المصادر:

- **GNOME**: الإضافة `gnome-shell-extension-appindicator` (Ubuntu/Fedora) هي التي تنفّذ
  `org.kde.StatusNotifierWatcher` + أيقونات XEmbed القديمة؛ بدونه لا توجد أي أيقونة درج في
  GNOME. الإضافة **لا تدعم التلميحات** — معلومات الصلاة تُقرأ من عنصر القائمة.
- **MATE**: نقطة الإشعارات في `mate-panel` توفّر XEmbed دائمًا على X11، وSNI منها اختياري
  عبر مفتاح `org.mate.panel enable-sni-support` (غالبًا معطّل افتراضيًا). `xapp-sn-watcher`
  يملك `org.kde.StatusNotifierWatcher` لكن قائمة `status-notifier-enabled-desktops`
  الافتراضية لا تتضمن MATE. النتيجة: XEmbed هو المسار المتوقع على MATE الافتراضي.
- XFCE: `xapp-sn-watcher` لا يبدأ على XFCE إطلاقًا (`XDG_CURRENT_DESKTOP=XFCE`)، لذا
  المسار هناك XEmbed أو `xfce4-statusnotifier-plugin` إن ثُبّت.

---

## checklist موحّد لكل بيئة

- [ ] الأيقونة تظهر بعد الإقلاع (أو لا تُخفى النافذة عند غياب host).
- [ ] tooltip يعرض الصلاة التالية ويتحدث.
- [ ] القائمة: إظهار النافذة، الودجة المصغرة، معلومات الصلاة، خروج.
- [ ] اتجاه RTL للقائمة العربية.
- [ ] نقرة يسار تعيد النافذة؛ يمين تفتح القائمة.
- [ ] وميض الأيقونة وقت الأذان يعود لطبيعته (IconName/IconPixmap).
- [ ] الإشعارات تصل (Qt SNI → `org.freedesktop.Notifications`).
- [ ] إعادة تشغيل اللوحة/فقدان host → `_tray_watchdog` (10 ثوان) يعيد البناء.
- [ ] تغيير اللغة → `_retranslate_tray` يحدّث نصوص القائمة.
- [ ] الإغلاق مع host = إخفاء؛ بدونه = خروج فعلي.

---

## ملاحظات بروتوكولية

- **SNI**: Qt 6.11 يسجّل العنصر باسم الاتصال الفريد (`:1.x`) على المسار
  `/StatusNotifierItem`، وليس باسم `org.kde.StatusNotifierItem-*`. القائمة تصل عبر
  DBusMenu. أسماء الـwatcher: `org.kde.StatusNotifierWatcher` (KDE/GNOME ext/sway).
  المواصفة الحديثة عند freedesktop سمّت الخدمة `org.freedesktop.StatusNotifierWatcher`،
  لكن Qt 6 لا يزال يتحقق من `org.kde.StatusNotifierWatcher` وكل المضيفين الفعليين يملكون
  اسم org.kde — لذلك البوابة تفحص org.kde فقط (فحص org.freedesktop يعطي إيجابية كاذبة).
- **تغليف مستقبلي**: نسخة AppImage الحالية بلا صندوق فلا حاجة لصلاحيات. إذا صار Flatpak
  لاحقًا فأضف `--talk-name=org.kde.StatusNotifierWatcher` وإلا فشل SNI داخل الصندوق.
- **XEmbed**: خاص بـX11 فقط؛ القائمة `QMenu` محلية، والتلميح/الإشعارات عبر نوافذ Qt.
  يعتمد على امتلاك selection `_NET_SYSTEM_TRAY_S<screen>` ورسالة `MANAGER` (ICCCM).
- **XApp**: `org.x.StatusIconMonitor` + `org.x.StatusIcon.<name>`؛ النقر يمينًا يفتح
  القائمة يدويًا عبر `QCursor.pos()` — صالح لـX11 فقط.
- **Wayland**: لا XEmbed؛ البوابة تشترط watcher. التفاصيل والتحقق: `WAYLAND-NOTES.md`.

---

## أوامر فحص سريعة في أي بيئة

```bash
echo "$XDG_SESSION_TYPE / $WAYLAND_DISPLAY / $QT_QPA_PLATFORM"
python3 scripts/tray-probe.py            # فحص ثابت: الناقل + Qt + XEmbed
python3 scripts/tray-probe.py --live 20  # أيقونة حقيقية + أحداث النقر/القائمة
busctl --user list | grep -iE 'statusnotifier|statusicon'
QT_LOGGING_RULES="qt.qpa.*=true" ./run.sh 2>&1 | tee /tmp/athan-tray.log
# في السجل: "System tray ready (qt backend)" أو "No system tray host detected yet"
```

فحص يدوي اختياري على X11 حقيقي داخل Xephyr (لوحة XFCE فعلية بدل المحاكي):

```bash
Xephyr :93 -screen 1024x700 -noreset &
HOME=$(mktemp -d) DISPLAY=:93 dbus-run-session -- xfce4-panel &
```

---

## قائمة المتبقي قبل تغيير الجلسة (تسليم)

نُفّذت وثُبّتت: XFCE X11 (XApp حي)، GNOME Wayland بلا extension (كل السلوك الآلي)،
GNOME Wayland + AppIndicator extension (أيقونة/قائمة/إخفاء/Activate/خروج — بشري + آلي).

| # | البيئة | الأوامر | المتوقع |
|---|---|---|---|
| 1 | **MATE X11** | `python3 scripts/tray-probe.py` ثم `--live 20` | `xembed-owner=0x...` و`detect=qt` إن كانت نقطة الإشعارات مفعّلة؛ وSNI فقط إن فُعّل `org.mate.panel enable-sni-support`؛ و`detect=xapp` إن وُجد xapp status applet |
| 2 | **GNOME X11** | نفس الأمرين | مع الإضافة المثبّتة: `sni_watcher=True`, `detect=qt`, `live-hosted=True`؛ و`xembed-owner` قد يظهر أيضًا (legacy) |
| 3 | GNOME X11 بلا إضافة (اختياري) | تعطيل الإضافة ثم probe | `detect=none` وإغلاق = خروج |

مرئي متبقٍ (بعد توفر host):
- [ ] وميض الأيقونة وقت الأذان يعود لطبيعته.
- [ ] استعادة موضع الودجة على Wayland (لا يُستخدم `move` هناك).
- [ ] اتجاه RTL للقائمة العربية.
- [ ] وصول إشعار الأذان فعليًا (خدمة `org.freedesktop.Notifications` موجودة).

فجوة معروفة غير مغطاة آليًا:
- [ ] سيناريو XEmbed حيث يظهر المدير **بعد** رفض أول (host متأخر): يُختبر يدويًا أو بإضافة
      سيناريو في `scripts/e2e-tray-envs.sh` لاحقًا.

إغلاق الجلسة الحالية: لا تطبيق ولا محاكيات متروكة (تحقق `ps -C python3 -o cmd=`).
