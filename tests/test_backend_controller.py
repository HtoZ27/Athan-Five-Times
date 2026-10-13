from backend.backend_controller import _ensure_country_data


class TestEnsureCountryData:
    def test_loads_tuple(self):
        result = _ensure_country_data()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_contains_methods(self):
        methods, countries, cities = _ensure_country_data()
        assert isinstance(methods, dict)
        assert "TN" in methods

    def test_contains_countries(self):
        _, countries, _ = _ensure_country_data()
        assert isinstance(countries, dict)
        assert "TN" in countries
        assert "US" in countries

    def test_contains_cities(self):
        _, _, cities = _ensure_country_data()
        assert isinstance(cities, dict)
        assert "TN" in cities
        assert len(cities["TN"]) > 0
        assert isinstance(cities["TN"][0], tuple)
        assert len(cities["TN"][0]) == 3
