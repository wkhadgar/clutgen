"""
:file: generator.py
:author: Paulo Santos (@wkhadgar)
:brief: Look-up Table generation base.
:version: 0.1
:date: 23-02-2026

:copyright: Copyright (c) 2026
"""

from __future__ import annotations

import datetime
import math
import sys
from enum import Enum
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


class GenMethod(Enum):
    LINEAR = "l"
    SPLINE = "s"
    POLINOMIAL = "p"
    PIECEWISE = "w"


class VirtualSensor:
    def __init__(
        self,
        measure_dict: dict[int, int | float] | None = None,
        *,
        resolution: int,
    ):
        """
        Creates a virtual sensor for simulation.

        :param measure_dict: Calibration measurement dictionary in the form [adc_raw:calibration].
        :param resolution: Resolution of the measurements made, in bits of precision.
        :param generator: Optional data generator of type `foo(raw, resolution) -> val`
        """
        self.resolution: int = resolution

        if measure_dict is not None:
            self.x = np.array(list(measure_dict.keys()))
            self.y = np.array(list(measure_dict.values()))
            return

        raise ValueError(f"Unable to create virtual sensor with given data: {measure_dict}")

    def __get_best_fit_lms(self) -> list:
        """
        Generates a list of polynomial coefficients that best approximate the measurements.

        :return: List of polynomial coefficients, ordered from highest degree to lowest.
        """
        c, [residuals, _, _, _] = np.polynomial.polynomial.polyfit(self.x, self.y, 1, full=True)
        minimal_dev = residuals
        best_coefficients: np.ndarray = c
        for deg in range(2, 8):
            if (len(self.x) <= deg + 1) or minimal_dev < 1e-10:
                break

            c, [residuals, _, _, _] = np.polynomial.polynomial.polyfit(
                self.x, self.y, deg, full=True
            )
            if residuals < minimal_dev:
                minimal_dev = residuals
                best_coefficients = c

        return list(reversed(best_coefficients))

    def data_gen(self, method: GenMethod, *, max_val: int, min_val: int) -> dict[int, int]:
        max_raw = 2**self.resolution
        virtual_measures_span = range(0, max_raw)

        match method:
            case GenMethod.POLINOMIAL:
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
                if self.x[0] != 0:
                    self.x = np.append([0], self.x)
                    self.y = np.append(self.y[0], self.y)
                if self.x[-1] != max_raw:
                    self.x = np.append(self.x, [max_raw])
                    self.y = np.append(self.y, self.y[-1])

                y_interp = np.interp(virtual_measures_span, self.x, self.y)
                return {
                    xi: int(max(min(math.trunc(yi), max_val), min_val))
                    for xi, yi in zip(virtual_measures_span, y_interp, strict=False)
                }
            case GenMethod.SPLINE:
                x, y = self.x, self.y
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


