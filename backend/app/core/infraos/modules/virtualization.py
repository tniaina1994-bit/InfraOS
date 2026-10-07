# SPDX-License-Identifier: GPL-3.0-or-later
"""Virtualization Manager — libvirt/KVM (hote ISO ; degrade en LXC)."""
from ..module_base import SimpleServiceModule


class VirtModule(SimpleServiceModule):
    name = "virtualization"
    SERVICE = "libvirtd"
    PACKAGE = "libvirt-clients"
    PLANNED = ["vms", "pools"]
