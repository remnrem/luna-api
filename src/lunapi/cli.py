"""Command-line interface for the common Luna sample-list workflow.

This module deliberately contains only the command-line adapter.  Luna
options, parameter files, sample-list loading, EDF attachment, command
evaluation, and output writing continue to be handled by the existing
``lunapi``/C++ APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import os
import sys
from typing import Sequence

from . import __version__, lunapi0
from .instance import inst as _inst
from .project import proj


HELP = """\
Usage:
  luna.py SAMPLE_LIST [options] [LUNA_VARIABLES...] -s "COMMANDS"
  luna.py EDF        [options] [LUNA_VARIABLES...] -s "COMMANDS"
  luna.py SAMPLE_LIST [options] < command-file

Common examples:
  luna.py s.lst -o out.db sig=EEG @params.txt -s "EPOCH len=30 PSD"
  luna.py s.lst 1 10 -o out.db -s "HEADERS"
  luna.py s.lst subject_001 -o out.db -s "DESC"
  luna.py --build /data/study > s.lst
  luna.py --validate s.lst

Supported interface:
  Input
    SAMPLE_LIST              Tab-delimited ID / EDF / annotation sample list
    EDF                      Process one EDF/EDFZ/REC/SEDF recording

  Output
    -o FILE                  Write one SQLite result database (overwrites it)
    -t DIRECTORY             Write Luna plain-text tables to a directory

  Commands
    -s COMMANDS              Evaluate the remainder of the command line
    stdin                     If -s is omitted, read a command file from stdin

  Luna variables
    key=value                 Set a Luna special variable or option
    @PARAM_FILE               Read a Luna parameter file

  Sample selection
    N                         Select sample-list row N (1-based)
    N-M                       Select an inclusive row range
    N/M                       Select the Luna slice N of M
    ID                        Select a sample-list ID; repeat for multiple IDs

  Supported helper modes
    --build PATH...           Build a sample list using Luna's C++ builder
    --validate SAMPLE_LIST    Validate EDF paths in a sample list
    --version                 Show lunapi and Luna versions
    -h, --help                Show this help

Not currently implemented by this interface:
  -a/--append and Luna's standalone special tools such as --xml, --merge,
  --repath, --gpa, --psc, --pops, and signal/filter design helpers.
  Use the native luna executable for those workflows.
