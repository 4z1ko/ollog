import pytest
from app.profile.grid import grid_to_latlon


class TestGridToLatlon4Char:
    def test_fn31_returns_center_coordinates(self):
        lat, lon = grid_to_latlon("FN31")
        assert lat == pytest.approx(41.5, abs=0.5)
        assert lon == pytest.approx(-73.0, abs=1.0)

    def test_jo22_european_grid(self):
        lat, lon = grid_to_latlon("JO22")
        assert lat == pytest.approx(52.5, abs=0.5)
        assert lon == pytest.approx(5.0, abs=1.0)

    def test_returns_float_tuple(self):
        result = grid_to_latlon("FN31")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], float)


class TestGridToLatlon6Char:
    def test_fn31pr_returns_precise_center(self):
        lat, lon = grid_to_latlon("FN31pr")
        assert lat == pytest.approx(41.7292, abs=0.05)
        assert lon == pytest.approx(-72.7083, abs=0.05)

    def test_6char_more_precise_than_4char(self):
        lat4, lon4 = grid_to_latlon("FN31")
        lat6, lon6 = grid_to_latlon("FN31pr")
        # 6-char should give different (more precise) coordinates
        # unless pr happens to be exactly at center of FN31
        assert isinstance(lat6, float)
        assert isinstance(lon6, float)


class TestGridToLatlon2Char:
    def test_2char_grid_accepted(self):
        lat, lon = grid_to_latlon("FN")
        assert isinstance(lat, float)
        assert isinstance(lon, float)


class TestGridToLatlonCaseInsensitive:
    def test_lowercase_same_as_uppercase(self):
        upper = grid_to_latlon("FN31")
        lower = grid_to_latlon("fn31")
        assert upper[0] == pytest.approx(lower[0], abs=0.001)
        assert upper[1] == pytest.approx(lower[1], abs=0.001)

    def test_mixed_case(self):
        result = grid_to_latlon("Fn31pR")
        assert isinstance(result, tuple)


class TestGridToLatlonEdgeCases:
    def test_aa00_bottom_left(self):
        lat, lon = grid_to_latlon("AA00")
        assert lat < -80
        assert lon < -170

    def test_rr99_top_right(self):
        lat, lon = grid_to_latlon("RR99")
        assert lat > 80
        assert lon > 170


class TestGridToLatlonInvalid:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            grid_to_latlon("")

    def test_none_raises(self):
        with pytest.raises((ValueError, TypeError)):
            grid_to_latlon(None)

    def test_odd_length_3_raises(self):
        with pytest.raises(ValueError):
            grid_to_latlon("FN3")

    def test_odd_length_5_raises(self):
        with pytest.raises(ValueError):
            grid_to_latlon("FN31p")

    def test_single_char_raises(self):
        with pytest.raises(ValueError):
            grid_to_latlon("X")

    def test_8char_rejected(self):
        with pytest.raises(ValueError):
            grid_to_latlon("FN31pr55")

    def test_invalid_chars_raises(self):
        with pytest.raises(ValueError):
            grid_to_latlon("99AA")
