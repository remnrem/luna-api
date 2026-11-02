"""Command-line adapter for the pure-Python :mod:`lunapi.destrat` reader.

The command follows the useful, query-oriented part of the native
``destrat`` grammar.  Database paths and an optional command selector are
positional; ``-r`` and ``-c`` consume factor specifications, including level
restrictions such as ``F/11,15``.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import textwrap
from shutil import get_terminal_size
from typing import Sequence

import pandas as pd

from .destrat import destrat


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="destrat.py",
        description="Query Luna SQLite/destrat output databases.",
        epilog=(
            "Examples: destrat.py out.db; "
            "destrat.py out.db +PSD -r CH F -v PSD; "
            "destrat.py out.db +PSD -r F/11,15 CH"
        ),
    )
    parser.add_argument(
        "items",
        nargs="+",
        metavar="DB|COMMAND",
        help="database path(s), followed optionally by +COMMAND or [COMMAND]",
    )
    parser.add_argument(
        "-r", dest="rows", action="append", nargs="+", metavar="FACTOR",
        help="row stratifier(s), e.g. CH F/11,15; may be repeated",
    )
    parser.add_argument(
        "-c", dest="columns", action="append", nargs="+", metavar="FACTOR",
        help="column stratifier(s), e.g. B; may be repeated",
    )
    parser.add_argument(
        "-v", dest="variables", action="append", nargs="+", metavar="VARIABLE",
        help="variable(s) to extract; may be repeated",
    )
    parser.add_argument(
        "-i", dest="individuals", action="append", nargs="+", metavar="ID",
        help="individual ID(s) to include; may be repeated",
    )
    parser.add_argument(
        "-s", dest="statement", metavar="COMMAND",
        help="select a command, as an alternative to +COMMAND",
    )
    parser.add_argument(
        "-x", dest="summary", action="store_true",
        help="print the output summary (the default without a command)",
    )
    parser.add_argument(
        "-d", dest="dictionary", action="store_true",
        help="print the command/variable dictionary",
    )
    parser.add_argument(
        "-p", dest="precision", type=int, metavar="N",
        help="print numeric values with N decimal places",
    )
    # Native destrat uses -f to select database output mode.  The Python
    # reader is database-only, so accepting it keeps common invocations
    # compatible without changing behavior.
    parser.add_argument("-f", dest="database_mode", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "-n", dest="include_command", action="store_true",
        help="prepend a CMD column to extracted output",
    )
    parser.add_argument(
        "-b", "--behead", dest="behead", action="store_true",
        help="print each extracted row as name/value pairs",
    )
    return parser


def _flatten(groups: list[list[str]] | None) -> list[str]:
    return [item for group in (groups or []) for item in group]


def _split_items(items: Sequence[str]) -> tuple[list[str], str | None]:
    """Split database paths from an optional native-style command selector."""

    databases = []
    command = None
    for item in items:
        if item.startswith("+") and len(item) > 1:
            if command is not None:
                raise ValueError("only one command selector may be specified")
            command = item[1:]
        elif len(item) > 2 and item.startswith("[") and item.endswith("]"):
            if command is not None:
                raise ValueError("only one command selector may be specified")
            command = item[1:-1]
        else:
            databases.append(item)
    if not databases:
        raise ValueError("at least one database path is required")
    return databases, command


def _format_frame(frame: pd.DataFrame, precision: int | None) -> str:
    kwargs = {"sep": "\t", "index": False, "na_rep": "NA", "lineterminator": "\n"}
    if precision is not None:
        kwargs["float_format"] = f"%.{precision}f"
    return frame.to_csv(**kwargs)


def _format_summary(frame: pd.DataFrame) -> str:
    """Format the summary with wrapped variable lists for terminal reading."""

    if frame.empty:
        return frame.to_string(index=False)

    columns = ["CMD", "FACTORS", "N_VARS"]
    widths = {
        column: max(len(column), max(len(str(value)) for value in frame[column]))
        for column in columns
    }
    prefix_width = sum(widths.values()) + 3 * len(columns)
    terminal_width = max(80, get_terminal_size((120, 20)).columns)
    variable_width = max(30, terminal_width - prefix_width - 1)

    header = (
        f"{'CMD':<{widths['CMD']}}   "
        f"{'FACTORS':<{widths['FACTORS']}}   "
        f"{'N_VARS':>{widths['N_VARS']}}   VARIABLES"
    )
    lines = [header]
    continuation = " " * (prefix_width + 1)
    for row in frame.itertuples(index=False):
        values = dict(zip(frame.columns, row))
        variables = str(values.get("VARIABLES", ""))
        wrapped = textwrap.wrap(
            variables,
            width=variable_width,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [""]
        prefix = (
            f"{str(values['CMD']):<{widths['CMD']}}   "
            f"{str(values['FACTORS']):<{widths['FACTORS']}}   "
            f"{str(values['N_VARS']):>{widths['N_VARS']}}   "
        )
        lines.append(prefix + wrapped[0])
        lines.extend(continuation + part for part in wrapped[1:])
    return "\n".join(lines)


def _format_behead(frame: pd.DataFrame) -> str:
    """Format rows like Luna's ``behead`` utility."""

    lines = []
    for row in frame.itertuples(index=False, name=None):
        for column, value in zip(frame.columns, row):
            if pd.isna(value):
                value = "NA"
            lines.append(f"{str(column):>25}   {str(value):<20}")
        lines.append("")
    return "\n".join(lines)


def _write(text: str) -> None:
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Python destrat command and return an exit status."""

    args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        databases, command = _split_items(args.items)
        if args.statement is not None:
            if command is not None:
                raise ValueError("cannot specify both +COMMAND/[COMMAND] and -s")
            command = args.statement.lstrip("+#")

        db = destrat(databases)

        if args.dictionary:
            _write(db.vars().to_string(index=False))
            return 0

        if command is None:
            if args.rows or args.columns or args.variables or args.individuals:
                raise ValueError("-r, -c, -v and -i require a command selector")
            _write(_format_summary(db.tables()))
            return 0

        frame = db.get(
            command,
            r=_flatten(args.rows) or None,
            c=_flatten(args.columns) or None,
            v=_flatten(args.variables) or None,
            ids=_flatten(args.individuals) or None,
        )
        if args.include_command:
            frame = frame.copy()
            frame.insert(0, "CMD", command)
        if args.behead:
            _write(_format_behead(frame))
        else:
            _write(_format_frame(frame, args.precision))
        return 0
    except (FileNotFoundError, ValueError, KeyError, sqlite3.Error) as exc:
        print(f"destrat.py: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
