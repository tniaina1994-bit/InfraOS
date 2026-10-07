# packaging/ — paquets Debian InfraOS (ISO + prod)

- `debian/` : sources `infraos-backend`, `infraos-frontend` (dh-python,
  nginx en dépendance, unit systemd + conf nginx dans `installer/`).
- Build : `dpkg-buildpackage -b` sur builder Debian 13.
- L'ISO (`iso/`) installe ces `.deb` — jamais de conversion LXC→ISO.
