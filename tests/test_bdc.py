from __future__ import annotations

import hashlib

from lunapi.bdc import BDCClient


class FakeResponse:
    def __init__(self, payload=None, content=b"", status_code=200, headers=None):
        self._payload = payload
        self._content = content
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=1024):
        del chunk_size
        yield self._content


class FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if url.endswith("access_token"):
            return FakeResponse({"access_token": "temporary-token"})
        return FakeResponse({"data": {"datanode": [{
            "object_id": "edf-guid", "file_name": "subject-01.edf", "file_size": 4,
        }, {
            "object_id": "ann-guid", "file_name": "subject-01.annot", "file_size": 2,
        }]}})

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return FakeResponse(content=b"data", headers={"Content-Length": "4"})


class TokenSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/projects"):
            return FakeResponse({"items": [{"id": "project-a"}]})
        if url.endswith("/files"):
            return FakeResponse({"items": [{
                "id": "file-a", "name": "subject.edf", "size": 4,
            }]})
        if url.endswith("/download_info"):
            return FakeResponse({"url": "https://download.test/file-a"})
        return FakeResponse(content=b"data", headers={"Content-Length": "4"})


class NestedSession(TokenSession):
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        params = kwargs.get("params", {})
        if url.endswith("/files") and params.get("parent") == "folder-a":
            return FakeResponse({"items": [
                {"id": "nested-edf", "name": "subject.edf", "size": 4},
                {"id": "nested-xml", "name": "subject-nsrr.xml", "size": 2},
            ]})
        if url.endswith("/files"):
            return FakeResponse({"items": [{
                "id": "folder-a", "name": "visit-1", "type": "FOLDER",
            }]})
        return super().get(url, **kwargs)


def test_bdc_authenticates_and_groups_recordings():
    session = FakeSession()
    client = BDCClient("https://example.test", "key-id", "api-key", "project", session)

    groups = client.recording_groups()

    assert len(groups) == 1
    assert groups[0]["recording"]["guid"] == "edf-guid"
    assert groups[0]["sidecars"][0]["guid"] == "ann-guid"
    assert session.posts[0][1]["json"] == {"key_id": "key-id", "api_key": "api-key"}


def test_bdc_download_skips_complete_file(tmp_path):
    session = FakeSession()
    client = BDCClient("https://example.test", "key-id", "api-key", session=session)
    content = b"data"
    record = {
        "guid": "edf-guid", "name": "subject.edf", "size": len(content),
        "md5": hashlib.md5(content).hexdigest(),
    }
    target = tmp_path / "subject.edf"
    target.write_bytes(content)

    assert client.download(record, tmp_path) == target
    assert not any(url.endswith("/data/edf-guid") for url, _ in session.gets)


def test_bdc_download_writes_and_verifies_file(tmp_path):
    session = FakeSession()
    client = BDCClient("https://example.test", "key-id", "api-key", session=session)
    record = {"guid": "edf-guid", "name": "subject.edf", "size": 4,
              "md5": hashlib.md5(b"data").hexdigest()}

    target = client.download(record, tmp_path)

    assert target.read_bytes() == b"data"


def test_bdc_seven_bridges_token_lists_and_downloads(tmp_path):
    session = TokenSession()
    client = BDCClient(
        "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2",
        project="project-a", token="single-token", session=session,
    )

    assert client.projects() == ["project-a"]
    record = client.files()[0]
    target = client.download(record, tmp_path)

    assert target.read_bytes() == b"data"
    assert session.calls[0][1]["headers"]["X-SBG-Auth-Token"] == "single-token"


def test_bdc_recurses_into_folders_and_pairs_nsrr_xml():
    client = BDCClient(
        "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2",
        project="project-a", token="single-token", session=NestedSession(),
    )

    groups = client.recording_groups()

    assert groups[0]["recording"]["path"] == "visit-1/subject.edf"
    assert groups[0]["sidecars"][0]["path"] == "visit-1/subject-nsrr.xml"
