"""Process-based project execution helpers for lunapi."""

from __future__ import annotations

import itertools
import os
import traceback
import warnings
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd


_CHILD_PROJ = None


class FileOutputModeError(RuntimeError):
   """Raised when table access is attempted on a file-output-only ProcResult."""
   pass


@dataclass
class ProcResult:
   """Result returned by proc(), silent_proc(), proc_parallel(), and procn().

   In memory mode (default): table data lives in the C-level cache of *_owner*;
   all table queries delegate there.

   In file-output mode (out_db / out_text): *_owner* is None and table data was
   written directly to disk.  Metadata (errors, records, out_paths) is still
   available; table queries raise FileOutputModeError.
   """

   _owner: object = field(repr=False)
   errors: pd.DataFrame = field(repr=False)
   stdout: pd.DataFrame = field(repr=False)
   records: pd.DataFrame = field(repr=False)
   workers: int = 1
   _out_paths: list = field(default_factory=list, repr=False)

   @property
   def ok(self) -> bool:
      return self.errors.empty

   def _file_mode_error(self):
      paths = ", ".join(str(p) for p in self._out_paths) if self._out_paths else "(unknown)"
      raise FileOutputModeError(
         f"Results were written to file(s) ({paths}), not held in memory. "
         "Load with lp.import_db() or read text tables directly."
      )

   def _owner_keys(self):
      if self._owner is None:
         return []
      s = self._owner.strata()
      if s is None or (hasattr(s, "empty") and s.empty):
         return []
      return [_table_key(row.Command, row.Strata) for row in s.itertuples(index=False)]

   def __getitem__(self, key):
      if self._owner is None:
         self._file_mode_error()
      if isinstance(key, tuple) and len(key) == 2:
         return self.table(key[0], key[1])
      cmd, strata = _split_table_key(key)
      t = self._owner.table(cmd, strata)
      if t is None:
         available = ", ".join(self._owner_keys()) or "<none>"
         raise KeyError(f"{key!r} not found in results. Available: {available}")
      return t

   def __contains__(self, key) -> bool:
      return key in self._owner_keys()

   def __iter__(self):
      return iter(self._owner_keys())

   def __len__(self) -> int:
      return len(self._owner_keys())

   def keys(self):
      return self._owner_keys()

   def items(self):
      for key in self._owner_keys():
         cmd, strata = _split_table_key(key)
         yield key, self._owner.table(cmd, strata)

   def values(self):
      for key in self._owner_keys():
         cmd, strata = _split_table_key(key)
         yield self._owner.table(cmd, strata)

   def get(self, key, default=None):
      try:
         return self[key]
      except (KeyError, FileOutputModeError):
         return default

   def table(self, cmd, strata="BL"):
      """Return one result table by Luna command and strata."""
      if self._owner is None:
         self._file_mode_error()
      return self._owner.table(cmd, strata)

   def strata(self):
      """Return available command/strata pairs as a DataFrame."""
      if self._owner is None:
         self._file_mode_error()
      return self._owner.strata()

   def commands(self):
      """Return available commands as a DataFrame."""
      if self._owner is None:
         self._file_mode_error()
      s = self._owner.strata()
      if s is None or s.empty:
         return pd.DataFrame(columns=["Command"])
      return pd.DataFrame(sorted(s["Command"].unique()), columns=["Command"])

   def has_table(self, cmd, strata="BL"):
      """Return whether a command/strata table is present."""
      if self._owner is None:
         return False
      try:
         return self._owner.table(cmd, strata) is not None
      except Exception:
         return False

   def table_index(self):
      """Return ``{command: [strata_factor_list, ...]}`` for available tables."""
      if self._owner is None:
         self._file_mode_error()
      s = self._owner.strata()
      if s is None:
         return {}
      index = {}
      for row in s.itertuples(index=False):
         index.setdefault(row.Command, []).append(_strata_parts(row.Strata))
      return index

   def __repr__(self):
      n_total = len(self.records)
      n_errors = len(self.errors)
      if self._owner is None:
         paths = ", ".join(str(p) for p in self._out_paths) if self._out_paths else "(none)"
         status = "completed successfully" if self.ok else f"completed with {n_errors} error(s)"
         return f"ProcResult: {status} ({n_total} record(s), file output: {paths})"
      n_tables = len(self._owner_keys())
      if self.ok:
         return f"ProcResult: completed successfully ({n_total} record(s), {n_tables} table(s))"
      return (
         f"ProcResult: completed with {n_errors} error(s) "
         f"out of {n_total} record(s)\n{self.errors.to_string(index=False)}"
      )

   def _repr_html_(self):
      n_total = len(self.records)
      n_errors = len(self.errors)
      if self._owner is None:
         paths_html = "<br>".join(str(p) for p in self._out_paths) if self._out_paths else "(none)"
         status = "<b>Completed successfully</b>" if self.ok else f"<b>Completed with {n_errors} error(s)</b>"
         return (
            f"<p>{status}: {n_total} record(s) processed.</p>"
            f"<p>Output files:<br><code>{paths_html}</code></p>"
         )
      n_tables = len(self._owner_keys())
      if self.ok:
         return (
            f"<p><b>Completed successfully</b>: "
            f"{n_total} record(s) processed, {n_tables} table(s) returned.</p>"
         )
      status = (
         f"<p><b>Completed with errors</b>: "
         f"{n_errors} failure(s) out of {n_total} record(s).</p>"
      )
      return status + self.errors._repr_html_()


