import argparse
from pathlib import Path

from src import generator as gen


def build_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "input_files",
        help="Configuration TOMLs for the LUT generation.",
        type=Path,
        nargs="+",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
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
        "--preview",
        action="store_true",
        help="Generate preview plots for each generated LUT.",
    )

    method_group = parser.add_mutually_exclusive_group()
    parser.set_defaults(method=gen.GenMethod.LINEAR)

    method_group.add_argument(
        "-l",
        f"--{gen.GenMethod.LINEAR.value}",
        action="store_const",
        const=gen.GenMethod.LINEAR,
        dest="method",
        help="Linear Interpolation generation method. [default]",
    )
    method_group.add_argument(
        "-s",
        f"--{gen.GenMethod.SPLINES.value}",
        action="store_const",
        const=gen.GenMethod.SPLINES,
        dest="method",
        help="Cubic Splines Interpolation generation method.",
    )
    method_group.add_argument(
        "-p",
        f"--{gen.GenMethod.POLYNOMIAL.value}",
        action="store_const",
        const=gen.GenMethod.POLYNOMIAL,
        dest="method",
        help="Polynomial Interpolation generation method.",
    )
    method_group.add_argument(
        "-w",
        f"--{gen.GenMethod.PIECEWISE.value}",
        action="store_const",
        const=gen.GenMethod.PIECEWISE,
        dest="method",
        help="Piecewise Interpolation generation method.",
    )
    method_group.add_argument(
        "-d",
        f"--{gen.GenMethod.IDW.value}",
        action="store_const",
        const=gen.GenMethod.IDW,
        dest="method",
        help="Inverse Distance Weighting generation method.",
    )

    return parser


def main():
    parser = build_parser(argparse.ArgumentParser())
    args = parser.parse_args()

    gen.generate(
        in_files=args.input_files,
        out_dir=args.output_dir,
        filename=args.name,
        method=args.method,
        gen_preview=args.preview,
    )


if __name__ == "__main__":
    main()