"""


class CLIError(ValueError):
    """A user-facing command-line parsing or usage error."""


@dataclass(frozen=True)
class ParameterAction:
    """An option to apply through the existing Luna API."""

    kind: str
    key: str = ""
    value: str = ""


@dataclass
class CLIConfig:
    """Parsed configuration for the ordinary Luna CLI workflow."""

    input_path: str | None = None
    output_db: str | None = None
    output_text: str | None = None
    command: str | None = None
    row_start: int | None = None
    row_end: int | None = None
    ids: list[str] = field(default_factory=list)
    parameters: list[ParameterAction] = field(default_factory=list)
    mode: str = "run"
    build_args: list[str] = field(default_factory=list)


def _parse_positive_int(value: str, description: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise CLIError(f"invalid {description}: {value!r}") from exc
    if number < 1:
        raise CLIError(f"{description} must be at least 1: {value!r}")
    return number


def _add_row_selector(config: CLIConfig, token: str) -> bool:
    if token.isdigit():
        number = _parse_positive_int(token, "sample-list row")
        if config.row_start is None:
            config.row_start = number
            config.row_end = number
        elif config.row_start == config.row_end:
            config.row_end = number
        else:
            raise CLIError("cannot specify more than two numeric row selectors")
        return True

    if "/" in token:
        parts = token.split("/")
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            n = _parse_positive_int(parts[0], "slice numerator")
            m = _parse_positive_int(parts[1], "slice denominator")
            if n > m:
                raise CLIError("slice numerator must not exceed denominator")
            # The native sample-list slicer is not exposed as a Python helper.
            # Convert the common N/M form to the corresponding contiguous
            # partition using the loaded row count later.
            config.row_start = n
            config.row_end = -m
            return True

    if "-" in token:
        parts = token.split("-")
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            config.row_start = _parse_positive_int(parts[0], "row range start")
            config.row_end = _parse_positive_int(parts[1], "row range end")
            if config.row_start > config.row_end:
                raise CLIError("row range start must not exceed its end")
            return True

    return False


def parse_args(argv: Sequence[str]) -> CLIConfig:
    """Parse the supported Luna command-line grammar without side effects."""

    args = list(argv)
    if not args:
        raise CLIError("an input sample list or EDF is required")
    if args[0] in ("-h", "--help"):
        return CLIConfig(mode="help")
    if args[0] in ("-v", "--version"):
        return CLIConfig(mode="version")
    if args[0] == "--build":
        if len(args) == 1:
            raise CLIError("--build requires one or more folders")
        return CLIConfig(mode="build", build_args=args[1:])
    if args[0] == "--validate":
        if len(args) < 2:
            raise CLIError("--validate requires a sample-list path")
        config = CLIConfig(mode="validate", input_path=args[1])
        rest = args[2:]
    else:
        config = CLIConfig(input_path=args[0])
        rest = args[1:]

    i = 0
    while i < len(rest):
        token = rest[i]

        if token in ("-h", "--help"):
            config.mode = "help"
            return config
        if token in ("-v", "--version"):
            config.mode = "version"
            return config
        if token in ("-o", "-t"):
            if i + 1 >= len(rest):
                raise CLIError(f"{token} requires a path")
            value = rest[i + 1]
            if not value or value.startswith("-"):
                raise CLIError(f"{token} requires a path")
            if token == "-o":
                if config.output_text is not None:
                    raise CLIError("cannot combine -o and -t")
                config.output_db = value
            else:
                if config.output_db is not None:
                    raise CLIError("cannot combine -o and -t")
                config.output_text = value
            i += 2
            continue
        if token in ("-a", "--append"):
            raise CLIError("-a/--append is not supported yet; use -o to overwrite")
        if token == "-s":
            if i + 1 >= len(rest):
                raise CLIError("-s requires Luna commands")
            config.command = " ".join(rest[i + 1:])
            break
        if token.startswith("@"):
            if token != "@.":
                config.parameters.append(ParameterAction("include", value=token[1:]))
            i += 1
            continue
        if token.startswith("--"):
            raise CLIError(
                f"standalone option {token!r} is not supported; use key=value "
                "or one of the modes listed by --help"
            )
        if "=" in token:
            key, value = token.split("=", 1)
            if not key:
                raise CLIError(f"invalid Luna variable: {token!r}")
            config.parameters.append(ParameterAction("var", key, value))
            i += 1
            continue
        if _add_row_selector(config, token):
            i += 1
            continue
        config.ids.append(token)
        i += 1

    return config


def _apply_parameters(project: proj, actions: Sequence[ParameterAction]) -> None:
    for action in actions:
        if action.kind == "include":
            project.include(action.key)
        else:
            project.var(action.key, action.value)


def _select_rows(rows, config: CLIConfig):
    selected = list(rows)
    if config.ids:
        wanted = set(config.ids)
        selected = [row for row in selected if str(row[0]) in wanted]

    if config.row_start is not None:
        if config.row_end is not None and config.row_end < 0:
            n, m = config.row_start, -config.row_end
            total = len(selected)
            start = ((n - 1) * total) // m
            end = (n * total) // m
            selected = selected[start:end]
        else:
            lo = config.row_start
            hi = config.row_end or lo
            selected = selected[lo - 1:hi]
    return selected


def _print_built_sample_list(project: proj) -> None:
    for row in project.eng.get_sample_list():
        ident, edf, annots = row
        annot_text = ",".join(sorted(annots)) if annots else "."
        print(f"{ident}\t{edf}\t{annot_text}")


def _load_sample_list(project: proj, path: str) -> int:
    """Load a sample list without the notebook-oriented stdout message."""

    project.eng.clear()
    return project.eng.read_sample_list(path)


def _single_input_id(path: str) -> str:
    lower = path.lower()
    for suffix in (".edf.gz", ".edfz", ".sedf", ".rec", ".edf"):
        if lower.endswith(suffix):
            return path[: -len(suffix)]
    return path


def _print_banner(phase: str, started: datetime) -> None:
    # ``lunapi0.version()`` combines the native version and build date as
    # ``vX.Y.Z  (date)``.  The command-line banner keeps those as the two
    # fields used by native lunaC: ``version, build-date``.
    version_text = lunapi0.version()
    if "(" in version_text and version_text.endswith(")"):
        version, build_date = version_text.rsplit("(", 1)
        version = version.rstrip()
        build_date = build_date[:-1]
    else:
        version, build_date = version_text, ""
    timestamp = started.strftime("%d-%b-%Y %H:%M:%S")
    if phase == "starting":
        print("===================================================================", file=sys.stderr)
        version_field = f"{version}, {build_date}" if build_date else version
        print(f"+++ luna | {version_field} | starting {timestamp} +++", file=sys.stderr)
        print("===================================================================", file=sys.stderr)
    else:
        print("-------------------------------------------------------------------", file=sys.stderr)
        print(f"+++ luna | finishing {timestamp}                       +++", file=sys.stderr)
        print("===================================================================", file=sys.stderr)


def _print_eval_log(log: str) -> None:
    """Forward native command logging without duplicating the outer record line."""

    if not log:
        return
    lines = [line for line in log.splitlines(True)
             if not line.lstrip().startswith("Processing:")
             and line.rstrip("\r\n") != "___________________________________________________________________"]
    text = "".join(lines)
    if text:
        print(text, file=sys.stderr, end="" if text.endswith("\n") else "\n")


def _read_command(config: CLIConfig) -> str:
    if config.command is not None:
        command = config.command.strip()
    elif sys.stdin.isatty():
        raise CLIError("no commands supplied; use -s or redirect a command file on stdin")
    else:
        command = sys.stdin.read().strip()
    if not command:
        raise CLIError("no Luna commands supplied")
    return command


def _is_single_edf(path: str) -> bool:
    lower = path.lower()
    return lower.endswith((".edf", ".edf.gz", ".edfz", ".rec", ".sedf"))


def _run(config: CLIConfig) -> int:
    project = proj(verbose=False)
    project.clear_vars()
    project.reinit()

    if config.mode == "build":
        project.build(config.build_args)
        _print_built_sample_list(project)
        return 0

    _apply_parameters(project, config.parameters)

    if config.mode == "validate":
        _load_sample_list(project, config.input_path)
        table = project.validate()
        print(table.to_string(index=False))
        return 0 if bool(table["Valid"].all()) else 1

    command = _read_command(config)
    single_edf = _is_single_edf(config.input_path)
    if single_edf:
        rows = [(_single_input_id(config.input_path), config.input_path, set())]
    else:
        _load_sample_list(project, config.input_path)
        rows = _select_rows(project.eng.get_sample_list(), config)

    if not rows:
        raise CLIError("no sample-list records matched the requested selection")

    started = datetime.now()
    _print_banner("starting", started)
    print(f"input(s): {config.input_path}", file=sys.stderr)
    if config.output_db is not None:
        print(f"output  : {config.output_db}", file=sys.stderr)
    elif config.output_text is not None:
        print(f"output  : {config.output_text}", file=sys.stderr)
    print(f"commands: c1\t{command}\t", file=sys.stderr)

    if config.output_db is not None:
        project.eng.output_attach(config.output_db)
    elif config.output_text is not None:
        project.eng.output_plaintext(config.output_text)

    failures = 0
    try:
        for ordinal, row in enumerate(rows, start=1):
            ident = str(row[0])
            print("\n___________________________________________________________________", file=sys.stderr)
            print(f"Processing: {ident} [ #{ordinal} ]", file=sys.stderr)
            try:
                # Reinitialize per record just as the existing file-output
                # worker does, while preserving the configured output writer.
                project.reinit()
                _apply_parameters(project, config.parameters)
                if single_edf:
                    record = _inst(project.eng.inst(ident, config.input_path))
                else:
                    record = project.inst(ident)
                log = record.edf.eval_file(command)
                _print_eval_log(log)
            except Exception as exc:  # keep processing the remaining records
                failures += 1
                print(f"luna.py: ERROR processing {ident}: {exc}", file=sys.stderr)
                project.reset()
    finally:
        if config.output_db is not None or config.output_text is not None:
            project.eng.output_close()

    print(f"...processed {len(rows)} EDFs, done.", file=sys.stderr)
    if failures == 0:
        print("...processed 1 command set(s),  all of which passed", file=sys.stderr)
    else:
        print(f"...processed 1 command set(s), {failures} of which failed", file=sys.stderr)
    _print_banner("finishing", datetime.now())

    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``luna.py`` command-line interface and return an exit code."""

    try:
        config = parse_args(sys.argv[1:] if argv is None else argv)
        if config.mode == "help":
            print(HELP)
            return 0
        if config.mode == "version":
            print(f"lunapi {__version__}")
            print(f"luna {lunapi0.version()}")
            return 0
        return _run(config)
    except CLIError as exc:
        print(f"luna.py: error: {exc}", file=sys.stderr)
        print("luna.py: use --help for supported options", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"luna.py: fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
