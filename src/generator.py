"""
:file: generator.py
:author: Paulo Santos (@wkhadgar)
:brief: Look-up Table generation base.
:version: 0.1
:date: 23-02-2026

:copyright: Copyright (c) 2026
"""

from __future__ import annotations

import csv
import datetime
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tomllib

LUT_LINE_WIDTH = 95


class GenMethod(Enum):
    LINEAR = "linear"
    SPLINES = "splines"
    POLYNOMIAL = "polynomial"
    PIECEWISE = "piecewise"
    IDW = "idw"


@dataclass
class LUTConfig:
    code_name: str
    doc_name: str
    resolution: int
    output_type: str
    method: GenMethod
    preview: bool
    raw_values: tuple[str, ...]
    calibration_values: tuple[str, ...]


class VirtualSensor:
    def __init__(
        self,
        measure_dict: dict[int, int],
        *,
        resolution: int,
    ):
        """
        Creates a virtual sensor for simulation.

        :param measure_dict: Calibration measurement dictionary in the form [adc_raw:calibration].
        :param resolution: Resolution of the measurements made, in bits of precision.
        """
        self.resolution: int = resolution

        sanitized_dict = dict(sorted(measure_dict.items(), key=lambda item: item[0]))
        self.x = np.array(list(sanitized_dict.keys()))
        self.y = np.array(list(sanitized_dict.values()))

    def __get_best_fit_lms(self) -> list:
        """
        Generates a list of polynomial coefficients that best approximate the measurements.

        :return: List of polynomial coefficients, ordered from highest degree to lowest.
        """
        c, extra = np.polynomial.polynomial.polyfit(self.x, self.y, 1, full=True)
        minimal_dev = extra[0] if len(extra) > 0 else float("inf")
        best_coefficients: np.ndarray = c

        for deg in range(2, 8):
            if (len(self.x) <= deg + 1) or minimal_dev < 1e-10:
                break

            c, extra = np.polynomial.polynomial.polyfit(self.x, self.y, deg, full=True)
            residuals = extra[0] if len(extra) > 0 else float("inf")
            if residuals < minimal_dev:
                minimal_dev = residuals
                best_coefficients = c

        return list(reversed(best_coefficients))

    def data_gen(self, method: GenMethod, *, max_val: int, min_val: int) -> dict[int, int]:
        """
        Generates the interpolated points, based on the given method.

        :param method: Method of interpolation.
        :param max_val: Maximum interpolation value.
        :param min_val: Minimum interpolation value.
        :return: Dictionary mapping raw ADC values to interpolated LUT values.
        """
        max_raw = 2**self.resolution
        virtual_measures_span = range(0, max_raw)

        match method:
            case GenMethod.POLYNOMIAL:
                virtual_measures: dict[int, int] = {}
                coefficients = self.__get_best_fit_lms()
                degree = len(coefficients)
                for virtual_reading in virtual_measures_span:
                    out = (virtual_reading * coefficients[0]) + coefficients[1]
                    i = 2
                    while i < degree:
                        out = (out * virtual_reading) + coefficients[i]
                        i += 1
                    virtual_measures[virtual_reading] = int(
                        max(min(math.trunc(out), max_val), min_val)
                    )
                return virtual_measures

            case GenMethod.LINEAR:
                x = self.x
                y = self.y

                if self.x[0] != 0:
                    x = np.append([0], x)
                    y = np.append(y[0], y)
                if self.x[-1] != max_raw:
                    x = np.append(x, [max_raw])
                    y = np.append(y, y[-1])

                y_interp = np.interp(virtual_measures_span, x, y)
                return {
                    xi: int(max(min(math.trunc(yi), max_val), min_val))
                    for xi, yi in zip(virtual_measures_span, y_interp, strict=False)
                }

            case GenMethod.SPLINES:
                x = self.x
                y = self.y

                n = len(x)
                h = np.diff(x)

                A = np.zeros((n, n))
                B = np.zeros(n)
                A[0, 0] = 1
                A[-1, -1] = 1

                for i in range(1, n - 1):
                    A[i, i - 1] = h[i - 1] / 6
                    A[i, i] = (h[i - 1] + h[i]) / 3
                    A[i, i + 1] = h[i] / 6
                    B[i] = (y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1]

                M = np.linalg.solve(A, B)

                def interpolate(xi):
                    idx = np.searchsorted(x, xi, side='right') - 1
                    idx = np.clip(idx, 0, n - 2)

                    dx = x[idx + 1] - x[idx]
                    t = (xi - x[idx]) / dx

                    val = (
                        (M[idx] * (1 - t) ** 3 / 6 + M[idx + 1] * t**3 / 6) * dx**2
                        + (y[idx] - M[idx] * dx**2 / 6) * (1 - t)
                        + (y[idx + 1] - M[idx + 1] * dx**2 / 6) * t
                    )
                    return val

                return {
                    xi: int(max(min(math.trunc(interpolate(xi)), max_val), min_val))
                    for xi in virtual_measures_span
                }

            case GenMethod.PIECEWISE:
                indices = np.searchsorted(self.x, virtual_measures_span, side='right') - 1
                indices = np.clip(indices, 0, len(self.y) - 1)
                y_interp = self.y[indices]

                return {
                    xi: int(max(min(yi, max_val), min_val))
                    for xi, yi in zip(virtual_measures_span, y_interp, strict=True)
                }

            case GenMethod.IDW:
                virtual_measures: dict[int, int] = {}
                power = 2

                for xi in virtual_measures_span:
                    distances = np.abs(self.x - xi)

                    if np.any(distances == 0):
                        yi = self.y[np.argmin(distances)]
                    else:
                        weights = 1.0 / (distances**power)
                        yi = np.sum(weights * self.y) / np.sum(weights)

                    virtual_measures[xi] = int(max(min(int(yi), max_val), min_val))

                return virtual_measures


