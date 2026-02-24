import argparse

from src.generator import GenMethod
from src.generator import main as generator_main


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        metavar="path/to/yaml.yml",
        help="Configuration YAMLs for the LUT generation.",
        type=str,
        nargs="+",
        required=True,
    )
    parser.add_argument(
        "-n",
        "--name",
        metavar="name",
        help="Name of the generated header.",
        default="lookup_tables",
    )

    method_group = parser.add_mutually_exclusive_group()

    method_group.add_argument(
        "-l",
        "--linear",
        action="store_const",
        const=GenMethod.LINEAR,
        dest="method",
        help="Linear Interpolation generation method.",
    )
    method_group.add_argument(
        "-s",
        "--spline",
        action="store_const",
        const=GenMethod.SPLINE,
        dest="method",
        help="Cubic Splines Interpolation generation method.",
    )
    method_group.add_argument(
        "-p",
        "--polinomial",
        action="store_const",
        const=GenMethod.POLINOMIAL,
        dest="method",
        help="Polinomial Interpolation generation method.",
    )
    method_group.add_argument(
        "-w",
        "--piecewise",
        action="store_const",
        const=GenMethod.PIECEWISE,
        dest="method",
        help="Piecewise Interpolation generation method.",
    )

    parser.set_defaults(method=GenMethod.LINEAR)

    generator_main(
        parser.parse_args().i,
        parser.parse_args().name,
        parser.parse_args().method,
    )


if __name__ == "__main__":
    main()
