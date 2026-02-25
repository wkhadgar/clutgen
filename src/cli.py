import argparse
from pathlib import Path

from src import generator as gen
from src.generator import GenMethod


def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "input_files",
        help="Configuration TOMLs for the LUT generation.",
        type=Path,
        nargs="+",
    )
    parser.add_argument(
        "-o",
        metavar="output/dir/",
        help="Output directory. Generated files will be added here.",
        type=Path,
        default=Path("./clutgenerated"),
    )
    parser.add_argument(
        "-n",
        "--name",
        metavar="name",
        help="Name of the generated LUT files.",
        default="lookup_tables",
    )
    parser.add_argument(
        "-v",
        "--preview",
        action="store_true",
        help="Generate preview plots for each generated LUT.",
    )

    method_group = parser.add_mutually_exclusive_group()
    parser.set_defaults(method=GenMethod.LINEAR)

    method_group.add_argument(
        "-l",
        f"--{GenMethod.LINEAR.value}",
        action="store_const",
        const=GenMethod.LINEAR,
        dest="method",
        help="Linear Interpolation generation method. [default]",
    )
    method_group.add_argument(
        "-s",
        f"--{GenMethod.SPLINES.value}",
        action="store_const",
        const=GenMethod.SPLINES,
        dest="method",
        help="Cubic Splines Interpolation generation method.",
    )
    method_group.add_argument(
        "-p",
        f"--{GenMethod.POLYNOMIAL.value}",
        action="store_const",
        const=GenMethod.POLYNOMIAL,
        dest="method",
        help="Polinomial Interpolation generation method.",
    )
    method_group.add_argument(
        "-w",
        f"--{GenMethod.PIECEWISE.value}",
        action="store_const",
        const=GenMethod.PIECEWISE,
        dest="method",
        help="Piecewise Interpolation generation method.",
    )
    method_group.add_argument(
        "-d",
        f"--{GenMethod.IDW.value}",
        action="store_const",
        const=GenMethod.IDW,
        dest="method",
        help="Inverse Distance Weighting generation method.",
    )

    return parser


def main():
    parser = build_parser(argparse.ArgumentParser())

    gen.generate(
        in_files=parser.parse_args().input_files,
        out_dir=parser.parse_args().o,
        filename=parser.parse_args().name,
        method=parser.parse_args().method,
        gen_preview=parser.parse_args().preview,
    )


if __name__ == "__main__":
    main()