# Keep old name as alias for any external code that referenced it
ParallelProcResult = ProcResult


class ProcError(RuntimeError):
   """Raised when execution fails with ``strict=True``."""

   def __init__(self, message: str, result: ProcResult):
      super().__init__(message)
      self.result = result


ParallelProcError = ProcError


def _table_key(cmd, strata="BL"):
   return f"{cmd}: {strata}"


def _split_table_key(key):
   if ": " not in key:
      return key, ""
   cmd, strata = key.split(": ", 1)
   return cmd, strata


def _strata_parts(strata):
   if strata is None:
      return ["BL"]
   if isinstance(strata, str):
      return [part for part in strata.split("_") if part]
   return [str(part) for part in strata if str(part)]


def coerce_strata(pairs, cmd, strata):
   """Resolve a list/set strata to the matching string given C-level (cmd, strata) pairs.

   ``pairs`` is the list of ``(cmd, strata)`` tuples returned by
   ``eng.strata()`` / ``edf.strata()``.  If *strata* is already a string
   it is returned unchanged.  A list or set is matched order-independently
   against the ``_``-delimited factor tokens in each available strata string.
   """
   if isinstance(strata, str) or strata is None:
      return "BL" if strata is None else strata
   requested = set(_strata_parts(strata))
   matches = [s for c, s in pairs if c == cmd and set(_strata_parts(s)) == requested]
   if len(matches) == 1:
      return matches[0]
   if len(matches) > 1:
      raise KeyError(
         f"ambiguous strata {list(strata)!r} for {cmd!r}; matches: {', '.join(sorted(matches))}"
      )
   avail = sorted(s for c, s in pairs if c == cmd)
   raise KeyError(
      f"no strata matching {list(strata)!r} for {cmd!r}. "
      f"Available: {', '.join(avail) or '<none>'}"
   )


def _resolve_table_key(tables, cmd, strata="BL"):
   if isinstance(strata, str) or strata is None:
      key = _table_key(cmd, "BL" if strata is None else strata)
      if key in tables:
         return key
   requested = set(_strata_parts(strata))
   matches = []
   for key in tables:
      key_cmd, key_strata = _split_table_key(key)
      if key_cmd == cmd and set(_strata_parts(key_strata)) == requested:
         matches.append(key)
   if len(matches) == 1:
      return matches[0]
   if len(matches) > 1:
      raise KeyError(
         f"ambiguous strata {strata!r} for command {cmd!r}; matches: {', '.join(sorted(matches))}"
      )
   available = ", ".join(sorted(tables)) or "<none>"
   raise KeyError(f"{_table_key(cmd, strata)!r} not found in parallel results. Available tables: {available}")


def _tables_index(tables):
   index = {}
   for key in tables:
      cmd, strata = _split_table_key(key)
      index.setdefault(cmd, []).append(_strata_parts(strata))
   return index


