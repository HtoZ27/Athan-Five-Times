"""Tests for Islamic calendar events, reminders (repeat days) and the compact
desktop widget settings introduced alongside the Salatuk parity work."""

import os
from datetime import date, datetime, timedelta

import pytest

from backend import reminders
from backend.islamic_events import events_for_date, primary_event
from backend.hijri import gregorian_to_hijri


def _events_by_hijri(start: date, end: date) -> dict:
    """Map (hijri_year, month, day) -> event list by scanning Gregorian dates."""
    out: dict = {}
    d = start
    while d <= end:
        y, m, day = gregorian_to_hijri(d)
        out[(y, m, day)] = events_for_date(d)
        d += timedelta(days=1)
    return out


@pytest.fixture(scope="module")
def calendar_events():
    return _events_by_hijri(date(2025, 1, 1), date(2027, 6, 30))


@pytest.fixture(autouse=True)
def fresh_settings_cache():
    """The settings module caches by version; conftest swaps SETTINGS_FILE per
    test, so drop the cache to keep engines isolated from each other."""
    import backend.settings as S

    S.invalidate_cache()
    yield
    S.invalidate_cache()


class TestIslamicEvents:
    def test_hijri_new_year(self, calendar_events):
        evs = calendar_events.get((1447, 1, 1), [])
        assert any("الهجرة" in e for e in evs)

    def test_ashura(self, calendar_events):
        evs = calendar_events.get((1447, 1, 10), [])
        assert "عاشوراء" in evs

    def test_white_days(self, calendar_events):
        for day in (13, 14, 15):
            assert "الأيام البيض" in calendar_events.get((1447, 2, day), [])

    def test_mawlid_removed(self, calendar_events):
        evs = calendar_events.get((1447, 3, 12), [])
        assert not any("مولد" in e for e in evs)

    def test_mid_shaban_night(self, calendar_events):
        evs = calendar_events.get((1447, 8, 14), [])
        assert any("النصف من شعبان" in e for e in evs)

    def test_mid_ramadan(self, calendar_events):
        assert any("النصف من رمضان" in e for e in calendar_events.get((1447, 9, 14), []))
        assert "النصف من رمضان" in calendar_events.get((1447, 9, 15), [])

    def test_ramadan_decades(self, calendar_events):
        evs = calendar_events.get((1447, 9, 12), [])
        assert any("العشر الثانية" in e for e in evs)
        evs = calendar_events.get((1447, 9, 25), [])
        assert any("العشر الأواخر" in e for e in evs)

    def test_laylat_al_qadr_nights(self, calendar_events):
        for day in (21, 23, 27, 29):
            assert "ليلة القدر" in calendar_events.get((1447, 9, day), [])

    def test_eid_al_fitr_days(self, calendar_events):
        assert any("عيد الفطر" in e for e in calendar_events.get((1447, 10, 1), []))
        assert any("عيد الفطر" in e for e in calendar_events.get((1447, 10, 2), []))

    def test_hajj_days(self, calendar_events):
        assert "يوم التروية" in calendar_events.get((1447, 12, 8), [])
        assert "يوم عرفة" in calendar_events.get((1447, 12, 9), [])
        assert any("عيد الأضحى" in e for e in calendar_events.get((1447, 12, 10), []))
        for day in (11, 12, 13):
            assert any("التشريق" in e for e in calendar_events.get((1447, 12, day), []))

    def test_ramadan_countdown(self, calendar_events):
        found = []
        for hday in range(1, 30):
            evs = calendar_events.get((1447, 8, hday), [])
            found.extend(e for e in evs if e.startswith("باقي"))
        assert found, "no Ramadan countdown events generated"
        assert any("1 يوم" in e or "يوم واحد" in e or "يوم على رمضان" in e for e in found)

    def test_primary_event_prefers_named_over_countdown(self):
        # On days with both a named event and a Ramadan countdown, the named
        # one wins; on countdown-only days the countdown is returned.
        countdown_only = None
        named_multi = None
        d = date(2025, 1, 1)
        while d <= date(2027, 6, 30) and (countdown_only is None or named_multi is None):
            evs = events_for_date(d)
            cd = [e for e in evs if e.startswith("باقي")]
            named = [e for e in evs if not e.startswith("باقي")]
            if cd and not named and countdown_only is None:
                countdown_only = d
            if cd and named and named_multi is None:
                named_multi = d
            d += timedelta(days=1)
        if countdown_only is not None:
            assert primary_event(countdown_only).startswith("باقي")
        if named_multi is not None:
            assert not primary_event(named_multi).startswith("باقي")


