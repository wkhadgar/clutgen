# CLUTGen

CLUTGen automates the creation of **Look-Up Tables** for embedded systems, converting raw ADC readings into calibrated physical units such as temperature, pressure, or distance.

Given a set of calibration samples, CLUTGen fits an interpolation curve and generates a production-ready `.c`/`.h` pair with the full LUT precomputed for every possible ADC reading.

> For Zephyr west module usage, see the [zephyr branch](https://github.com/wkhadgar/clutgen/tree/zephyr).

---

## Requirements

* Python 3.10+
* `numpy`, `matplotlib`

---

## Installation

From PyPI:

```bash
pip install clutgen
```

From source:

```bash
pip install .
```

---

## Usage

```
clutgen [OPTIONS] input_files...
```

| Argument | Description |
| :--- | :--- |
| `input_files` | One or more `.toml` configuration files |
| `-o`, `--output-dir` | Output directory for generated files (default: `./clutgenerated`) |
| `-n`, `--name` | Base name for the generated `.c`/`.h` files (default: `lookup_tables`) |
| `--preview` | Open an interactive matplotlib plot after generation |

**Interpolation method** (mutually exclusive, default: `--linear`):

| Flag | Method |
| :--- | :--- |
| `-l`, `--linear` | Linear interpolation |
| `-s`, `--splines` | Cubic spline interpolation |
| `-p`, `--polynomial` | Best-fit polynomial up to degree 7 |
| `-w`, `--piecewise` | Zero-order hold (step-like) |
| `-d`, `--idw` | Inverse Distance Weighting |

**Examples:**

```bash
# Generate with default linear interpolation
clutgen ./calibration/temperature.toml

# Generate with splines and open preview
clutgen --splines --preview ./calibration/temperature.toml ./calibration/pressure.toml

# Custom output directory and file name
clutgen -o ./src/generated -n sensor_luts ./calibration/temperature.toml
```

---

## TOML Configuration

Each sensor requires a TOML configuration file and a CSV with its calibration samples.

**CSV schema:**
```csv
raw,calibration
```

Where `raw` is the ADC reading and `calibration` is the expected output value at that reading.

**TOML schema:**
```toml
name = "temp_sensor"                # C identifier — used as <n>_lut in generated code
description = "ambient temperature" # Used in Doxygen comments and plot titles
table_resolution_bits = 12          # ADC resolution in bits (e.g., 12 → 4096 entries)
lut_type = "int16_t"                # C type for the generated array

samples_csv = "./data/temperature_samples.csv"  # Relative to this file, or absolute

# Optional
interpolation = "polynomial"        # Overrides the CLI interpolation method for this LUT
preview = true                      # Overrides the CLI --preview flag for this LUT
```

### Interpolation Methods

| Value | Description |
| :--- | :--- |
| `linear` | Linear interpolation between calibration points. Default. |
| `splines` | Cubic spline interpolation; smooth transitions between points. |
| `polynomial` | Best-fit polynomial up to degree 7; prone to oscillation with sparse data. |
| `piecewise` | Zero-order hold; constant value between points, step-like output. |
| `idw` | Inverse Distance Weighting; weighted average of all known points. |

---

## Output

For each run, CLUTGen produces two files:

* `<name>.h` — extern declarations with Doxygen comments, safe to include anywhere in the project
* `<name>.c` — full LUT definitions, compiled once and linked

Each configured sensor produces an array named `<n>_lut`, where `n` is the `name` field from the TOML:

```c
#include "lookup_tables.h"

int val = temp_sensor_lut[adc_reading];
```

If `--preview` is set (or `preview = true` in a TOML), an additional `preview/` subdirectory is created inside the output directory containing a `.png` plot for each sensor.