class LUTStringify:
    def __init__(
        self,
        out_path: Path,
        sensor: VirtualSensor,
        *,
        output_type: str,
        method: GenMethod,
    ):
        """
        Creates an instance of a calibrated data generator based on a virtual sensor.

        :param sensor: Virtual sensor to be used or generation function.
        :param output_type: Type used in the generated output.
        """

        self.sensor = sensor
        self.var_size_bits: int = int(
            output_type.removeprefix("u").removeprefix("int").removesuffix("_t")
        )
        self.type_str = f"const {output_type}"
        self.preview_out_dir = out_path / "preview"
        self.preview_out_path = None
        self.method: GenMethod = method

        out_path.mkdir(exist_ok=True)
        self.preview_out_dir.mkdir(exist_ok=True)

        if output_type.startswith("u"):
            self.max_int = (2**self.var_size_bits) - 1
            self.min_int = 0
        else:
            self.max_int = (2 ** (self.var_size_bits - 1)) - 1
            self.min_int = -self.max_int

    def __get_lut_values_str(self):
        """
        Generates calibrated values based on previous measurements.

        :return: String representing the values the sensor read.
        """
        line_dim = 0
        output_str = ""

        table = self.sensor.data_gen(self.method, max_val=self.max_int, min_val=self.min_int)

        plt.figure(figsize=(15, 10), dpi=250)
        plt.scatter(self.sensor.x, self.sensor.y, c="r", s=10, zorder=3)
        plt.grid(visible=True, which="both")
        plt.plot(range(len(table)), list(table.values()), c="b")
        plt.legend(["Calibration values", "Calculated LUT"])
        plt.savefig(self.preview_out_path, bbox_inches='tight')

        for v in list(table.values()):
            current_temp_str = f"{v}, "

            if (line_dim + len(current_temp_str)) >= 95:
                current_temp_str = "\n\t" + current_temp_str
                line_dim = 0

            output_str += current_temp_str
            line_dim += len(current_temp_str)

        return "{\n\t" + output_str + "\n};\n\n"

    def get_lut_definition(self, code_name: str, doc_name: str):
        """
        Generates a syntactically correct C string for header assignment.

        :param code_name: Name used in the code for the generated LUT.
        :param doc_name: Natural language name for the generated LUT.
        :return: Formatted string for use in headers.
        """

        self.preview_out_path = self.preview_out_dir / code_name
        plt.close()
        plt.title(f"{doc_name.capitalize()}")
        plt.xlabel(f"ADC Value (scaled to {self.sensor.resolution} bits)")
        plt.ylabel("LUT Value (in calibration unit)")
        return (
            f"{self.type_str} {code_name}_lut[{2**self.sensor.resolution}] = "
            + self.__get_lut_values_str()
        )

    def get_lut_declaration(self, code_name: str, doc_name: str):
        docs = (
            "/**\n"
            f" * @brief LUT for {doc_name} measurements.\n"
            " *\n"
            f" * @note The value read by the ADC is scaled to {self.sensor.resolution} bits "
            f"(0 to {(2**self.sensor.resolution) - 1}), and used as an index for this LUT.\n"
            " */"
        )

        return docs + f"\nextern {self.type_str} {code_name}_lut[{2**self.sensor.resolution}];\n\n"


def main(in_files: list[str], filename: str, method: GenMethod):
    out_dir = Path("./generated_luts")
    out_include_dir = Path("./include")
    out_path_c = out_dir / (filename + ".c")
    out_path_h = out_include_dir / (filename + ".h")

    header_h = (
        "/**\n"
        f" * @file {filename}.h\n"
        " * @brief Organizes lookup tables to speed up sensor readings.\n"
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
        " * @note The code in this file is generated and should not be modified.\n"
        " * @version 0.1\n"
        f" * @date {datetime.datetime.now().strftime('%d-%m-%Y')}\n"
        " *\n"
        " */\n"
        "\n"
        f'#include "{filename}.h"\n\n'
    )

    print("-- Running scripts to generate LUTs")

    luts_c = []
    luts_h = []

    calibration_data_yamls: list[Path] = []
    for file in in_files:
        abs_file_path = Path(file).resolve()
        if file.endswith(".yml") or file.endswith(".yaml"):
            calibration_data_yamls.append(abs_file_path.resolve())

    if len(calibration_data_yamls) == 0:
        print("-- No configuration YAMLs found.")
        return

    for gen_yaml in calibration_data_yamls:
        with open(gen_yaml, encoding="utf8") as stream:
            lut_descriptor = yaml.safe_load(stream)

            code_name: str = lut_descriptor["name"]
            doc_name: str = lut_descriptor["description"]
            resolution: int = int(lut_descriptor["table_resolution_bits"])
            output_size_bits: str = lut_descriptor["lut_type"]
            generator: Path = Path(lut_descriptor["generator"])

            try:
                path = (gen_yaml.parent / generator).resolve(strict=True)
            except FileNotFoundError:
                path = generator.resolve(strict=True)

            if generator.suffix == ".csv":
                gen_data = pd.read_csv(path)
            elif generator.suffix in (".xls", ".xlsx", ".xlsm", ".xlsb", ".odf", ".ods", ".odt"):
                gen_data = pd.read_excel(path)
            else:
                print(f"Could not obtain generator for {code_name}\nCheck the table format.")
                sys.exit(1)

        sensor = VirtualSensor(
            {
                int(raw): int(val)
                for raw, val in zip(gen_data["raw"], gen_data["calibration"], strict=False)
            },
            resolution=resolution,
        )
        print(f"-- Generating {code_name} LUT based on '{path}'...")
        printer = LUTStringify(out_dir, sensor, output_type=output_size_bits, method=method)
        luts_c.append(printer.get_lut_definition(code_name=code_name, doc_name=doc_name))
        luts_h.append(printer.get_lut_declaration(code_name=code_name, doc_name=doc_name))

    out_dir.mkdir(exist_ok=True)
    out_include_dir.mkdir(exist_ok=True)

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
