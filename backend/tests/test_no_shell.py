"""Tests: aucun shell arbitraire — shell=False partout, pas de shell=True/os.system."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # racine infraOS
CORE = ROOT / "backend" / "app" / "core" / "infraos"
API = ROOT / "backend" / "app" / "api"
FORBIDDEN = ["shell=True", "os.system", "eval("]


def test_no_forbidden_patterns():
    import re
    hits = []
    targets = list(CORE.rglob("*.py")) + list(API.rglob("*.py"))
    for p in targets:
        if "tests" in p.parts or "__pycache__" in p.parts:
            continue
        txt = p.read_text(errors="ignore")
        for pat in [r"shell\s*=\s*True", r"os\.system\s*\(", r"eval\s*\("]:
            if re.search(pat, txt):
                hits.append(f"{p}:{pat}")
        if "Popen" in txt:
            hits.append(f"{p}:Popen")
    assert not hits, f"motifs interdits: {hits}"


def test_subprocess_only_in_exec():
    import re
    allowed = {CORE / "exec.py", CORE / "updates.py", CORE / "apt.py",
               CORE / "nft.py", CORE / "wireguard.py", CORE / "backup.py"}
    bad = []
    for p in CORE.rglob("*.py"):
        if p in allowed or "tests" in p.parts or "__pycache__" in p.parts:
            continue
        if re.search(r"^\s*(import subprocess|from.*subprocess)", p.read_text(), re.M):
            bad.append(str(p))
    assert not bad, f"subprocess hors exec/updates: {bad}"
