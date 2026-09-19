from __future__ import annotations

import os
import re
import socket
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
import ipaddress
from .netutil import lan_host_candidates

# ----------------------------
# Paths
# ----------------------------
def sisyphus_user_dir() -> Path:
    # Let's put this in ~/.sisyphus/scanner_certs/
    return Path.home() / ".sisyphus"

def scanner_certs_dir() -> Path:
    d = sisyphus_user_dir() / "scanner_certs"
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
    d = scanner_certs_dir()
    return CertPaths(
        cert_pem=d / "scanner-cert.pem",
        key_pem=d / "scanner-key.pem",
    )

# ----------------------------
# Host/IP discovery
# ----------------------------
def hostname_local() -> str:
    # stable-ish across reboots; user may rename machine, but rare
    hn = socket.gethostname().strip().split(".")[0]
    hn = re.sub(r"[^A-Za-z0-9\-]", "-", hn)  # sanitize
    return f"{hn}.local" if hn else "localhost"

def lan_ip_best_effort() -> str:
    """
    Similar to your _best_lan_ip() trick.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def lan_ipv4_candidates() -> list[str]:
    """
    Collect a small set of candidate IPv4s for SANs.
    Keep it conservative to avoid weird interfaces.
    """
    ips = {lan_ip_best_effort(), "127.0.0.1"}
    # Try hostname resolution as well
    try:
        hn = socket.gethostname()
        for info in socket.getaddrinfo(hn, None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    # remove empties
    return sorted([ip for ip in ips if ip])

# ----------------------------
# Cert validity check
# ----------------------------
def _openssl_not_after(cert_pem: Path) -> datetime | None:
    """
    Parse cert expiry using openssl.
    Returns UTC-ish datetime or None.
    """
    try:
        out = subprocess.check_output(
            ["openssl", "x509", "-in", str(cert_pem), "-noout", "-enddate"],
            text=True,
        ).strip()
        # format: notAfter=Jun  1 12:00:00 2028 GMT
        if "=" in out:
            out = out.split("=", 1)[1].strip()
        return datetime.strptime(out, "%b %d %H:%M:%S %Y %Z")
    except Exception:
        return None

def cert_is_usable(cert_pem: Path, key_pem: Path, min_valid_days: int = 30) -> bool:
    if not cert_pem.exists() or not key_pem.exists():
        return False
    exp = _openssl_not_after(cert_pem)
    if not exp:
        return False
    return exp > (datetime.utcnow() + timedelta(days=min_valid_days))

# ----------------------------
# Cert generation (OpenSSL)
# ----------------------------
def _make_openssl_san_config(*, dns_names: Iterable[str], ip_addrs: Iterable[str]) -> str:
    dns_names = [d for d in dns_names if d]
    ip_addrs = [i for i in ip_addrs if i]

    lines = []
    lines.append("[ req ]")
    lines.append("default_bits = 2048")
    lines.append("prompt = no")
    lines.append("default_md = sha256")
    lines.append("distinguished_name = dn")
    lines.append("x509_extensions = v3_req")
    lines.append("")
    lines.append("[ dn ]")
    lines.append("C = US")
    lines.append("ST = MN")
    lines.append("L = Local")
    lines.append("O = HWDB Dashboard")
    lines.append("OU = Scanner")
    lines.append("CN = HWDB Dashboard Scanner")
    lines.append("")
    lines.append("[ v3_req ]")
    lines.append("keyUsage = critical, digitalSignature, keyEncipherment")
    lines.append("extendedKeyUsage = serverAuth")
    lines.append("subjectAltName = @alt_names")
    lines.append("")
    lines.append("[ alt_names ]")

    n = 1
    for d in dns_names:
        lines.append(f"DNS.{n} = {d}")
        n += 1

    m = 1
    for ip in ip_addrs:
        lines.append(f"IP.{m} = {ip}")
        m += 1

    return "\n".join(lines) + "\n"

def generate_self_signed_cert(
    *,
    cert_pem: Path,
    key_pem: Path,
    dns_names: Iterable[str],
    ip_addrs: Iterable[str],
    days: int = 825,  # ~2.25 years (matches your “a little over 2 years”)
) -> None:
    cert_pem.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(cert_pem.parent, 0o700)
    except Exception:
        pass

    cfg_text = _make_openssl_san_config(dns_names=dns_names, ip_addrs=ip_addrs)

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".cnf") as tf:
        tf.write(cfg_text)
        cfg_path = tf.name

    try:
        # -nodes: no passphrase (needed for unattended startup)
        subprocess.check_call([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-sha256",
            "-days", str(int(days)),
            "-nodes",
            "-keyout", str(key_pem),
            "-out", str(cert_pem),
            "-config", cfg_path,
        ])
        try:
            os.chmod(key_pem, 0o600)
            os.chmod(cert_pem, 0o644)
        except Exception:
            pass
    finally:
        try:
            os.unlink(cfg_path)
        except Exception:
            pass


def _split_san_candidates(hosts: Iterable[str]) -> tuple[list[str], list[str]]:
    """
    Given a list like ["my-mac.local", "my-mac", "192.168.1.23", ...],
    return (dns_names, ip_addrs) for OpenSSL SAN config.
    """
    dns: list[str] = []
    ips: list[str] = []

    seen_dns = set()
    seen_ip = set()

    for h in hosts or []:
        h = (h or "").strip()
        if not h:
            continue

        # IP?
        try:
            ipaddress.ip_address(h)
            if h not in seen_ip:
                seen_ip.add(h)
                ips.append(h)
            continue
        except Exception:
            pass

        # DNS
        if h not in seen_dns:
            seen_dns.add(h)
            dns.append(h)

    # Always include loopback/localhost
    if "localhost" not in seen_dns:
        dns.insert(0, "localhost")
    if "127.0.0.1" not in seen_ip:
        ips.insert(0, "127.0.0.1")

    return dns, ips
        
def ensure_scanner_cert() -> CertPaths:
    """
    Ensure a persistent cert/key exist and are not close to expiry.
    Regenerates if missing or expiring soon.

    SANs include:
      - localhost / 127.0.0.1
      - hostname, hostname.local
      - all private LAN IPv4s (and any other candidates) from netutil.lan_host_candidates()
    """
    paths = default_cert_paths()

    if cert_is_usable(paths.cert_pem, paths.key_pem, min_valid_days=30):
        return paths

    # Single source of truth for what we want to support on phones across OSes
    hosts = lan_host_candidates() or []

    # Back-compat / extra safety: include your previous picks too
    # (won't hurt; de-duped below)
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

    # De-dupe while preserving order
    seen = set()
    uniq_hosts = []
    for h in hosts:
        h = (h or "").strip()
        if h and h not in seen:
            seen.add(h)
            uniq_hosts.append(h)

    dns_names, ip_addrs = _split_san_candidates(uniq_hosts)

    generate_self_signed_cert(
        cert_pem=paths.cert_pem,
        key_pem=paths.key_pem,
        dns_names=dns_names,
        ip_addrs=ip_addrs,
        days=825,
    )
    return paths
