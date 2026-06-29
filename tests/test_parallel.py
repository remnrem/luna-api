import pandas as pd
import pytest

from lunapi.parallel import (
    ParallelProcError,
    ParallelProcResult,
    clamp_workers,
    default_workers,
    normalize_result_table,
    normalize_sample_row,
    parse_param_text,
    project_eval_slices,
    resolve_params,
)


def test_default_workers_is_safe_for_unknown_cpu_count(monkeypatch):
    monkeypatch.setattr("lunapi.parallel.os.cpu_count", lambda: None)

    assert default_workers(None) == 1


def test_default_workers_caps_at_ten():
    assert default_workers(64) == 10


def test_clamp_workers_bounds_and_record_count():
    assert clamp_workers(0, cpu_count=8) == 1
    assert clamp_workers(99, cpu_count=8) == 8
    assert clamp_workers(8, total_records=3, cpu_count=8) == 3


def test_project_eval_slices_are_contiguous_and_cover_all_rows():
    tasks = [
        {"ordinal": i, "sample_row": [f"S{i}", f"{i}.edf", "."], "label": f"S{i}"}
        for i in range(1, 8)
    ]

    slices = project_eval_slices(tasks, workers=3)

    assert [(s["start_ordinal"], s["end_ordinal"]) for s in slices] == [
        (1, 3),
        (4, 6),
        (7, 7),
    ]
    assert [row[0] for s in slices for row in s["rows"]] == [
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
    ]


def test_project_eval_slices_respects_batch_size():
    tasks = [
        {"ordinal": i, "sample_row": [f"S{i}", f"{i}.edf", "."], "label": f"S{i}"}
        for i in range(1, 6)
    ]

    slices = project_eval_slices(tasks, workers=3, batch_size=2)

    assert [(s["start_ordinal"], s["end_ordinal"]) for s in slices] == [
        (1, 2),
        (3, 4),
        (5, 5),
    ]


def test_normalize_result_table_adds_id_column():
    df = pd.DataFrame({"X": [1, 2]})

    out = normalize_result_table(df, "S1")

    assert list(out.columns) == ["ID", "X"]
    assert out["ID"].tolist() == ["S1", "S1"]


def test_normalize_result_table_fills_blank_ids():
    df = pd.DataFrame({"ID": ["", None, "S2"], "X": [1, 2, 3]})

    out = normalize_result_table(df, "S1")

    assert list(out.columns) == ["ID", "X"]
    assert out["ID"].tolist() == ["S1", "S1", "S2"]


def test_normalize_sample_row_joins_annotation_collections():
    assert normalize_sample_row(["S1", "x.edf", {"b.annot", "a.annot"}]) == [
        "S1",
        "x.edf",
        "a.annot,b.annot",
    ]


def test_parallel_result_missing_key_lists_available_tables():
    result = ParallelProcResult(
        tables={"HEADERS: CH": pd.DataFrame()},
        errors=pd.DataFrame(),
        stdout=pd.DataFrame(),
        records=pd.DataFrame(),
        workers=1,
    )

    with pytest.raises(KeyError, match="Available tables: HEADERS: CH"):
        result["PSD: CH_F"]


def test_parallel_result_programmatic_table_accessors():
    result = ParallelProcResult(
        tables={
            "HEADERS: BL": pd.DataFrame({"ID": ["S1"]}),
            "PSD: CH_F": pd.DataFrame({"ID": ["S1"], "PSD": [1.0]}),
        },
        errors=pd.DataFrame(),
        stdout=pd.DataFrame(),
        records=pd.DataFrame(),
        workers=1,
    )

    assert result.has_table("HEADERS")
    assert result.has_table("PSD", "CH_F")
    assert result.has_table("PSD", ["CH", "F"])
    assert result.has_table("PSD", ["F", "CH"])
    assert result.table("PSD", "CH_F")["PSD"].tolist() == [1.0]
    assert result.table("PSD", ["CH", "F"])["PSD"].tolist() == [1.0]
    assert result.table("PSD", ["F", "CH"])["PSD"].tolist() == [1.0]
    assert result.tables["PSD: CH_F"]["PSD"].tolist() == [1.0]
    assert result.tables() == {"HEADERS": [["BL"]], "PSD": [["CH", "F"]]}
    assert result.table_index() == {"HEADERS": [["BL"]], "PSD": [["CH", "F"]]}
    assert result.strata().to_dict("records") == [
        {"Command": "HEADERS", "Strata": "BL"},
        {"Command": "PSD", "Strata": "CH_F"},
    ]
    assert result.commands()["Command"].tolist() == ["HEADERS", "PSD"]


def test_parse_param_text_supports_luna_delimiters_and_comments():
    text = """
% comment
sig EEG
alias="C3 M2"
thresh\t5
"""

    assert parse_param_text(text) == [
        ("sig", "EEG"),
        ("alias", '"C3 M2"'),
        ("thresh", "5"),
    ]


def test_resolve_params_file_then_dict_override(tmp_path):
    param_file = tmp_path / "params.txt"
    param_file.write_text("sig=EEG\nth=3\n", encoding="utf-8")

    assert resolve_params({"th": 5, "extra": "yes"}, param_file) == [
        ("sig", "EEG"),
        ("th", "5"),
        ("extra", "yes"),
    ]


def test_parse_param_text_rejects_bad_lines():
    with pytest.raises(ValueError):
        parse_param_text("novalue")


def test_proc_parallel_runs_file_backed_sample_list(lp, tmp_sl_two):
    lp.sample_list(str(tmp_sl_two))

    result = lp.proc_parallel("HEADERS", workers=2)

    assert result.ok
    assert result.workers == 2
    assert "HEADERS: CH" in result
    df = result["HEADERS: CH"]
    assert set(df["ID"]) == {"test_subject_1", "test_subject_2"}
    assert set(df["CH"]) == {"EEG"}


def test_procn_alias_delegates_to_proc_parallel(monkeypatch, lp):
    calls = {}

    def fake_proc_parallel(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(lp, "proc_parallel", fake_proc_parallel)

    out = lp.procn(
        "HEADERS",
        workers=2,
        batch_size=5,
        params={"sig": "EEG"},
        progress=True,
    )

    assert out == "ok"
    assert calls["args"] == ("HEADERS",)
    assert calls["kwargs"] == {
        "workers": 2,
        "batch_size": 5,
        "params": {"sig": "EEG"},
        "param_file": None,
        "strict": False,
        "progress": True,
    }


def test_proc_parallel_collects_errors_when_not_strict(lp, tmp_sl_two):
    lp.sample_list(str(tmp_sl_two))

    result = lp.proc_parallel("NOT_A_REAL_COMMAND", workers=2)

    assert not result.ok
    assert len(result.errors) == 2
    assert set(result.errors["ID"]) == {"test_subject_1", "test_subject_2"}


def test_proc_parallel_strict_raises_with_partial_result(lp, tmp_sl_two):
    lp.sample_list(str(tmp_sl_two))

    with pytest.raises(ParallelProcError) as excinfo:
        lp.proc_parallel("NOT_A_REAL_COMMAND", workers=2, strict=True)

    assert not excinfo.value.result.ok
    assert len(excinfo.value.result.errors) == 2
