Name:           athan-five-times
Version:        0.3.0b1
Release:        1%{?dist}
Summary:        Islamic prayer times with azan audio and adhkar
License:        GPL-3.0-or-later
URL:            https://github.com/HtoZ27/Athan-Five-Times
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
Requires:       python3 >= 3.10
Requires:       python3-pyside6-core python3-pyside6-gui python3-pyside6-widgets
Requires:       python3-pyside6-qml python3-pyside6-quick python3-pyside6-quickcontrols2
Requires:       python3-pyside6-svg libnotify
# Prayer calculation (adhan) and audio decoding (miniaudio) come from PyPI:
#   pip install adhan miniaudio

%description
Desktop prayer-times application with streaming azan audio, a structured
adhkar library, system-tray integration, do-not-disturb automation and
17 interface languages. Built with PySide6/Qt6.

%prep
%autosetup -n Athan-Five-Times-%{version}

%build
# Pure Python + QML, nothing to compile.

%install
install -d %{buildroot}%{_datadir}/athan-five-times
cp -a backend qml assets %{buildroot}%{_datadir}/athan-five-times/
find %{buildroot}%{_datadir}/athan-five-times -type d -name __pycache__ -prune -exec rm -rf {} +
install -Dm755 packaging/common/athan-five-times %{buildroot}%{_bindir}/athan-five-times
install -Dm644 packaging/common/com.azanprayer.app.desktop \
  %{buildroot}%{_datadir}/applications/com.azanprayer.app.desktop
install -Dm644 assets/kaaba.svg \
  %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/com.azanprayer.app.svg
install -Dm644 LICENSE %{buildroot}%{_docdir}/%{name}/LICENSE

%files
%{_bindir}/athan-five-times
%{_datadir}/athan-five-times/
%{_datadir}/applications/com.azanprayer.app.desktop
%{_datadir}/icons/hicolor/scalable/apps/com.azanprayer.app.svg
%{_docdir}/%{name}/LICENSE

%changelog
* Tue Oct 13 2026 H.Z.Tun <htoz27@users.noreply.github.com> - 0.3.0b1-1
- Initial RPM packaging.
