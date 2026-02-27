"""
:file: test_config.py
:brief: Tests for GenMethod enum and LUTConfig dataclass.
"""

import pytest

from src.config import GenMethod, LUTConfig


class TestGenMethod:
    def test_all_methods_have_string_values(self):
        for method in GenMethod:
            assert isinstance(method.value, str)

    def test_from_string(self):
        assert GenMethod("linear") == GenMethod.LINEAR
        assert GenMethod("splines") == GenMethod.SPLINES
        assert GenMethod("polynomial") == GenMethod.POLYNOMIAL
        assert GenMethod("piecewise") == GenMethod.PIECEWISE
        assert GenMethod("idw") == GenMethod.IDW

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            GenMethod("unknown")

    def test_five_methods_defined(self):
        assert len(GenMethod) == 5


class TestLUTConfig:
    def test_fields_stored(self):
        config = LUTConfig(
            code_name="temp",
            description="temperature",
            resolution=12,
            output_type="int16_t",
            method=GenMethod.LINEAR,
            raw_values=("0", "255"),
            calibration_values=("0", "100"),
        )
        assert config.code_name == "temp"
        assert config.description == "temperature"
        assert config.resolution == 12
        assert config.output_type == "int16_t"
        assert config.method == GenMethod.LINEAR
        assert config.raw_values == ("0", "255")
        assert config.calibration_values == ("0", "100")
