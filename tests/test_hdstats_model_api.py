import json

from lunapi.project import proj


class FakeLunaEngine:
    def read_hdstats_pc_model(self, model_file):
        assert model_file == "model.json"
        return json.dumps({"format": "luna-hdstats-pc-api-model", "model_id": "model.json"})

    def read_hdstats_pc_descriptor(self, model_file, descriptor_file):
        assert model_file == "model.json"
        assert descriptor_file == "model.desc.json"
        return json.dumps({"components": [{"id": "PC_A_1", "orientation": -1}]})


def test_read_hdstats_pc_model_returns_normalized_dictionary(monkeypatch):
    monkeypatch.setattr(proj, "eng", FakeLunaEngine())
    api = object.__new__(proj)

    model = api.read_hdstats_pc_model("model.json")

    assert model == {"format": "luna-hdstats-pc-api-model", "model_id": "model.json"}


def test_read_hdstats_pc_descriptor_returns_core_overlay(monkeypatch):
    monkeypatch.setattr(proj, "eng", FakeLunaEngine())
    api = object.__new__(proj)

    model = api.read_hdstats_pc_descriptor("model.json", "model.desc.json")

    assert model["components"] == [{"id": "PC_A_1", "orientation": -1}]
