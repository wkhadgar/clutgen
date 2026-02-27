"""
:file: sensor.py
:author: Paulo Santos (@wkhadgar)
:brief: Virtual sensor model and interpolation methods.
:version: 0.1
:date: 27-02-2026

:copyright: Copyright (c) 2026
"""

from __future__ import annotations

import math

import numpy as np

from src.config import GenMethod


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
                x = self.x.copy()
                y = self.y.copy()
                if x[0] != 0:
                    x = np.append([0], x)
                    y = np.append([y[0]], y)
                if x[-1] != max_raw:
                    x = np.append(x, [max_raw])
                    y = np.append(y, y[-1])

                y_interp = np.interp(virtual_measures_span, x, y)
                return {
                    xi: int(max(min(math.trunc(yi), max_val), min_val))
                    for xi, yi in zip(virtual_measures_span, y_interp, strict=False)
                }

            case GenMethod.SPLINES:
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
