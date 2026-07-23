"""Small Python client for files stored in a Gen3/BioData Catalyst commons.

The client deliberately deals in file-index records rather than depending on
the external ``gen3-client`` executable.  This keeps it usable by notebooks
and desktop applications alike while allowing each Gen3 deployment to supply
its own endpoint and project identifier.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time
from typing import Callable

import requests


_DEFAULT_ENDPOINT = "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2"
_TOKEN_TTL = 25 * 60
_EDF_RE = re.compile(r"\.(?:edf|edf\.gz|edfz)$", re.IGNORECASE)
_SIDECAR_RE = re.compile(r"\.(?:annot|xml|eannot|tsv|idx)$", re.IGNORECASE)


def _clean_endpoint(endpoint: str) -> str:
    endpoint = str(endpoint or _DEFAULT_ENDPOINT).strip()
    if not endpoint:
        raise ValueError("A Gen3 endpoint is required.")
    return endpoint.rstrip("/")


def _first(mapping: dict, *keys, default=None):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return default


class BDCClient:
    """Authenticated file browser/downloader for a Gen3 commons.

    Parameters
    ----------
    endpoint : str
        Base URL of the Gen3 commons.
    key_id, api_key : str
        API-key pair created by the commons Profile page.
    project : str, optional
        Project identifier used by :meth:`files` when supplied.
    session : requests.Session, optional
        Injectable HTTP session for tests or callers with custom TLS setup.
    """

    def __init__(self, endpoint=_DEFAULT_ENDPOINT, key_id=None, api_key=None,
                 project=None, session=None, token=None):
        self.endpoint = _clean_endpoint(endpoint)
        self.key_id = str(key_id or "").strip()
        self.api_key = str(api_key or "").strip()
        self.project = str(project or "").strip() or None
        self.token = str(token or "").strip() or None
        self.session = session or requests.Session()
        self._access_token = None
        self._token_expires = 0.0

    @property
    def authenticated(self) -> bool:
        return bool(self._access_token and time.time() < self._token_expires)

    def authenticate(self) -> str:
        if self.token:
            return self.token
        if not self.key_id or not self.api_key:
            raise ValueError("Both a Gen3 key ID and API key are required.")
        url = f"{self.endpoint}/user/credentials/cdis/access_token"
        response = self.session.post(
            url, json={"key_id": self.key_id, "api_key": self.api_key}, timeout=60
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Gen3 authentication response did not contain an access token.")
        self._access_token = str(token)
        self._token_expires = time.time() + _TOKEN_TTL
        return self._access_token

    def _headers(self) -> dict[str, str]:
        if self.token:
            return {"X-SBG-Auth-Token": self.token, "Accept": "application/json"}
        if not self.authenticated:
            self.authenticate()
        return {"Authorization": f"bearer {self._access_token}"}

    def _get(self, path: str, **kwargs):
        response = self.session.get(
            f"{self.endpoint}/{path.lstrip('/')}",
            headers=self._headers(),
            timeout=kwargs.pop("timeout", 60),
            **kwargs,
        )
        if response.status_code == 401:
            self._access_token = None
            response = self.session.get(
                f"{self.endpoint}/{path.lstrip('/')}",
                headers=self._headers(), timeout=kwargs.pop("timeout", 60), **kwargs
            )
        response.raise_for_status()
        return response

    def projects(self) -> list[str]:
        """Return project IDs visible to the current credentials when available."""
        if self.token:
            rows = self._paged_items("projects")
            return sorted(str(row["id"]) for row in rows if isinstance(row, dict) and row.get("id"))
        query = "{project(first:0){project_id id}}"
        response = self.session.post(
            f"{self.endpoint}/api/v0/submission/graphql/",
            json={"query": query}, headers=self._headers(), timeout=60,
        )
        response.raise_for_status()
        data = response.json().get("data", {}).get("project", []) or []
        return sorted({str(_first(row, "project_id", "id")) for row in data if isinstance(row, dict)})

    def files(self, project=None) -> list[dict]:
        """Return normalized file-index records for *project*.

        Gen3 deployments expose slightly different metadata keys.  The
        normalizer accepts the common indexd fields and preserves the raw
        record under ``raw`` for callers needing deployment-specific data.
        """
        project = str(project or self.project or "").strip()
        if not project:
            raise ValueError("A BDC project identifier is required.")
        if self.token:
            rows = self._project_files_recursive(project)
            return [self._normalize_file(row, project) for row in rows if isinstance(row, dict)]
        # Gen3's supported project/file discovery interface is the GraphQL
        # datanode query.  Paginate so a large project does not require one
        # enormous response.
        rows = []
        offset = 0
        page_size = 1000
        project_literal = json.dumps(project)
        while True:
            query = """
            { datanode(first: %d, offset: %d, project_id: %s) {
                project_id object_id id md5sum file_size file_name
            } }
            """ % (page_size, offset, project_literal)
            response = self.session.post(
                f"{self.endpoint}/api/v0/submission/graphql/",
                json={"query": query}, headers=self._headers(), timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                raise RuntimeError(str(payload["errors"]))
            page = payload.get("data", {}).get("datanode", []) or []
            if not isinstance(page, list):
                page = []
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return [self._normalize_file(row, project) for row in rows if isinstance(row, dict)]

    def _paged_items(self, path: str, **params) -> list[dict]:
        """Fetch all Seven Bridges collection pages using limit/offset."""
        rows = []
        limit = 100
        offset = 0
        while True:
            query = {**params, "limit": limit, "offset": offset}
            response = self._get(path, params=query, timeout=120)
            page = response.json().get("items", []) or []
            if not isinstance(page, list):
                page = []
            rows.extend(page)
            if len(page) < limit:
                return rows
            offset += limit

    def _project_files_recursive(self, project: str) -> list[dict]:
        """Return files at every depth below a Seven Bridges project root."""
        output = []

        def visit(items, prefix=""):
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip().strip("/")
                if not name:
                    continue
                item_type = str(item.get("type") or item.get("class") or "").upper()
                is_folder = item_type in {"FOLDER", "DIRECTORY"} or bool(item.get("folder"))
                relative = "/".join(part for part in (prefix, name) if part)
                if is_folder:
                    folder_id = item.get("id") or item.get("file_id")
                    if folder_id:
                        children = self._paged_items("files", parent=folder_id)
                        visit(children, relative)
                else:
                    copied = dict(item)
                    copied["path"] = relative
                    output.append(copied)

        visit(self._paged_items("files", project=project))
        return output

    @staticmethod
    def _normalize_file(row: dict, project: str) -> dict:
        name = str(_first(row, "file_name", "filename", "name", "submitter_id", default=""))
        path = str(_first(row, "path", "file_path", default=name))
        guid = str(_first(row, "object_id", "guid", "did", "id", default=""))
        size = _first(row, "size", "file_size", default=None)
        try:
            size = int(size) if size is not None else None
        except (TypeError, ValueError):
            size = None
        return {
            "guid": guid,
            "name": name,
            "path": path,
            "size": size,
            "md5": _first(row, "md5", "md5sum", "checksum"),
            "project": project,
            "is_edf": bool(_EDF_RE.search(name)),
            "is_sidecar": bool(_SIDECAR_RE.search(name)),
            "raw": row,
        }

    def recording_groups(self, project=None) -> list[dict]:
        """Group EDF records with same-basename sidecars."""
        rows = self.files(project)
        sidecars = {}
        for row in rows:
            if row["is_sidecar"]:
                sidecars.setdefault(self._pair_key(row), []).append(row)
        grouped = []
        for row in rows:
            if not row["is_edf"]:
                continue
            grouped.append({"recording": row, "sidecars": sidecars.get(self._pair_key(row), [])})
        return grouped

    @staticmethod
    def _stem(name: str) -> str:
        lower = str(name).lower()
        for suffix in (".edf.gz", ".edfz", ".edf"):
            if lower.endswith(suffix):
                return lower[:-len(suffix)]
        return pathlib.PurePosixPath(lower).stem

    @classmethod
    def _pair_key(cls, record: dict) -> str:
        """Return a directory-aware key shared by recordings and sidecars."""
        path = str(record.get("path") or record.get("name") or "").replace("\\", "/").lower()
        if record.get("is_edf"):
            stem = cls._stem(path)
        else:
            stem = pathlib.PurePosixPath(path).with_suffix("").as_posix()
            if stem.endswith("-nsrr"):
                stem = stem[:-5]
        return stem

    def download(self, record: dict, destination: str | os.PathLike,
                 force=False, progress: Callable[[int, int], None] | None = None) -> pathlib.Path:
        """Download one normalized index record to *destination*.

        Existing files are skipped unless *force* is true.  A ``Range`` header
        resumes a partial file when the server supports it.
        """
        guid = str(record.get("guid") or record.get("object_id") or "").strip()
        if not guid:
            raise ValueError("A BDC file record must contain a GUID/object_id.")
        relative_name = str(record.get("path") or record.get("name") or guid).replace("\\", "/").lstrip("/")
        relative_name = "/".join(part for part in relative_name.split("/") if part not in ("", ".", ".."))
        target = pathlib.Path(destination) / relative_name
        name = pathlib.PurePosixPath(relative_name).name
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = record.get("size")
        if target.exists() and not force and (expected is None or target.stat().st_size == expected):
            return target

        offset = target.stat().st_size if target.exists() and not force else 0
        headers = self._headers()
        if offset:
            headers["Range"] = f"bytes={offset}-"
        response = self.session.get(
            (f"{self.endpoint}/files/{guid}/download_info" if self.token
             else f"{self.endpoint}/data/{guid}"),
            headers=headers,
            stream=True, timeout=300,
        )
        if self.token:
            response.raise_for_status()
            download_url = response.json().get("url")
            if not download_url:
                raise RuntimeError(f"BDC did not return a download URL for {name}.")
            response = self.session.get(download_url, stream=True, timeout=300)
        if response.status_code == 401:
            headers = self._headers()
            if offset:
                headers["Range"] = f"bytes={offset}-"
            response = self.session.get(f"{self.endpoint}/data/{guid}", headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        append = bool(offset and response.status_code == 206)
        if offset and not append:
            offset = 0
        total = expected or response.headers.get("Content-Length")
        total = int(total) + offset if total and append else (int(total) if total else None)
        mode = "ab" if append else "wb"
        done = offset
        with target.open(mode) as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total or done)
        if expected is not None and target.stat().st_size != int(expected):
            raise IOError(f"Downloaded size mismatch for {name}.")
        checksum = record.get("md5")
        if checksum:
            digest = hashlib.md5(target.read_bytes()).hexdigest()
            if digest.lower() != str(checksum).lower():
                raise IOError(f"Checksum mismatch for {name}.")
        return target


bdc = BDCClient

__all__ = ["BDCClient", "bdc"]
