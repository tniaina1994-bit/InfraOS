"""Runtime detection: container vs VM vs bare-metal. Never assume LXC."""
from __future__ import annotations
from .exec import run


def detect_virt() -> str:
    r = run("systemd-detect-virt", caller="detect")
    if r.rc == 127:
        return "unknown"  # binaire absent (dev Windows)
    v = r.out.strip()
    return v if v else "none"


def is_container(virt: str | None = None) -> bool:
    v = (virt or detect_virt()).lower()
    return v in ("lxc", "lxc-libvirt", "openvz", "docker", "podman", "systemd-nspawn")


def firewall_full_support() -> tuple[bool, str]:
    """LXC unprivileged often lacks full nftables/kernel control."""
    virt = detect_virt()
    if virt == "lxc":
        return False, "LXC: firewall en mode degrade (regles hotes via Proxmox). Full support sur ISO bare-metal/VM."
    if is_container(virt):
        return False, f"Conteneur ({virt}): firewall degrade."
    return True, "OK"
