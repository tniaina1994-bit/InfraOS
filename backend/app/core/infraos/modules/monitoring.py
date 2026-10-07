# SPDX-License-Identifier: GPL-3.0-or-later
"""Monitoring — node-exporter (phase ulterieure : alertes, tableaux)."""
from ..module_base import SimpleServiceModule


class MonitoringModule(SimpleServiceModule):
    name = "monitoring"
    SERVICE = "prometheus-node-exporter"
    PACKAGE = "prometheus-node-exporter"
    PLANNED = ["alerts", "targets"]
