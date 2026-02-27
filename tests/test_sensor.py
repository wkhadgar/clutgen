"""
:file: test_sensor.py
:brief: Tests for VirtualSensor and all interpolation methods.
"""

import numpy as np
import pytest
from conftest import MAX_RAW, RESOLUTION, SIMPLE_SAMPLES

from src.config import GenMethod
from src.sensor import VirtualSensor


class TestVirtualSensor:
    def test_sorts_input(self):
        unsorted = {192: 96, 0: 0, 128: 64}
        sensor = VirtualSensor(unsorted, resolution=RESOLUTION)
        assert list(sensor.x) == sorted(unsorted.keys())

    def test_resolution_stored(self, simple_sensor):
        assert simple_sensor.resolution == RESOLUTION

    def test_does_not_mutate_on_linear(self, simple_sensor):
        x_before = simple_sensor.x.copy()
        y_before = simple_sensor.y.copy()
        simple_sensor.data_gen(GenMethod.LINEAR, max_val=127, min_val=-128)
        assert np.array_equal(simple_sensor.x, x_before)
        assert np.array_equal(simple_sensor.y, y_before)

    def test_single_sample_does_not_crash(self, single_sample_sensor):
        result = single_sample_sensor.data_gen(GenMethod.LINEAR, max_val=127, min_val=-128)
        assert len(result) == MAX_RAW


class TestDataGenCommon:
    @pytest.mark.parametrize("method", list(GenMethod))
    def test_output_has_correct_length(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert len(result) == MAX_RAW

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_keys_are_full_range(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert list(result.keys()) == list(range(MAX_RAW))

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_values_clamped_unsigned(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=255, min_val=0)
        assert all(0 <= v <= 255 for v in result.values())

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_values_clamped_signed(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert all(-128 <= v <= 127 for v in result.values())

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_values_are_integers(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=127, min_val=-128)
        assert all(isinstance(v, int) for v in result.values())

    @pytest.mark.parametrize("method", list(GenMethod))
    def test_extreme_clamping(self, simple_sensor, method):
        result = simple_sensor.data_gen(method, max_val=10, min_val=-10)
        assert all(-10 <= v <= 10 for v in result.values())


class TestDataGenLinear:
    def test_exact_at_calibration_points(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.LINEAR, max_val=127, min_val=-128)
        for raw, cal in SIMPLE_SAMPLES.items():
            assert result[raw] == cal

    def test_does_not_mutate_sensor(self, simple_sensor):
        x_before = simple_sensor.x.copy()
        simple_sensor.data_gen(GenMethod.LINEAR, max_val=127, min_val=-128)
        assert np.array_equal(simple_sensor.x, x_before)


class TestDataGenSplines:
    def test_two_points_does_not_crash(self, two_sample_sensor):
        result = two_sample_sensor.data_gen(GenMethod.SPLINES, max_val=127, min_val=-128)
        assert len(result) == MAX_RAW

    def test_output_length(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.SPLINES, max_val=127, min_val=-128)
        assert len(result) == MAX_RAW


class TestDataGenPolynomial:
    def test_two_points_uses_linear_fit(self, two_sample_sensor):
        result = two_sample_sensor.data_gen(GenMethod.POLYNOMIAL, max_val=127, min_val=-128)
        assert len(result) == MAX_RAW

    def test_output_length(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.POLYNOMIAL, max_val=127, min_val=-128)
        assert len(result) == MAX_RAW


class TestDataGenPiecewise:
    def test_exact_at_first_point(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.PIECEWISE, max_val=127, min_val=-128)
        assert result[0] == SIMPLE_SAMPLES[0]

    def test_holds_value_between_points(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.PIECEWISE, max_val=127, min_val=-128)
        # Between 0 and 64 should hold the value at 0
        assert result[32] == SIMPLE_SAMPLES[0]


class TestDataGenIDW:
    def test_exact_at_calibration_points(self, simple_sensor):
        result = simple_sensor.data_gen(GenMethod.IDW, max_val=127, min_val=-128)
        for raw, cal in SIMPLE_SAMPLES.items():
            assert result[raw] == cal

    def test_point_on_calibration_value(self):
        sensor = VirtualSensor({0: 0, 128: 50, 255: 100}, resolution=RESOLUTION)
        result = sensor.data_gen(GenMethod.IDW, max_val=127, min_val=-128)
        assert result[128] == 50