def default_workers(cpu_count=None) -> int:
   if cpu_count is None:
      cpu_count = os.cpu_count()
   try:
      cpu_count = int(cpu_count)
   except (TypeError, ValueError):
      cpu_count = 1
   return min(10, max(1, cpu_count // 2))


def clamp_workers(value, total_records=None) -> int:
   try:
      value = default_workers() if value is None else int(value)
   except (TypeError, ValueError):
      value = default_workers()
   value = max(1, value)
   if total_records is not None:
      value = min(value, max(1, int(total_records)))
   return value


def tokenize_param_line(line: str, keep_quotes: bool = True) -> list[str]:
   out, buf, quote, esc = [], [], None, False
   for ch in line:
      if esc:
         buf.append(ch)
         esc = False
         continue
      if quote:
         buf.append(ch)
         if ch == "\\":
            esc = True
         elif ch == quote:
            quote = None
         continue
      if ch in ("'", '"'):
         quote = ch
         buf.append(ch)
         continue
      if ch in (" ", "\t", "=") and not out:
         out.append("".join(buf).strip())
         buf = []
         continue
      buf.append(ch)
   if buf:
      out.append("".join(buf).strip())
   if len(out) == 2:
      out[1] = out[1].lstrip("= \t")
   if not keep_quotes and len(out) == 2:
      val = out[1]
      if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
         out[1] = val[1:-1]
   return out


def parse_param_text(text: str) -> list[tuple[str, str]]:
   pairs = []
   for lineno, raw in enumerate(text.splitlines(), start=1):
      line = raw.strip()
      if not line or line.startswith("%"):
         continue
      toks = tokenize_param_line(line)
      if len(toks) != 2 or not toks[0]:
         raise ValueError(f"badly formatted parameter line {lineno}: {raw}")
      pairs.append((toks[0].strip(), toks[1].strip()))
   return pairs


def parse_param_file(path) -> list[tuple[str, str]]:
   return parse_param_text(Path(path).read_text(encoding="utf-8"))


def resolve_params(params=None, param_file=None) -> list[tuple[str, str]]:
   resolved = []
   if param_file is not None:
      resolved.extend(parse_param_file(param_file))
   if params is None:
      return resolved
   if isinstance(params, Mapping):
      incoming = list(params.items())
   else:
      incoming = list(params)
   for item in incoming:
      if len(item) != 2:
         raise ValueError("params must be a mapping or an iterable of (key, value) pairs")
      key, value = item
      if key is None or str(key).strip() == "":
         raise ValueError("parameter keys must be non-empty")
      resolved.append((str(key), "" if value is None else str(value)))

   # Preserve the position of file-defined keys while allowing later values to win.
   merged = {}
   order = []
   for key, value in resolved:
      if key not in merged:
         order.append(key)
      merged[key] = value
   return [(key, merged[key]) for key in order]


def normalize_result_table(df, record_id):
   if df is None:
      return None
   out = df.copy()
   record_id = "" if record_id is None else str(record_id)
   if "ID" not in out.columns:
      out.insert(0, "ID", record_id)
      return out
   try:
      id_col = out["ID"]
      missing = id_col.isna()
      if hasattr(id_col, "astype"):
         missing = missing | id_col.astype(str).str.strip().eq("")
      if missing.any():
         out.loc[missing, "ID"] = record_id
   except Exception:
      pass
   cols = ["ID"] + [col for col in out.columns if col != "ID"]
   return out.loc[:, cols]


def project_eval_slices(tasks, workers, batch_size=None):
   if not tasks:
      return []
   workers = clamp_workers(workers, len(tasks))
   if batch_size is None:
      chunk_size = max(1, (len(tasks) + workers - 1) // workers)
   else:
      try:
         chunk_size = int(batch_size)
      except (TypeError, ValueError):
         chunk_size = 1
      chunk_size = max(1, chunk_size)
   chunks = []
   for chunk_index, start in enumerate(range(0, len(tasks), chunk_size), start=1):
      records = tasks[start:start + chunk_size]
      if not records:
         continue
      chunks.append({
         "slice_index": chunk_index,
         "start_ordinal": records[0]["ordinal"],
         "end_ordinal": records[-1]["ordinal"],
         "rows": [list(record["sample_row"]) for record in records],
         "records": records,
      })
   return chunks


def normalize_sample_row(row) -> list[str]:
   out = []
   for value in row:
      if value is None:
         out.append("")
      elif isinstance(value, set):
         out.append(",".join(str(item) for item in sorted(value)))
      elif isinstance(value, (list, tuple)):
         out.append(",".join(str(item) for item in value))
      else:
         out.append(str(value))
   return out


def _init_child_project():
   global _CHILD_PROJ
   import lunapi as lp

   _CHILD_PROJ = lp.proj(verbose=False)
   _CHILD_PROJ.silence(True)


def _run_record(proj, record):
   ordinal = record["ordinal"]
   sample_row = record["sample_row"]
   label = record["label"]
   cmd = record["cmd"]
   params = record["params"]
   id_str = str(sample_row[0] or "").strip()
   stdout_txt = ""
   try:
      proj.clear_vars()
      proj.reinit()
      for key, value in params:
         proj.var(key, value)

      try:
         p = proj.inst(id_str)
      except NameError:
         from lunapi.instance import inst as _inst
         p = _inst(proj.eng.inst(id_str))
      stdout_txt = p.eval_lunascope(cmd) or ""

      tbls = p.strata()
      tree_tbls = None
      results = {}
      if tbls is not None:
         tree_tbls = tbls[["Command", "Strata"]].copy()
         for row in tbls.itertuples(index=False):
            key = _table_key(row.Command, row.Strata)
            df = normalize_result_table(p.table(row.Command, row.Strata), id_str)
            if df is not None:
               results[key] = df

      try:
         p.silent_proc("REPORT show-all")
      except RuntimeError:
         pass

      return {
         "ordinal": ordinal,
         "label": label,
         "id": id_str,
         "slice_index": record.get("slice_index"),
         "stdout": stdout_txt,
         "tbls": tree_tbls,
         "results": results,
         "error": None,
         "traceback": None,
      }
   except Exception as exc:
      return {
         "ordinal": ordinal,
         "label": label,
         "id": id_str,
         "slice_index": record.get("slice_index"),
         "stdout": stdout_txt,
         "tbls": None,
         "results": {},
         "error": f"{type(exc).__name__}: {exc}",
         "traceback": traceback.format_exc(),
      }


def _slice_worker(task):
   global _CHILD_PROJ
   if _CHILD_PROJ is None:
      _init_child_project()
   proj = _CHILD_PROJ
   rows = task["rows"]
   records = task["records"]
   try:
      proj.clear()
      proj.eng.set_sample_list(rows)
      results = []
      for record in records:
         record = dict(record)
         record["slice_index"] = task["slice_index"]
         result = _run_record(proj, record)
         results.append(result)
      return {
         "slice_index": task["slice_index"],
         "start_ordinal": task["start_ordinal"],
         "end_ordinal": task["end_ordinal"],
         "results": results,
      }
   finally:
      try:
         proj.clear()
      except Exception:
         pass


def _run_record_file(proj, record):
   """Run one record writing output to a file; no in-memory result collection."""
   ordinal = record["ordinal"]
   sample_row = record["sample_row"]
   label = record["label"]
   cmd = record["cmd"]
   params = record["params"]
   id_str = str(sample_row[0] or "").strip()
   try:
      proj.clear_vars()
      proj.reinit()
      for key, value in params:
         proj.var(key, value)
      try:
         p = proj.inst(id_str)
      except NameError:
         from lunapi.instance import inst as _inst
         p = _inst(proj.eng.inst(id_str))
      p.edf.eval_file(cmd)
      return {
         "ordinal": ordinal,
         "label": label,
         "id": id_str,
         "slice_index": record.get("slice_index"),
         "stdout": "",
         "tbls": None,
         "results": {},
         "error": None,
         "traceback": None,
      }
   except Exception as exc:
      return {
         "ordinal": ordinal,
         "label": label,
         "id": id_str,
         "slice_index": record.get("slice_index"),
         "stdout": "",
         "tbls": None,
         "results": {},
         "error": f"{type(exc).__name__}: {exc}",
         "traceback": traceback.format_exc(),
      }


def _slice_worker_file(task):
   """Slice worker that writes results to a file (out_db or out_text mode)."""
   global _CHILD_PROJ
   if _CHILD_PROJ is None:
      _init_child_project()
   proj = _CHILD_PROJ
   rows = task["rows"]
   records = task["records"]
   out_db = task.get("out_db")
   out_text = task.get("out_text")
   slice_idx = task["slice_index"]

   if out_db:
      out_path = f"{out_db}-{slice_idx}.db"
      proj.eng.output_attach(out_path)
   else:
      out_path = out_text  # all workers share same folder; rows are keyed by ID
      proj.eng.output_plaintext(out_path)

   try:
      proj.clear()
      proj.eng.set_sample_list(rows)
      results = []
      for record in records:
         record = dict(record)
         record["slice_index"] = slice_idx
         result = _run_record_file(proj, record)
         results.append(result)
      return {
         "slice_index": slice_idx,
         "start_ordinal": task["start_ordinal"],
         "end_ordinal": task["end_ordinal"],
         "out_path": out_path,
         "results": results,
      }
   finally:
      try:
         proj.eng.output_close()
      except Exception:
         pass
      try:
         proj.clear()
      except Exception:
         pass


def _create_process_pool(workers, mp_context):
   kwargs = {
      "max_workers": workers,
      "mp_context": mp_context,
      "initializer": _init_child_project,
   }
   try:
      return ProcessPoolExecutor(**kwargs)
   except PermissionError:
      real_sysconf = getattr(os, "sysconf", None)
      if real_sysconf is None:
         raise

      def safe_sysconf(name):
         if name == "SC_SEM_NSEMS_MAX":
            return -1
         return real_sysconf(name)

      os.sysconf = safe_sysconf
      try:
         return ProcessPoolExecutor(**kwargs)
      finally:
         os.sysconf = real_sysconf


def run_parallel_project(
   project,
   cmdstr: str,
   *,
   workers=None,
   batch_size=None,
   params=None,
   param_file=None,
   strict: bool = False,
   progress=None,
   out_db=None,
   out_text=None,
   in_memory=None,
   n1=None,
   n2=None,
   ids=None,
   skip=None,
) -> ParallelProcResult:
   import multiprocessing

   if out_db and out_text:
      raise ValueError("out_db and out_text are mutually exclusive")
   file_mode = bool(out_db or out_text)
   if in_memory is None:
      in_memory = not file_mode
   if in_memory and file_mode:
      raise ValueError(
         "Simultaneous in_memory and file output is not supported; pass in_memory=False"
      )

   sample_list = project.sample_list(df=False)
   if not sample_list:
      result = ParallelProcResult(
         tables={},
         errors=_errors_frame([]),
         stdout=_stdout_frame([]),
         records=_records_frame([]),
         workers=0,
      )
      if strict:
         raise ParallelProcError("parallel processing failed: no records in sample list", result)
      return result

   resolved_params = resolve_params(params=params, param_file=param_file)
   if batch_size is None and progress is True and not file_mode:
      batch_size = 1

   tasks = [
      {
         "ordinal": idx,
         "sample_row": normalize_sample_row(row),
         "label": str(row[0] or "").strip(),
         "cmd": cmdstr,
         "params": resolved_params,
      }
      for idx, row in enumerate(sample_list, start=1)
      if str(row[0] or "").strip()
   ]

   # --- row-range and ID filtering (mirrors luna n1/n2 and id=/skip= args) ---
   if n1 is not None or n2 is not None:
      lo = n1 if n1 is not None else 1
      hi = n2 if n2 is not None else (tasks[-1]["ordinal"] if tasks else 0)
      tasks = [t for t in tasks if lo <= t["ordinal"] <= hi]

   if ids is not None:
      if isinstance(ids, str):
         ids = ids.split()
      ids_set = set(ids)
      tasks = [t for t in tasks if t["label"] in ids_set]

   if skip is not None:
      if isinstance(skip, str):
         skip = skip.split()
      skip_set = set(skip)
      tasks = [t for t in tasks if t["label"] not in skip_set]
   # --------------------------------------------------------------------------

   # Clamp workers to the actual number of tasks after filtering
   workers = clamp_workers(workers, len(tasks))
   slices = project_eval_slices(tasks, workers, batch_size=batch_size)

   completed = []
   completed_ordinals = set()
   executor = None
   pending = {}
   pool_error = None
   progress_callback, close_progress = _coerce_progress(progress, len(tasks))

   def emit(event):
      if progress_callback is not None:
         progress_callback(event)

   def handle_record_result(result):
      ordinal = result.get("ordinal")
      if ordinal in completed_ordinals:
         return
      completed_ordinals.add(ordinal)
      completed.append(result)
      emit({
         "event": "record",
         "ordinal": ordinal,
         "total": len(tasks),
         "id": result.get("id"),
         "error": result.get("error"),
      })

   worker_fn = _slice_worker_file if file_mode else _slice_worker
   collected_out_paths = []

   def handle_slice_result(slice_result):
      if "out_path" in slice_result:
         collected_out_paths.append(slice_result["out_path"])
      for result in slice_result.get("results", []):
         handle_record_result(result)

   try:
      mp_context = multiprocessing.get_context("spawn")
      executor = _create_process_pool(workers, mp_context)
      for task_slice in slices:
         submitted_slice = dict(task_slice)
         if file_mode:
            submitted_slice["out_db"] = out_db
            submitted_slice["out_text"] = out_text
         fut = executor.submit(worker_fn, submitted_slice)
         pending[fut] = task_slice
         emit({
            "event": "slice_queued",
            "slice_index": task_slice["slice_index"],
            "start_ordinal": task_slice["start_ordinal"],
            "end_ordinal": task_slice["end_ordinal"],
         })

      while pending:
         done_futs, _ = wait(pending.keys(), timeout=0.2, return_when=FIRST_COMPLETED)
         if not done_futs:
            continue
         for fut in done_futs:
            task_slice = pending.pop(fut)
            try:
               slice_result = fut.result()
            except Exception as exc:
               tb = traceback.format_exc()
               slice_result = {
                  "slice_index": task_slice["slice_index"],
                  "results": [
                     _synthetic_error_result(record, task_slice["slice_index"], exc, tb)
                     for record in task_slice["records"]
                  ],
               }
            handle_slice_result(slice_result)
   except Exception as exc:
      pool_error = (exc, traceback.format_exc())
   finally:
      if executor is not None:
         executor.shutdown(wait=True, cancel_futures=True)

   missing = [record for record in tasks if record["ordinal"] not in completed_ordinals]
   if pool_error is not None:
      exc, tb = pool_error
      for record in missing:
         handle_record_result(_synthetic_error_result(record, None, exc, tb))
   else:
      for record in missing:
         handle_record_result(_synthetic_missing_result(record))

   if file_mode:
      result = _collate_file_results(completed, workers, collected_out_paths)
   else:
      result = _collate_results(completed, workers, project)
   close_progress()
   n_total = len(result.records)
   n_errors = len(result.errors)
   if file_mode:
      paths_str = ", ".join(str(p) for p in result._out_paths) or "(none)"
      if result.ok:
         print(f"lunapi: completed successfully ({n_total} record(s), files: {paths_str})")
      else:
         print(f"lunapi: completed with {n_errors} error(s) out of {n_total} record(s), files: {paths_str}")
   else:
      n_tables = len(result)
      if result.ok:
         print(f"lunapi: completed successfully ({n_total} record(s), {n_tables} table(s))")
      else:
         print(f"lunapi: completed with {n_errors} error(s) out of {n_total} record(s)")
   if strict and not result.ok:
      raise ProcError(
         f"parallel processing failed for {n_errors} record(s)",
         result,
      )
   return result


def _coerce_progress(progress, total):
   if progress is None or progress is False:
      return None, lambda: None
   if callable(progress):
      return progress, lambda: None
   if progress is not True:
      raise ValueError("progress must be True, False, None, or a callable")

   try:
      from tqdm.auto import tqdm
   except Exception:
      done = {"n": 0, "errors": 0}

      def print_progress(event):
         if event.get("event") != "record":
            return
         done["n"] += 1
         if event.get("error"):
            done["errors"] += 1
         print(f"lunapi: {done['n']} / {total} records, errors={done['errors']}")

      return print_progress, lambda: None

   bar = tqdm(total=total, desc="lunapi", unit="record")
   errors = {"n": 0}

   def update_bar(event):
      if event.get("event") != "record":
         return
      if event.get("error"):
         errors["n"] += 1
         bar.set_postfix(errors=errors["n"])
      bar.update(1)

   return update_bar, bar.close


def _synthetic_error_result(record, slice_index, exc, tb):
   return {
      "ordinal": record["ordinal"],
      "label": record["label"],
      "id": str(record["sample_row"][0] or "").strip(),
      "slice_index": slice_index,
      "stdout": "",
      "tbls": None,
      "results": {},
      "error": f"{type(exc).__name__}: {exc}",
      "traceback": tb,
   }


def _synthetic_missing_result(record):
   return {
      "ordinal": record["ordinal"],
      "label": record["label"],
      "id": str(record["sample_row"][0] or "").strip(),
      "slice_index": record.get("slice_index"),
      "stdout": "",
      "tbls": None,
      "results": {},
      "error": "RuntimeError: record did not return a result",
      "traceback": None,
   }


def _collate_results(completed, workers, project) -> ProcResult:
   completed = sorted(completed, key=lambda item: item.get("ordinal", 0))
   result_parts = {}
   for result in completed:
      for key, df in (result.get("results") or {}).items():
         if df is not None:
            result_parts.setdefault(key, []).append(df)
   for key, parts in result_parts.items():
      if not parts:
         continue
      df = pd.concat(parts, ignore_index=True)
      for col in df.columns:
         if "ID" not in col.split("_"):
            try:
               df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
               pass
      cmd, strata = key.split(": ", 1)
      project.eng.inject_table(cmd, strata, df.columns.tolist(),
                               [df[col].tolist() for col in df.columns])
   return ProcResult(
      _owner=project,
      errors=_errors_frame(completed),
      stdout=_stdout_frame(completed),
      records=_records_frame(completed),
      workers=workers,
   )


def _collate_file_results(completed, workers, out_paths) -> ProcResult:
   """Collate results for file-output mode — no table injection into project cache."""
   completed = sorted(completed, key=lambda item: item.get("ordinal", 0))
   return ProcResult(
      _owner=None,
      _out_paths=list(dict.fromkeys(out_paths)),  # deduplicate (text mode shares one folder)
      errors=_errors_frame(completed),
      stdout=_stdout_frame(completed),
      records=_records_frame(completed),
      workers=workers,
   )


# ── Text-output reader helpers ──────────────────────────────────────────────

def _parse_txt_filename(fname: str):
   """Parse 'CMD_F1_F2.txt[.gz]' → (cmd, [f1, f2]), or None if not recognised."""
   for ext in ('.txt.gz', '.txt'):
      if fname.endswith(ext):
         parts = fname[:-len(ext)].split('_')
         return parts[0], parts[1:]
   return None


def _candidate_filenames(cmd: str, factors):
   """Yield candidate filenames for cmd+factors: exact order first, then all permutations."""
   factors = list(factors)
   seen = set()
   orderings = list(itertools.permutations(factors)) if len(factors) > 1 else [factors]
   for ordering in orderings:
      stem = '_'.join([cmd] + list(ordering))
      for ext in ('.txt', '.txt.gz'):
         name = stem + ext
         if name not in seen:
            seen.add(name)
            yield name


def list_text_tables(path, id=None) -> pd.DataFrame:
   """List available tables in a Luna ``-t`` text-output folder.

   Inspects one individual subdirectory and returns a summary of
   available command/strata combinations based on the filenames present.

   Parameters
   ----------
   path : str or Path
      Root folder passed as ``out_text``.
   id : str, optional
      Individual ID (subdirectory name) to inspect.  Defaults to the
      first subdirectory in sorted order.

   Returns
   -------
   pd.DataFrame
      Columns: ``command``, ``strata``, ``file``.
      ``strata`` is ``'BL'`` for the baseline (no factors) or the factor
      name(s) joined by ``'_'`` (e.g. ``'CH'``, ``'B_CH'``).
   """
   root = Path(path)
   if not root.exists():
      raise FileNotFoundError(f"Text output folder not found: {root}")

   if id is not None:
      target = root / id
      if not target.is_dir():
         raise FileNotFoundError(f"Individual folder not found: {target}")
   else:
      subdirs = sorted(d for d in root.iterdir() if d.is_dir())
      if not subdirs:
         raise FileNotFoundError(f"No individual subdirectories in: {root}")
      target = subdirs[0]

   rows = []
   for f in sorted(target.iterdir()):
      parsed = _parse_txt_filename(f.name)
      if parsed is None:
         continue
      cmd, factors = parsed
      rows.append({
         'command': cmd,
         'strata':  '_'.join(factors) if factors else 'BL',
         'file':    f.name,
      })

   if not rows:
      return pd.DataFrame(columns=['command', 'strata', 'file'])

   return (
      pd.DataFrame(rows)
      .sort_values(['command', 'strata'])
      .reset_index(drop=True)
   )


def read_text_table(path, cmd_or_file, factors=None) -> pd.DataFrame:
   """Read a concatenated text-output table from a Luna ``-t`` directory.

   Finds every per-individual file that matches the requested
   command/strata combination and concatenates them into a single
   DataFrame — equivalent to::

      awk 'NR==1 || FNR!=1' path/*/COMMAND_FACTOR.txt

   Factor ordering in the filename is handled automatically; both ``.txt``
   and ``.txt.gz`` files are supported.

   Parameters
   ----------
   path : str or Path
      Root folder passed as ``out_text``.
   cmd_or_file : str, tuple, or list
      One of:

      * A bare command name: ``'HEADERS'`` (baseline strata)
      * A filename:          ``'HEADERS_CH.txt'`` or ``'HEADERS_CH.txt.gz'``
      * A sequence:          ``('HEADERS', 'CH')`` or ``['HEADERS', ['B','CH']]``

   factors : str or list of str, optional
      Factor(s) when *cmd_or_file* is a plain command name, e.g.
      ``factors='CH'`` or ``factors=['B', 'CH']``.

   Returns
   -------
   pd.DataFrame
   """
   root = Path(path)

   # ── resolve to (cmd, facs) ───────────────────────────────────────────
   if isinstance(cmd_or_file, (list, tuple)):
      parts = list(cmd_or_file)
      if len(parts) >= 2 and isinstance(parts[1], (list, tuple)):
         cmd, facs = parts[0], list(parts[1])
      else:
         cmd, facs = parts[0], parts[1:]
   elif str(cmd_or_file).endswith(('.txt', '.txt.gz')):
      parsed = _parse_txt_filename(Path(cmd_or_file).name)
      if parsed is None:
         raise ValueError(f"Unrecognised extension: {cmd_or_file!r}")
      cmd, facs = parsed
   else:
      cmd = str(cmd_or_file)
      facs = ([factors] if isinstance(factors, str) else list(factors)) if factors else []

   # ── find first set of matching files across all individuals ──────────
   matches = []
   matched_name = None
   for candidate in _candidate_filenames(cmd, facs):
      found = sorted(root.glob(f"*/{candidate}"))
      if found:
         matches, matched_name = found, candidate
         break

   if not matches:
      strata_label = '_'.join(facs) if facs else 'BL'
      msg = f"No files found for command='{cmd}', strata='{strata_label}' under {root}"
      try:
         avail = list_text_tables(root)
         if not avail.empty:
            msg += f"\nAvailable:\n{avail.to_string(index=False)}"
      except Exception:
         pass
      raise FileNotFoundError(msg)

   # ── concatenate, skipping unreadable files with a warning ────────────
   dfs = []
   for f in matches:
      try:
         dfs.append(pd.read_csv(f, sep='\t', compression='infer'))
      except Exception as exc:
         warnings.warn(f"Skipping {f}: {exc}")

   if not dfs:
      raise ValueError(f"All files matching '{matched_name}' were unreadable")

   return pd.concat(dfs, ignore_index=True)


class _ErrorsFrame(pd.DataFrame):
   """Errors DataFrame that stays silent when empty."""

   @property
   def _constructor(self):
      return _ErrorsFrame

   def _repr_html_(self):
      if len(self) == 0:
         return None
      return super()._repr_html_()

   def __repr__(self):
      if len(self) == 0:
         return ""
      return super().__repr__()


def _errors_frame(results):
   rows = [
      {
         "Ordinal": result.get("ordinal"),
         "ID": result.get("id"),
         "Label": result.get("label"),
         "Slice": result.get("slice_index"),
         "Error": result.get("error"),
         "Traceback": result.get("traceback"),
      }
      for result in results
      if result.get("error")
   ]
   return _ErrorsFrame(rows, columns=["Ordinal", "ID", "Label", "Slice", "Error", "Traceback"])


def _stdout_frame(results):
   rows = [
      {
         "Ordinal": result.get("ordinal"),
         "ID": result.get("id"),
         "Stdout": result.get("stdout") or "",
      }
      for result in results
      if result.get("stdout")
   ]
   return pd.DataFrame(rows, columns=["Ordinal", "ID", "Stdout"])


def _records_frame(results):
   rows = [
      {
         "Ordinal": result.get("ordinal"),
         "ID": result.get("id"),
         "Label": result.get("label"),
         "Slice": result.get("slice_index"),
         "OK": not bool(result.get("error")),
      }
      for result in results
   ]
   return pd.DataFrame(rows, columns=["Ordinal", "ID", "Label", "Slice", "OK"])


__all__ = [
   "FileOutputModeError",
   "ParallelProcError",
   "ParallelProcResult",
   "ProcError",
   "ProcResult",
   "clamp_workers",
   "coerce_strata",
   "default_workers",
   "list_text_tables",
   "normalize_result_table",
   "normalize_sample_row",
   "parse_param_file",
   "parse_param_text",
   "project_eval_slices",
   "read_text_table",
   "resolve_params",
   "run_parallel_project",
   "tokenize_param_line",
]
