import argparse

from src import generator as gen
from src.generator import GenMethod


def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "-i",
        metavar="path/to/config.toml",
        help="Configuration YAMLs for the LUT generation.",
        type=str,
        nargs="+",
        required=True,
    )
    parser.add_argument(
        "-n",
        "--name",
        metavar="name",
        help="Name of the generated LUT files.",
        default="lookup_tables",
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
        parser.parse_args().i,
        parser.parse_args().name,
        parser.parse_args().method,
    )


if __name__ == "__main__":
    main()
