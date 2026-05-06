from __future__ import annotations

import os, socket
from dataclasses import dataclass
from pathlib import Path
from .scanner_certs import (
    cert_is_usable,
    generate_self_signed_cert,
    _split_san_candidates,
    hostname_local,
    lan_ipv4_candidates,
)
from .netutil import lan_host_candidates

def sisyphus_user_dir() -> Path:
    return Path.home() / ".sisyphus"

def dashboard_certs_dir() -> Path:
    d = sisyphus_user_dir() / "dashboard_certs"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except Exception:
        pass
    return d

@dataclass(frozen=True)
class CertPaths:
    cert_pem: Path
    key_pem: Path

def default_cert_paths() -> CertPaths:
    d = dashboard_certs_dir()
    return CertPaths(
        cert_pem=d / "dashboard-cert.pem",
        key_pem=d / "dashboard-key.pem",
    )

def ensure_dashboard_cert() -> CertPaths:
    paths = default_cert_paths()

    if cert_is_usable(paths.cert_pem, paths.key_pem, min_valid_days=30):
        return paths

    hosts = lan_host_candidates() or []
    try:
        hosts.append(hostname_local())
    except Exception:
        pass
    try:
        hosts.append(socket.gethostname().strip())
    except Exception:
        pass
    try:
        hosts.extend(lan_ipv4_candidates())
    except Exception:
        pass

    # de-dupe preserve order
    seen = set()
    uniq = []
    for h in hosts:
        h = (h or "").strip()
        if h and h not in seen:
            seen.add(h)
            uniq.append(h)

    dns_names, ip_addrs = _split_san_candidates(uniq)

    generate_self_signed_cert(
        cert_pem=paths.cert_pem,
        key_pem=paths.key_pem,
        dns_names=dns_names,
        ip_addrs=ip_addrs,
        days=825,
        #quiet=True,
    )
    return paths
