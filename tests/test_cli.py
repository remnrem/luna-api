import pytest
import pandas as pd
from datetime import datetime

from lunapi import cli
from lunapi import destrat_cli
from lunapi.cli import CLIError, _print_eval_log, parse_args


def test_cli_parses_common_luna_invocation():
    config = parse_args(
        ["study.lst", "-o", "out.db", "sig=EEG", "@params.txt", "-s", "EPOCH", "PSD"]
    )

    assert config.input_path == "study.lst"
    assert config.output_db == "out.db"
    assert config.command == "EPOCH PSD"
    assert [(p.kind, p.key, p.value) for p in config.parameters] == [
        ("var", "sig", "EEG"),
        ("include", "", "params.txt"),
    ]


def test_cli_parses_row_and_id_selection():
    config = parse_args(["study.lst", "2-5", "subject_7", "-s", "HEADERS"])

    assert (config.row_start, config.row_end) == (2, 5)
    assert config.ids == ["subject_7"]


def test_cli_s_consumes_the_remainder():
    config = parse_args(["study.lst", "-s", "PSD", "sig=EEG", "spectrum"])

    assert config.command == "PSD sig=EEG spectrum"
    assert config.parameters == []


def test_cli_rejects_append_until_supported():
    with pytest.raises(CLIError, match="not supported yet"):
        parse_args(["study.lst", "-a", "out.db", "-s", "HEADERS"])


def test_cli_exposes_build_and_validate_modes():
    build = parse_args(["--build", "-edfid", "/data"])
    validate = parse_args(["--validate", "study.lst"])

    assert build.mode == "build"
    assert build.build_args == ["-edfid", "/data"]
    assert validate.mode == "validate"
    assert validate.input_path == "study.lst"


def test_cli_banner_matches_native_version_date_layout(monkeypatch, capsys):
    monkeypatch.setattr(cli.lunapi0, "version", lambda: "v1.6.8  (31-Aug-2026)")

    cli._print_banner("starting", datetime(2026, 9, 2, 19, 49, 50))

    assert capsys.readouterr().err.splitlines() == [
        "===================================================================",
        "+++ luna | v1.6.8, 31-Aug-2026 | starting 02-Sep-2026 19:49:50 +++",
        "===================================================================",
    ]


def test_cli_eval_log_does_not_duplicate_record_header(capsys):
    _print_eval_log(
        "___________________________________________________________________\n"
        "Processing: subject-1 | recording.edf\n"
        " duration 01.00.00, 3600s\n\n"
        " ..................................................................\n"
        " CMD #1: HEADERS\n"
    )

    assert capsys.readouterr().err == (
        " duration 01.00.00, 3600s\n\n"
        " ..................................................................\n"
        " CMD #1: HEADERS\n"
    )


def test_destrat_cli_splits_native_command_selector_and_databases():
    databases, command = destrat_cli._split_items(["one.db", "two.db", "+PSD"])

    assert databases == ["one.db", "two.db"]
    assert command == "PSD"


def test_destrat_cli_supports_level_restricted_rows(monkeypatch, capsys):
    class FakeDB:
        def __init__(self, paths):
            assert paths == ["out.db"]

        def get(self, command, **kwargs):
            assert command == "PSD"
            assert kwargs == {
                "r": ["F/11,15", "CH"],
                "c": None,
                "v": ["PSD"],
                "ids": None,
            }
            return pd.DataFrame({"ID": ["s1"], "PSD": [1.25]})

    monkeypatch.setattr(destrat_cli, "destrat", FakeDB)
    assert destrat_cli.main(
        ["out.db", "+PSD", "-r", "F/11,15", "CH", "-v", "PSD"]
    ) == 0
    assert capsys.readouterr().out == "ID\tPSD\ns1\t1.25\n"


def test_destrat_cli_behead_formats_each_row_as_name_value_pairs(monkeypatch, capsys):
    class FakeDB:
        def __init__(self, paths):
            pass

        def get(self, command, **kwargs):
            return pd.DataFrame({"ID": ["s1"], "CH": ["C3"], "MEAN": [-0.039]})

    monkeypatch.setattr(destrat_cli, "destrat", FakeDB)
    assert destrat_cli.main(["out.db", "+STATS", "-r", "CH", "--behead"]) == 0
    assert capsys.readouterr().out == (
        "                       ID   s1                  \n"
        "                       CH   C3                  \n"
        "                     MEAN   -0.039              \n"
    )
