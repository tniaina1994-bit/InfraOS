# SPDX-License-Identifier: GPL-3.0-or-later
"""Modeles SQLAlchemy — Postgres en prod/ISO, SQLite en dev LXC.

Tables: users (auth locale), groups (+role), user_groups (membres),
sessions (JWT jti revocables), audit_events, jobs.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # admin|operator|viewer
    display_name: Mapped[str] = mapped_column(String(128), default="")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_source: Mapped[str] = mapped_column(String(16), default="local")  # local|ldap|ad|kerberos
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(256), default="")
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # role confere aux membres


class UserGroup(Base):
    __tablename__ = "user_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class DnsZone(Base):
    __tablename__ = "dns_zones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # ex. lan.local, 10.in-addr.arpa
    kind: Mapped[str] = mapped_column(String(16), default="master")  # master|forward
    reverse: Mapped[bool] = mapped_column(Boolean, default=False)
    ttl: Mapped[int] = mapped_column(Integer, default=3600)
    forwarders: Mapped[str] = mapped_column(Text, default="[]")  # JSON list (kind=forward)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DnsRecord(Base):
    __tablename__ = "dns_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("dns_zones.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))  # @, www, 10 (= relatif, @ = apex)
    rtype: Mapped[str] = mapped_column(String(16), index=True)  # A|AAAA|CNAME|MX|TXT|PTR|NS
    value: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # MX
    ttl: Mapped[int] = mapped_column(Integer, default=0)  # 0 = TTL zone


class DhcpScope(Base):
    __tablename__ = "dhcp_scopes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    subnet: Mapped[str] = mapped_column(String(32))  # 192.168.20.0/24
    pool_start: Mapped[str] = mapped_column(String(64))  # 192.168.20.100
    pool_end: Mapped[str] = mapped_column(String(64))  # 192.168.20.200
    gateway: Mapped[str] = mapped_column(String(64), default="")  # option routers
    dns: Mapped[str] = mapped_column(Text, default="[]")  # JSON [serveurs]
    domain: Mapped[str] = mapped_column(String(255), default="")
    lease_valid: Mapped[int] = mapped_column(Integer, default=3600)
    lease_max: Mapped[int] = mapped_column(Integer, default=7200)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class DhcpReservation(Base):
    __tablename__ = "dhcp_reservations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_id: Mapped[int] = mapped_column(ForeignKey("dhcp_scopes.id", ondelete="CASCADE"), index=True)
    mac: Mapped[str] = mapped_column(String(32), index=True)  # aa:bb:...
    ip: Mapped[str] = mapped_column(String(64))
    hostname: Mapped[str] = mapped_column(String(255), default="")


class FirewallRule(Base):
    __tablename__ = "firewall_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    chain: Mapped[str] = mapped_column(String(16), default="input")  # input|forward|output|prerouting|postrouting
    action: Mapped[str] = mapped_column(String(16), default="accept")  # accept|drop|dnat|masquerade|log
    proto: Mapped[str] = mapped_column(String(8), default="all")  # all|tcp|udp|icmp
    src: Mapped[str] = mapped_column(String(64), default="")  # CIDR ou vide
    dst: Mapped[str] = mapped_column(String(64), default="")
    dport: Mapped[int] = mapped_column(Integer, default=0)  # 0 = tous
    in_if: Mapped[str] = mapped_column(String(32), default="")
    out_if: Mapped[str] = mapped_column(String(32), default="")
    nat_to: Mapped[str] = mapped_column(String(64), default="")  # dnat: ip[:port]
    log: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class VpnServer(Base):
    __tablename__ = "vpn_servers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # wg0
    address: Mapped[str] = mapped_column(String(64))  # 10.8.0.1/24
    port: Mapped[int] = mapped_column(Integer, default=51820)
    private_key: Mapped[str] = mapped_column(String(128), default="")  # 0600 conceptuel
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class VpnPeer(Base):
    __tablename__ = "vpn_peers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("vpn_servers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    public_key: Mapped[str] = mapped_column(String(128))
    preshared_key: Mapped[str] = mapped_column(String(128), default="")
    allowed_ips: Mapped[str] = mapped_column(String(255), default="")  # 10.8.0.2/32
    endpoint: Mapped[str] = mapped_column(String(128), default="")  # host:port
    keepalive: Mapped[int] = mapped_column(Integer, default=25)


class IpamNetwork(Base):
    __tablename__ = "ipam_networks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    cidr: Mapped[str] = mapped_column(String(32))  # 192.168.20.0/24
    gateway: Mapped[str] = mapped_column(String(64), default="")
    vlan: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(255), default="")


class IpamHost(Base):
    __tablename__ = "ipam_hosts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("ipam_networks.id", ondelete="CASCADE"), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    mac: Mapped[str] = mapped_column(String(32), default="")
    hostname: Mapped[str] = mapped_column(String(255), default="")
    kind: Mapped[str] = mapped_column(String(16), default="static")  # static|reserved|dhcp|gateway


class DiscoveryScan(Base):
    __tablename__ = "discovery_scans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target: Mapped[str] = mapped_column(String(64))
    profile: Mapped[str] = mapped_column(String(16), default="ping")  # ping|fast|os
    status: Mapped[str] = mapped_column(String(16), default="done")
    hosts_up: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DiscoveryHost(Base):
    __tablename__ = "discovery_hosts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("discovery_scans.id", ondelete="CASCADE"), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    mac: Mapped[str] = mapped_column(String(32), default="")
    hostname: Mapped[str] = mapped_column(String(255), default="")
    ports: Mapped[str] = mapped_column(Text, default="[]")  # JSON [{port,proto,service}]
    os: Mapped[str] = mapped_column(String(255), default="")


class MonitoringSample(Base):
    __tablename__ = "monitoring_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host: Mapped[str] = mapped_column(String(128), default="local", index=True)
    cpu: Mapped[int] = mapped_column(Integer, default=0)
    mem: Mapped[int] = mapped_column(Integer, default=0)
    disk: Mapped[int] = mapped_column(Integer, default=0)
    load1: Mapped[str] = mapped_column(String(16), default="")
    net_rx: Mapped[int] = mapped_column(Integer, default=0)
    net_tx: Mapped[int] = mapped_column(Integer, default=0)
    uptime: Mapped[int] = mapped_column(Integer, default=0)
    temp: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class MonitoringAgent(Base):
    __tablename__ = "monitoring_agents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hostname: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    os: Mapped[str] = mapped_column(String(64), default="")  # linux|windows
    token: Mapped[str] = mapped_column(String(128), default="")  # secret agent
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class SambaShare(Base):
    __tablename__ = "samba_shares"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    path: Mapped[str] = mapped_column(String(255))
    comment: Mapped[str] = mapped_column(String(255), default="")
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    browsable: Mapped[bool] = mapped_column(Boolean, default=True)
    guest_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_users: Mapped[str] = mapped_column(String(255), default="")
    valid_groups: Mapped[str] = mapped_column(String(255), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class BackupJob(Base):
    __tablename__ = "backup_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    backend: Mapped[str] = mapped_column(String(16), default="restic")  # restic|borg|rsync
    repo: Mapped[str] = mapped_column(String(255))
    sources: Mapped[str] = mapped_column(Text, default="[]")  # JSON chemins absolus
    schedule: Mapped[str] = mapped_column(String(64), default="")  # cron, vide = manuel
    retention: Mapped[str] = mapped_column(String(255), default="--keep-daily 7 --keep-weekly 4")
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class BackupRun(Base):
    __tablename__ = "backup_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("backup_jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    log: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class UpdateRun(Base):
    __tablename__ = "update_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), default="packages")  # packages|security|upgrade
    packages: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(16), default="running")
    log: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(255), default="")


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), index=True)
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_perm"),)


class UserRole(Base):
    __tablename__ = "user_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class IdentityDomain(Base):
    """Domaine Samba AD DC gere par le module Identity (jamais de secrets en clair)."""
    __tablename__ = "identity_domains"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    realm: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    netbios: Mapped[str] = mapped_column(String(15), default="")
    dc_hostname: Mapped[str] = mapped_column(String(64), default="")
    dc_fqdn: Mapped[str] = mapped_column(String(255), default="")
    dc_ip: Mapped[str] = mapped_column(String(45), default="")
    dns_backend: Mapped[str] = mapped_column(String(32), default="SAMBA_INTERNAL")
    status: Mapped[str] = mapped_column(String(16), default="provisioning")  # provisioning|active|error
    admin_user: Mapped[str] = mapped_column(String(64), default="Administrator")
    hosts_written: Mapped[bool] = mapped_column(Boolean, default=False)
    krb5_written: Mapped[bool] = mapped_column(Boolean, default=False)
    named_stopped: Mapped[bool] = mapped_column(Boolean, default=False)
    provisioned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), default="")


class Module(Base):
    __tablename__ = "modules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(32), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ModuleDependency(Base):
    __tablename__ = "module_dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), index=True)
    depends_on: Mapped[str] = mapped_column(String(64))


class SystemSetting(Base):
    __tablename__ = "system_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                 onupdate=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    action: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text, default="")
    resource: Mapped[str] = mapped_column(String(255), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    result: Mapped[str] = mapped_column(String(16), default="SUCCESS")  # SUCCESS|FAILURE|DENIED


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)  # ex. backup.run, updates.check
    payload: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|done|error
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