class LUTBuilder:
    def __init__(
        self,
        out_path: Path,
        sensor: VirtualSensor,
        *,
        output_type: str,
        method: GenMethod,
    ):
        """
        Builds C LUT strings from a virtual sensor's interpolated data.

        :param out_path: Output directory path.
        :param sensor: Virtual sensor to generate data from.
        :param output_type: C type used in the generated output.
        :param method: Interpolation method to use.
        """
        self.sensor = sensor
        self.var_size_bits: int = int(
            output_type.removeprefix("u").removeprefix("int").removesuffix("_t")
        )
        self.type_str = f"const {output_type}"
        self.out_dir = out_path
        self.preview_out_dir = None

        if output_type.startswith("u"):
            max_int = (2**self.var_size_bits) - 1
            min_int = 0
        else:
            max_int = (2 ** (self.var_size_bits - 1)) - 1
            min_int = -max_int

        self.interpolated_points = self.sensor.data_gen(method, max_val=max_int, min_val=min_int)

    def __get_lut_values_str(self) -> str:
        """
        Generates LUT values array based on previous measurements.

        :return: String representing the values the sensor read.
        """
        line_dim = 0
        output_str = ""

        for v in self.interpolated_points.values():
            current_temp_str = f"{v}, "

            if (line_dim + len(current_temp_str)) >= LUT_LINE_WIDTH:
                current_temp_str = "\n\t" + current_temp_str
                line_dim = 0

            output_str += current_temp_str
            line_dim += len(current_temp_str)

        return "{\n\t" + output_str + "\n};\n\n"

    def gen_table_preview_plot(self, preview_file_name: str, plot_title: str):
        """
        Saves a PNG plot preview of the interpolated points.

        :param preview_file_name: Name used for the image file (without extension).
        :param plot_title: Title of the generated preview plot.
        """
        if self.preview_out_dir is None:
            self.preview_out_dir = self.out_dir / "preview"
            self.preview_out_dir.mkdir(exist_ok=True, parents=True)

        self.preview_out_path = self.preview_out_dir / f"{preview_file_name}.png"

        fig, ax = plt.subplots(figsize=(15, 10), dpi=250)
        ax.set_title(plot_title.capitalize())
        ax.set_xlabel(f"ADC Value (scaled to {self.sensor.resolution} bits)")
        ax.set_ylabel("LUT Value (in calibration unit)")
        ax.scatter(self.sensor.x, self.sensor.y, c="r", s=10, zorder=3)
        ax.grid(visible=True, which="both")
        ax.plot(
            list(self.interpolated_points.keys()),
            list(self.interpolated_points.values()),
            c="b",
        )
        ax.legend(["Calibration values", "Calculated LUT"])
        fig.savefig(self.preview_out_path, bbox_inches='tight')
        plt.close(fig)

    def get_lut_definition(self, code_name: str) -> str:
        """
        Generates a syntactically correct C string for the .c file definition.

        :param code_name: Name used in the code for the generated LUT.
        :return: Formatted string for use in definition.
        """
        return (
            f"{self.type_str} {code_name}_lut[{2**self.sensor.resolution}] = "
            + self.__get_lut_values_str()
        )

    def get_lut_declaration(self, code_name: str, doc_name: str) -> str:
        """
        Generates a documented C declaration string for external use in code.

        :param code_name: Name used in the code for the generated LUT.
        :param doc_name: Natural language name for the generated LUT.
        :return: Formatted string for use in declaration.
        """
        docs = (
            "/**\n"
            f" * @brief LUT for {doc_name} measurements.\n"
            " *\n"
            f" * @note The value read by the ADC is scaled to {self.sensor.resolution} bits "
            f"(0 to {(2**self.sensor.resolution) - 1}), and used as an index for this LUT.\n"
            " */"
        )
        return docs + f"\nextern {self.type_str} {code_name}_lut[{2**self.sensor.resolution}];\n\n"


