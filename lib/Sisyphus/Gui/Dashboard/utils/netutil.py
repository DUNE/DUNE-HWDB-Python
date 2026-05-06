# Sisyphus/Gui/Dashboard/utils/netutil.py
from __future__ import annotations

import os, re, socket, subprocess, sys
from typing import List
import ipaddress


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def _is_private_ipv4(ip: str, *, allow_link_local: bool = False) -> bool:
    """
    True for RFC1918 private IPv4s (and optionally link-local 169.254/16).
    Uses ipaddress for correctness.
    """
    try:
        addr = ipaddress.ip_address(ip)
        if addr.version != 4:
            return False
        if addr.is_private:
            return True
        if allow_link_local and addr.is_link_local:
            return True
        return False
    except Exception:
        return False


def _is_wsl() -> bool:
    # Works for WSL1/WSL2
    if os.environ.get("WSL_INTEROP") or os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
            t = f.read().lower()
        return ("microsoft" in t) or ("wsl" in t)
    except Exception:
        return False


def _is_probably_wsl_virtual_ipv4(ip: str) -> bool:
    """
    Heuristic:
      - In WSL2, Linux-side interface IPs are often 172.16/12 (e.g. 172.22.0.x),
        which phones cannot reach directly.
      - We treat 172.16/12 as "least preferred" under WSL, not outright forbidden.
    """
    try:
        a = ipaddress.ip_address(ip)
        if a.version != 4:
            return False
        # 172.16.0.0/12
        return a in ipaddress.ip_network("172.16.0.0/12")
    except Exception:
        return False


def _score_ipv4_for_phone(ip: str, *, wsl_mode: bool) -> int:
    """
    Lower score = better candidate for phone access.
    Preference:
      - 192.168/16 and 10/8 are most common LANs
      - 172.16/12 is common for VPNs and (under WSL2) often virtual/NAT -> last
    """
    try:
        a = ipaddress.ip_address(ip)
        if a.version != 4:
            return 1000
        if a.is_loopback:
            return 900
        if a.is_link_local:
            return 800

        if a in ipaddress.ip_network("192.168.0.0/16"):
            return 0
        if a in ipaddress.ip_network("10.0.0.0/8"):
            return 1

        if a in ipaddress.ip_network("172.16.0.0/12"):
            # under WSL, this is *very often* the vNIC range -> push to end
            return 50 if wsl_mode else 2

        # other private ranges (rare) — still okay
        if a.is_private:
            return 10

        return 500
    except Exception:
        return 1000


def _dedupe(seq: List[str]) -> List[str]:
    out, seen = [], set()
    for x in seq:
        x = (x or "").strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _candidates_from_getaddrinfo() -> List[str]:
    ips = []
    try:
        hn = socket.gethostname()
        for info in socket.getaddrinfo(hn, None, socket.AF_INET):
            ip = info[4][0]
            if _is_private_ipv4(ip):
                ips.append(ip)
    except Exception:
        pass
    return ips


def _candidates_windows() -> List[str]:
    # parse `ipconfig`
    out = _run(["ipconfig"])
    ips = re.findall(r"IPv4 Address[^\:]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", out)
    return [ip for ip in ips if _is_private_ipv4(ip)]


def _candidates_linux() -> List[str]:
    # parse `ip -4 addr`
    out = _run(["ip", "-4", "addr"])
    ips = re.findall(r"inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/", out)
    return [ip for ip in ips if _is_private_ipv4(ip)]


def _candidates_macos() -> List[str]:
    ips = []
    ip_en0 = _run(["ipconfig", "getifaddr", "en0"]).strip()
    if _is_private_ipv4(ip_en0):
        ips.append(ip_en0)

    out = _run(["ifconfig"])
    ips2 = re.findall(r"inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s", out)
    ips.extend([ip for ip in ips2 if _is_private_ipv4(ip)])
    return ips


def _candidates_windows_from_wsl() -> List[str]:
    """
    When running under WSL2, the phone usually cannot reach the WSL VM IP.
    We therefore try to ask the Windows host for its LAN IPv4 addresses.
    """
    ips: List[str] = []

    # 1) Try PowerShell (best)
    ps = _run([
        "powershell.exe", "-NoProfile", "-Command",
        r"Get-NetIPAddress -AddressFamily IPv4 "
        r"| Where-Object { "
        r"  $_.IPAddress -match '^\d+\.' "
        r"  -and $_.IPAddress -notlike '127.*' "
        r"  -and $_.IPAddress -notlike '169.254.*' "
        r"  -and $_.InterfaceAlias -notmatch 'WSL' "
        r"  -and $_.InterfaceAlias -notmatch 'vEthernet' "
        r"} "
        r"| Select-Object -ExpandProperty IPAddress"
    ])
    for line in (ps or "").splitlines():
        ip = line.strip()
        if _is_private_ipv4(ip):
            ips.append(ip)

    # 2) Fallback: cmd.exe ipconfig
    if not ips:
        out = _run(["cmd.exe", "/c", "ipconfig"])
        ips2 = re.findall(r"IPv4 Address[^\:]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", out)
        ips.extend([ip for ip in ips2 if _is_private_ipv4(ip)])

    return _dedupe(ips)


def lan_host_candidates() -> List[str]:
    """
    Returns a *small* list of host candidates (hostnames + LAN IPs),
    ordered from most-likely-to-work to least.

    Key behavior:
      - Prefer IPv4 LAN IPs FIRST (phones resolve these reliably)
      - Under WSL2, prefer Windows host LAN IPs and push WSL virtual 172.16/12 toward the end
      - Put *.local LAST (mDNS often fails on Windows corp networks)
    """
    hn = socket.gethostname().split(".")[0].strip()
    wsl = _is_wsl()

    ips: List[str] = []

    if wsl:
        # IMPORTANT: Windows LAN IPs first
        ips.extend(_candidates_windows_from_wsl())

        # Include Linux-side IPs as fallbacks, but we'll sort them later
        ips.extend(_candidates_linux())
    else:
        if sys.platform.startswith("darwin"):
            ips.extend(_candidates_macos())
        elif sys.platform.startswith("win"):
            ips.extend(_candidates_windows())
        else:
            ips.extend(_candidates_linux())

    # Add hostname resolution candidates (late)
    ips.extend(_candidates_from_getaddrinfo())

    # Last resort “default route trick”
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if _is_private_ipv4(ip):
            ips.append(ip)
    except Exception:
        pass

    ips = _dedupe(ips)

    # Sort IPs by "phone friendliness"
    ips = sorted(ips, key=lambda ip: _score_ipv4_for_phone(ip, wsl_mode=wsl))

    # If we are in WSL and we *do* have some good Windows-ish IPs (10/8 or 192.168/16),
    # optionally drop the WSL-virtual 172.16/12 IPs entirely to avoid QR picking them.
    if wsl:
        have_good = any(
            ipaddress.ip_address(ip) in ipaddress.ip_network("192.168.0.0/16")
            or ipaddress.ip_address(ip) in ipaddress.ip_network("10.0.0.0/8")
            for ip in ips
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip)
        )
        if have_good:
            ips = [ip for ip in ips if not _is_probably_wsl_virtual_ipv4(ip)]

    # Hostnames: plain hostname earlier than .local
    hosts: List[str] = []
    if hn:
        hosts.append(hn)
    if hn:
        hosts.append(f"{hn}.local")  # Put .local last

    return _dedupe(ips + hosts)
