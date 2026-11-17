"""City altitude map and its integration with the prayer engine."""

from datetime import date

from backend.city_altitudes import city_count, lookup
from backend.countries_data import COUNTRY_CITIES
from backend.prayer_calc import calculate
from backend.prayer_calc import _normalise_city as normalise_city


def _unique_city_keys():
    return {
        (country, normalise_city(name))
        for country, cities in COUNTRY_CITIES.items()
        for name, _lat, _lon in cities
    }


class TestCityAltitudeMap:
    def test_map_covers_every_unique_city(self):
        keys = _unique_city_keys()
        assert city_count() == len(keys)
        assert all(lookup(country, city) is not None for country, city in keys)

    def test_values_are_plausible_metres(self):
        keys = _unique_city_keys()
        values = [lookup(country, city) for country, city in keys]
        assert all(value is not None for value in values)
        assert all(-500.0 <= value <= 5000.0 for value in values)

    def test_known_highland_cities(self):
        assert lookup("MA", "marrakesh") == 457.0
        assert lookup("NP", "kathmandu") == 1296.0
        assert lookup("BO", "lapaz") == 3782.0
        assert lookup("MX", "mexicocity") == 2240.0

    def test_known_below_sea_level_city(self):
        assert lookup("XW", "jericho") == -233.0

    def test_unknown_city_returns_none(self):
        assert lookup("ZZ", "notacity") is None

    def test_static_cities_keep_their_geographic_altitude(self):
        # The static path has its own official altitude; the map keeps the
        # real-world value so it stays useful outside that path.
        assert lookup("CA", "windsor") == 190.0


class TestCityAltitudeIntegration:
    day = date(2026, 6, 21)

    def test_map_is_used_for_non_static_city(self):
        common = {
            "target_date": self.day,
            "method_name": "Morocco",
            "tz_name": "Africa/Casablanca",
        }
        via_map = calculate(
            31.6295,
            -7.9811,
            city_name="Marrakesh",
            country_code="MA",
            **common,
        )
        explicit = calculate(
            31.6295,
            -7.9811,
            city_name="Marrakesh",
            country_code="MA",
            altitude=457.0,
            **common,
        )
        assert via_map is not None and explicit is not None
        assert via_map.as_dict() == explicit.as_dict()

    def test_explicit_zero_bypasses_city_map(self):
        common = {
            "target_date": self.day,
            "method_name": "Morocco",
            "tz_name": "Africa/Casablanca",
        }
        via_map = calculate(
            31.6295,
            -7.9811,
            city_name="Marrakesh",
            country_code="MA",
            **common,
        )
        sea_level = calculate(
            31.6295,
            -7.9811,
            city_name="Marrakesh",
            country_code="MA",
            altitude=0.0,
            **common,
        )
        assert via_map is not None and sea_level is not None
        assert via_map.sunrise < sea_level.sunrise

    def test_static_table_altitude_wins_over_city_map(self):
        common = {
            "target_date": self.day,
            "method_name": "Iraq",
            "tz_name": "Asia/Baghdad",
        }
        # Dahuk is a static-table city whose official metadata has altitude 0,
        # while the geographic map has a real elevation for it.
        default = calculate(
            36.8667,
            42.95,
            city_name="Dahuk",
            country_code="IQ",
            **common,
        )
        zero = calculate(
            36.8667,
            42.95,
            city_name="Dahuk",
            country_code="IQ",
            altitude=0.0,
            **common,
        )
        high = calculate(
            36.8667,
            42.95,
            city_name="Dahuk",
            country_code="IQ",
            altitude=570.0,
            **common,
        )
        assert default is not None and zero is not None and high is not None
        assert default.as_dict() == zero.as_dict()
        assert default.sunrise != high.sunrise

    def test_explicit_altitude_overrides_static_table(self):
        common = {
            "target_date": self.day,
            "method_name": "Iraq",
            "tz_name": "Asia/Baghdad",
        }
        default = calculate(
            33.3152,
            44.3661,
            city_name="Baghdad",
            country_code="IQ",
            **common,
        )
        explicit = calculate(
            33.3152,
            44.3661,
            city_name="Baghdad",
            country_code="IQ",
            altitude=500.0,
            **common,
        )
        assert default is not None and explicit is not None
        assert default.sunrise != explicit.sunrise

    def test_negative_altitude_is_inert(self):
        common = {
            "target_date": self.day,
            "method_name": "Palestine",
            "tz_name": "Asia/Hebron",
        }
        via_map = calculate(
            31.85,
            35.45,
            city_name="Jericho",
            country_code="XW",
            **common,
        )
        zero = calculate(
            31.85,
            35.45,
            city_name="Jericho",
            country_code="XW",
            altitude=0.0,
            **common,
        )
        assert via_map is not None and zero is not None
        assert via_map.as_dict() == zero.as_dict()

    def test_unknown_city_behaves_like_zero(self):
        common = {
            "target_date": self.day,
            "method_name": "Morocco",
            "tz_name": "Africa/Casablanca",
        }
        unknown = calculate(
            31.6295,
            -7.9811,
            city_name="No Such Place",
            country_code="MA",
            **common,
        )
        zero = calculate(
            31.6295,
            -7.9811,
            city_name="No Such Place",
            country_code="MA",
            altitude=0.0,
            **common,
        )
        assert unknown is not None and zero is not None
        assert unknown.as_dict() == zero.as_dict()