class TestRemindersDays:
    @pytest.fixture(autouse=True)
    def isolated_store(self, tmp_path, monkeypatch):
        store = tmp_path / "reminders.json"
        monkeypatch.setattr(reminders, "_storage_path", lambda: store)
        yield store

    def test_add_and_list(self):
        rec = reminders.add_reminder("أذكار الصباح", "06:30", [0, 2, 4])
        items = reminders.list_reminders()
        assert len(items) == 1
        assert items[0]["text"] == "أذكار الصباح"
        assert items[0]["time"] == "06:30"
        assert items[0]["days"] == [0, 2, 4]
        assert items[0]["enabled"] is True
        assert rec["id"] == items[0]["id"]

    def test_empty_days_means_daily(self):
        reminders.add_reminder("كل يوم", "12:00", [])
        for wd in range(7):
            base = datetime(2026, 10, 19, 12, 0)  # Monday
            now = base + timedelta(days=wd)
            assert len(reminders.due_reminders(now)) == 1, f"weekday {wd}"

    def test_days_filter(self):
        reminders.add_reminder("إثنين فقط", "07:00", [0])  # Monday
        monday = datetime(2026, 10, 19, 7, 0)   # weekday 0
        tuesday = datetime(2026, 10, 20, 7, 0)  # weekday 1
        assert len(reminders.due_reminders(monday)) == 1
        assert reminders.due_reminders(tuesday) == []

    def test_disabled_never_fires(self):
        rec = reminders.add_reminder("x", "08:00", [])
        reminders.toggle_reminder(rec["id"], False)
        assert reminders.due_reminders(datetime(2026, 10, 19, 8, 0)) == []

    def test_time_must_match_minute(self):
        reminders.add_reminder("y", "09:15", [])
        assert reminders.due_reminders(datetime(2026, 10, 19, 9, 14)) == []
        assert len(reminders.due_reminders(datetime(2026, 10, 19, 9, 15))) == 1

    def test_invalid_time_rejected(self):
        with pytest.raises(ValueError):
            reminders.add_reminder("z", "25:99", [])
        with pytest.raises(ValueError):
            reminders.add_reminder("z", "abc", [])

    def test_update_and_remove(self):
        rec = reminders.add_reminder("قبل", "05:00", [1])
        assert reminders.update_reminder(rec["id"], text="بعد", time_str="05:45", days=[3, 5])
        item = reminders.list_reminders()[0]
        assert item["text"] == "بعد"
        assert item["time"] == "05:45"
        assert item["days"] == [3, 5]
        assert reminders.remove_reminder(rec["id"]) is True
        assert reminders.list_reminders() == []
        assert reminders.remove_reminder("missing") is False

    def test_days_are_sanitised(self):
        rec = reminders.add_reminder("d", "10:00", [0, 9, -2, 6])
        assert reminders.list_reminders()[0]["days"] == [0, 6]
        reminders.update_reminder(rec["id"], days=[-1, 7])
        assert reminders.list_reminders()[0]["days"] == []


class TestWidgetBackend:
    def _engine(self):
        from backend.backend_controller import PrayerEngine

        return PrayerEngine()

    def test_widget_defaults_hidden(self):
        e = self._engine()
        assert e.isWidgetVisible() is False
        assert e.getWidgetGeometry() == [-1, -1]

    def test_widget_visibility_roundtrip_and_signal(self):
        e = self._engine()
        seen = []
        e.widgetVisibilityRequested.connect(lambda v: seen.append(bool(v)))
        e.setWidgetVisible(True)
        assert e.isWidgetVisible() is True
        assert seen == [True]
        e.setWidgetVisible(False)
        assert e.isWidgetVisible() is False
        assert seen == [True, False]

    def test_widget_geometry_roundtrip(self):
        e = self._engine()
        e.saveWidgetGeometry(321, 123)
        assert e.getWidgetGeometry() == [321, 123]

    def test_widget_progress_and_following(self):
        e = self._engine()
        e.recalculate()
        prog = e.getProgressToNext()
        assert 0.0 <= prog <= 1.0
        following = e.getFollowingPrayers()
        assert isinstance(following, list)
        assert 1 <= len(following) <= 2
        for item in following:
            assert set(item) == {"name", "time", "tomorrow"}
            assert item["name"] and item["time"]

    def test_widget_state_persists_across_engine_instances(self):
        e = self._engine()
        e.setWidgetVisible(True)
        e.saveWidgetGeometry(11, 22)
        e2 = self._engine()
        assert e2.isWidgetVisible() is True
        assert e2.getWidgetGeometry() == [11, 22]

    def test_reminder_slots_roundtrip(self, tmp_path, monkeypatch):
        store = tmp_path / "reminders.json"
        monkeypatch.setattr(reminders, "_storage_path", lambda: store)
        e = self._engine()
        assert e.addReminder("تذكير", "06:00", [1, 3]) is True
        items = e.getReminders()
        assert len(items) == 1
        rid = items[0]["id"]
        assert e.updateReminder(rid, "محدث", "06:30", [2]) is True
        updated = e.getReminders()[0]
        assert updated["text"] == "محدث"
        assert updated["days"] == [2]
        assert e.toggleReminder(rid, False) is True
        assert e.getReminders()[0]["enabled"] is False
        assert e.removeReminder(rid) is True
        assert e.getReminders() == []

    def test_background_mode_slows_clock(self):
        e = self._engine()
        assert e._clock_timer.interval() == 1000
        e.setBackgroundMode(True)
        assert e._clock_timer.interval() == 30000
        e.setBackgroundMode(False)
        assert e._clock_timer.interval() == 1000

    def test_visible_widget_keeps_clock_fast_in_background(self):
        # A visible compact widget shows a live countdown, so background mode
        # must not slow the engine clock down to 30 s while it is on screen.
        e = self._engine()
        e.setBackgroundMode(True)
        assert e._clock_timer.interval() == 30000
        e.setWidgetVisible(True)
        assert e._clock_timer.interval() == 1000
        e.setWidgetVisible(False)
        assert e._clock_timer.interval() == 30000
