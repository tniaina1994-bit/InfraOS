"""Tests: agent de reference (collecte locale, config) — sans serveur."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))


def test_collect_shape():
    import infraos_agent as ag
    m = ag.collect()
    assert {"cpu", "mem", "disk", "uptime", "os_info"} <= set(m)


def test_load_config(tmp_path):
    import infraos_agent as ag
    p = tmp_path / "agent.yaml"
    p.write_text('server: https://x\ntoken: "tok123"\n# commentaire\n')
    cfg = ag.load_config(str(p))
    assert cfg["server"] == "https://x" and cfg["token"] == "tok123"


def test_load_config_missing_token(tmp_path):
    import infraos_agent as ag
    p = tmp_path / "agent.yaml"
    p.write_text("server: https://x\n")
    try:
        ag.load_config(str(p))
    except SystemExit as e:
        assert e.code == 2
        return
    raise AssertionError("token manquant aurait du sortir en 2")
