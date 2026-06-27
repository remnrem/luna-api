"""Package-level and C++ extension smoke tests — no EDF file needed."""

import re
import pytest


def test_package_importable():
    import lunapi  # noqa: F401


def test_version_string():
    import lunapi
    assert isinstance(lunapi.__version__, str)
    assert re.match(r"\d+\.\d+\.\d+", lunapi.__version__)


def test_lp_version_matches():
    import lunapi
    from lunapi.resources import lp_version
    assert lp_version == lunapi.__version__


def test_fetch_doms_nonempty():
    from lunapi.results import fetch_doms
    doms = fetch_doms()
    assert isinstance(doms, list) and len(doms) > 0


def test_fetch_cmds_power_contains_psd():
    from lunapi.results import fetch_cmds
    assert "PSD" in fetch_cmds("power")


def test_fetch_params_psd_contains_sig():
    from lunapi.results import fetch_params
    assert "sig" in fetch_params("PSD")


def test_proj_instantiates():
    from lunapi import proj
    p = proj(verbose=False)
    assert p is not None


def test_proj_vars_coerce_bool_to_numeric_strings():
    from lunapi import proj
    p = proj(verbose=False)
    p.clear_vars()
    p.vars({"truthy": True, "falsey": False, "threshold": 1.25})
    assert p.vars("truthy") == "1"
    assert p.vars("falsey") == "0"
    assert p.vars("threshold") == "1.25"
    p.clear_vars()


def test_inst_requires_path():
    from lunapi import inst
    with pytest.raises(TypeError):
        inst()