def _parse_toml_config(
    gen_toml: Path, default_method: GenMethod, gen_preview: bool
) -> LUTConfig | None:
    """
    Parses a single TOML config file and its associated CSV.

    :param gen_toml: Path to the TOML config file.
    :param default_method: Fallback interpolation method if not specified in TOML.
    :param gen_preview: Fallback preview flag if not specified in TOML.
    :return: Parsed LUTConfig, or None if the config is invalid.
    """
    with open(gen_toml, "rb") as toml:
        lut_descriptor = tomllib.load(toml)

    code_name: str = lut_descriptor["name"]
    doc_name: str = lut_descriptor["description"]
    resolution: int = int(lut_descriptor["table_resolution_bits"])
    output_type: str = lut_descriptor["lut_type"]
    samples: Path = Path(lut_descriptor["samples_csv"])
    overwrite_method = lut_descriptor.get("interpolation", default_method.value)
    preview = lut_descriptor.get("preview", gen_preview)

    if samples.suffix != ".csv":
        print(f"-- Invalid samples file '{samples}' for {code_name}. Must be a CSV.")
        return None

    try:
        path = (gen_toml.parent / samples).resolve(strict=True)
    except FileNotFoundError:
        try:
            path = samples.resolve(strict=True)
        except FileNotFoundError:
            print(f"-- CSV not found for {code_name}: '{samples}'")
            return None

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        csv_header = next(reader)
        if csv_header[0] != "raw" or csv_header[1] != "calibration":
            print(f"-- {path} schema must be: 'raw,calibration'. Skipping.")
            return None
        raw_values, calibration_values = zip(*list(reader), strict=True)

    return LUTConfig(
        code_name=code_name,
        doc_name=doc_name,
        resolution=resolution,
        output_type=output_type,
        method=GenMethod(overwrite_method),
        preview=preview,
        raw_values=raw_values,
        calibration_values=calibration_values,
    )


def generate(
    in_files: list[Path], out_dir: Path, filename: str, method: GenMethod, gen_preview: bool
):
    out_path_c = out_dir / (filename + ".c")
    out_path_h = out_dir / (filename + ".h")

    header_h = (
        "/**\n"
        f" * @file {filename}.h\n"
        " * @brief Organizes lookup tables to speed up sensor readings.\n"
        " * @author CLUTGen <github.com/wkhadgar/clutgen>\n"
        " * @note The code in this file is generated and should not be modified.\n"
        " * @version 0.1\n"
        f" * @date {datetime.datetime.now().strftime('%d-%m-%Y')}\n"
        " *\n"
        " */\n"
        "\n"
        f"#ifndef {filename.upper()}_H\n"
        f"#define {filename.upper()}_H\n"
        "\n"
        "#include <stdint.h>\n\n"
    )

    footer = f"\n#endif /* {filename.upper()}_H */\n"

    header_c = (
        "/**\n"
        f" * @file {filename}.c\n"
        " * @brief Defines lookup tables to speed up sensor readings.\n"
        " * @author CLUTGen <github.com/wkhadgar/clutgen>\n"
        " * @note The code in this file is generated and should not be modified.\n"
        " * @version 0.1\n"
        f" * @date {datetime.datetime.now().strftime('%d-%m-%Y')}\n"
        " *\n"
        " */\n"
        "\n"
        f'#include "{filename}.h"\n\n'
    )

    print("-- Running scripts to generate LUTs")

    calibration_data_tomls = [f.resolve(strict=True) for f in in_files if f.suffix == ".toml"]

    if not calibration_data_tomls:
        print("-- No configuration TOMLs found.")
        return

    luts_c = []
    luts_h = []

    for gen_toml in calibration_data_tomls:
        config = _parse_toml_config(gen_toml, method, gen_preview)
        if config is None:
            continue

        sensor = VirtualSensor(
            {
                int(raw): int(val)
                for raw, val in zip(config.raw_values, config.calibration_values, strict=True)
            },
            resolution=config.resolution,
        )

        print(f"-- Generating {config.code_name} LUT...")
        builder = LUTBuilder(out_dir, sensor, output_type=config.output_type, method=config.method)
        luts_c.append(builder.get_lut_definition(code_name=config.code_name))
        luts_h.append(
            builder.get_lut_declaration(code_name=config.code_name, doc_name=config.doc_name)
        )

        if config.preview:
            builder.gen_table_preview_plot(
                preview_file_name=config.code_name, plot_title=config.doc_name
            )

    out_dir.mkdir(exist_ok=True, parents=True)

    with open(out_path_c, "w", encoding="utf8") as out:
        print(f"-- Generating source {filename}.c...")
        out.write(header_c)
        for lut in luts_c:
            out.write(lut)

    with open(out_path_h, "w", encoding="utf8") as out:
        print(f"-- Generating header {filename}.h...")
        out.write(header_h)
        for lut in luts_h:
            out.write(lut)
        out.write(footer)

    print("-- LUTs generated successfully.")
