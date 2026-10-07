"""Tests: Module Manager — discovery, ordre topo, cycles, enable/disable, status."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import module_manager as mm


def test_discover_has_core_four():
    names = {m["name"] for m in mm.discover()}
    assert {"system", "identity", "dns", "network"} <= names


def test_resolve_order_network_before_dns():
    order = mm.resolve_order([m for m in mm.discover() if "error" not in m])
    assert order.index("network") < order.index("dns")


def test_resolve_order_cycle():
    bad = [{"name": "a", "requires": ["b"]}, {"name": "b", "requires": ["a"]}]
    try:
        mm.resolve_order(bad)
    except ValueError as e:
        assert "cycle" in str(e)
        return
    raise AssertionError("cycle aurait du lever")


def test_resolve_order_unknown_dep():
    try:
        mm.resolve_order([{"name": "a", "requires": ["ghost"]}])
    except ValueError:
        return
    raise AssertionError("dependance inconnue aurait du lever")


def test_enable_disable_persist_tmp(tmp_path):
    dd = str(tmp_path)
    mm.enable("dns", actor="test", data_dir=dd)
    assert mm.status("dns", data_dir=dd)["enabled"] is True
    # dns requis par domain (actif par defaut) : desactiver domain d'abord
    mm.disable("domain", actor="test", data_dir=dd)
    mm.disable("dns", actor="test", data_dir=dd)
    assert mm.status("dns", data_dir=dd)["enabled"] is False
    mm.enable("dns", actor="test", data_dir=dd)
    mm.enable("domain", actor="test", data_dir=dd)


def test_disable_refused_when_dependent(tmp_path):
    dd = str(tmp_path)
    mm.enable("dns", actor="test", data_dir=dd)  # active network via requires
    try:
        mm.disable("network", actor="test", data_dir=dd)
    except ValueError as e:
        assert "requis par" in str(e)
        return
    raise AssertionError("disable aurait du etre refuse")


def test_status_shape():
    st = mm.status("system")
    for k in ("name", "display_name", "description", "enabled", "installed",
              "running", "services", "packages", "dependencies", "requires", "managed"):
        assert k in st, k
    assert st["display_name"] and st["version"]


def test_manifest_spec_aliases(tmp_path, monkeypatch):
    # format spec point 7 : display_name + dependencies + enabled
    d = tmp_path / "mymod"
    d.mkdir()
    (d / "manifest.yaml").write_text(
        "name: mymod\ndisplay_name: My Module\nversion: 0.1.0\n"
        "description: spec format\nenabled: false\n"
        "dependencies: [core]\nservices: [cron]\n")
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "manifest.yaml").write_text(
        "name: core\nversion: 0.1.0\nservices: []\npackages: []\n")
    monkeypatch.setenv("INFRAOS_MODULES_DIR", str(tmp_path))
    mods = {m["name"]: m for m in mm.discover(tmp_path)}
    assert mods["mymod"]["title"] == "My Module"
    assert mods["mymod"]["requires"] == ["core"]
    assert mm.status("mymod", data_dir=str(tmp_path))["enabled"] is False
    deps = mm.dependencies("mymod", data_dir=str(tmp_path))
    assert deps["satisfied"] is True
    assert mm.resolve_order([m for m in mm.discover(tmp_path) if "error" not in m]).index("core") == 0


def test_uninstall_no_packages_safe(tmp_path):
    dd = str(tmp_path)
    mm.disable("fileshare", actor="test", data_dir=dd)
    out = mm.uninstall("identity", actor="test", data_dir=dd)
    assert out["uninstall"]["removed"] == []
    assert out["enabled"] is False
    mm.enable("identity", actor="test", data_dir=dd)
    mm.enable("fileshare", actor="test", data_dir=dd)


def test_uninstall_refused_when_dependent(tmp_path):
    dd = str(tmp_path)
    try:
        mm.uninstall("network", actor="test", data_dir=dd)
    except ValueError as e:
        assert "requis par" in str(e)
        return
    raise AssertionError("uninstall aurait du etre refuse")
