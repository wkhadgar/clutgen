"""
:file: conftest.py
:brief: Shared fixtures for CLUTGen test suite.
"""

import csv
import textwrap

import pytest

from src.sensor import VirtualSensor

RESOLUTION = 8  # small resolution for fast tests (256 entries)
MAX_RAW = 2**RESOLUTION

SIMPLE_SAMPLES = {
    0: 0,
    64: 32,
    128: 64,
    192: 96,
    255: 127,
}


@pytest.fixture
def simple_sensor():
    return VirtualSensor(SIMPLE_SAMPLES, resolution=RESOLUTION)


@pytest.fixture
def single_sample_sensor():
    return VirtualSensor({128: 64}, resolution=RESOLUTION)


@pytest.fixture
def two_sample_sensor():
    return VirtualSensor({0: 0, 255: 100}, resolution=RESOLUTION)


@pytest.fixture
def tmp_toml(tmp_path):
    """Creates a valid TOML + CSV pair and returns the TOML path."""
    csv_path = tmp_path / "samples.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["raw", "calibration"])
        for raw, cal in SIMPLE_SAMPLES.items():
            writer.writerow([raw, cal])

    toml_path = tmp_path / "sensor.toml"
    toml_path.write_text(
        textwrap.dedent(f"""\
            name = "test_sensor"
            description = "test sensor"
            table_resolution_bits = {RESOLUTION}
            lut_type = "int16_t"
            samples_csv = "samples.csv"
        """)
    )
    return toml_path


@pytest.fixture
def tmp_toml_with_method(tmp_path):
    """Creates a valid TOML with an explicit interpolation override."""
    csv_path = tmp_path / "samples.csv"
    csv_path.write_text("raw,calibration\n0,0\n255,100\n")
    toml_path = tmp_path / "sensor.toml"
    toml_path.write_text(
        textwrap.dedent(f"""\
            name = "test_sensor"
            description = "test sensor"
            table_resolution_bits = {RESOLUTION}
            lut_type = "int16_t"
            samples_csv = "samples.csv"
            interpolation = "splines"
        """)
    )
    return toml_path


@pytest.fixture
def tmp_second_toml(tmp_path):
    """Creates a second valid TOML + CSV pair for multi-sensor tests."""
    csv_path = tmp_path / "pressure.csv"
    csv_path.write_text("raw,calibration\n0,0\n255,100\n")
    toml_path = tmp_path / "pressure.toml"
    toml_path.write_text(
        textwrap.dedent(f"""\
            name = "pressure_sensor"
            description = "pressure"
            table_resolution_bits = {RESOLUTION}
            lut_type = "uint16_t"
            samples_csv = "pressure.csv"
        """)
    )
    return toml_path
