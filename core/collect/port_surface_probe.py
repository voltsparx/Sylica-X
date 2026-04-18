# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Silica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Silica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root
# ──────────────────────────────────────────────────────────────

"""Port surface probe helpers for active attack-surface discovery."""

from __future__ import annotations

import asyncio
from functools import partial
import shutil
import subprocess
from typing import Any
import xml.etree.ElementTree as ET


SURFACE_SCAN_PROFILES: dict[str, list[str]] = {
    "stealth_sweep": ["-sS"],
    "connect_sweep": ["-sT"],
    "udp_sweep": ["-sU"],
    "ack_probe": ["-sA"],
    "window_probe": ["-sW"],
    "maimon_probe": ["-sM"],
    "null_probe": ["-sN"],
    "fin_probe": ["-sF"],
    "xmas_probe": ["-sX"],
    "sctp_init_probe": ["-sY"],
    "sctp_cookie_probe": ["-sZ"],
    "ip_protocol_sweep": ["-sO"],
    "host_discovery_only": ["-sn"],
    "skip_host_discovery": ["-Pn"],
    "service_version_probe": ["-sV"],
    "os_fingerprint": ["-O"],
    "full_aggressive_probe": ["-A"],
    "default_script_run": ["-sC"],
    "vuln_script_run": ["--script=vuln"],
    "auth_script_run": ["--script=auth"],
    "discovery_script_run": ["--script=discovery"],
    "exploit_script_run": ["--script=exploit"],
    "brute_script_run": ["--script=brute"],
    "safe_script_run": ["--script=safe"],
    "intrusive_script_run": ["--script=intrusive"],
    "malware_script_run": ["--script=malware"],
    "dos_script_run": ["--script=dos"],
    "external_script_run": ["--script=external"],
    "fuzzer_script_run": ["--script=fuzzer"],
    "banner_capture": ["--script=banner"],
    "http_surface_scripts": ["--script=http-*"],
    "ssl_surface_scripts": ["--script=ssl-*"],
    "dns_surface_scripts": ["--script=dns-*"],
    "ftp_surface_scripts": ["--script=ftp-*"],
    "smb_surface_scripts": ["--script=smb-*"],
    "smtp_surface_scripts": ["--script=smtp-*"],
    "snmp_surface_scripts": ["--script=snmp-*"],
    "timing_paranoid": ["-T0"],
    "timing_sneaky": ["-T1"],
    "timing_polite": ["-T2"],
    "timing_normal": ["-T3"],
    "timing_aggressive": ["-T4"],
    "timing_insane": ["-T5"],
    "top_100_ports": ["--top-ports", "100"],
    "top_1000_ports": ["--top-ports", "1000"],
    "all_65535_ports": ["-p-"],
    "common_service_ports": ["-p", "21,22,23,25,53,80,110,143,443,445,3306,3389,8080,8443"],
    "version_intensity_low": ["-sV", "--version-intensity", "0"],
    "version_intensity_high": ["-sV", "--version-intensity", "9"],
    "version_all_probes": ["-sV", "--version-all"],
    "traceroute_map": ["--traceroute"],
    "ipv6_mode": ["-6"],
    "show_port_reason": ["--reason"],
    "open_ports_only": ["--open"],
    "packet_trace_mode": ["--packet-trace"],
    "xml_stream_output": ["-oX", "-"],
    "grepable_stream_output": ["-oG", "-"],
    "os_scan_limit": ["--osscan-limit"],
    "os_scan_guess": ["--osscan-guess"],
    "defeat_rst_ratelimit": ["--defeat-rst-ratelimit"],
    "bad_checksum_probe": ["--badsum"],
    "random_mac_spoof": ["--spoof-mac", "0"],
    "data_length_pad": ["--data-length", "25"],
    "fragment_packets": ["-f"],
    "random_decoy_run": ["-D", "RND:5"],
    "source_port_80": ["--source-port", "80"],
    "min_send_rate_500": ["--min-rate", "500"],
    "max_send_rate_1000": ["--max-rate", "1000"],
    "min_parallelism_10": ["--min-parallelism", "10"],
    "max_parallelism_100": ["--max-parallelism", "100"],
    "max_retries_1": ["--max-retries", "1"],
    "host_timeout_30s": ["--host-timeout", "30s"],
    "scan_delay_100ms": ["--scan-delay", "100ms"],
    "fast_scan_mode": ["-F"],
    "resolve_all_ips": ["--resolve-all"],
    "no_dns_resolution": ["-n"],
    "use_public_dns": ["--dns-servers", "8.8.8.8,1.1.1.1"],
    "max_hostgroup_5": ["--max-hostgroup", "5"],
    "script_args_safe_mode": ["--script-args", "safe=1"],
    "script_trace_mode": ["--script-trace"],
    "update_script_db": ["--script-updatedb"],
}

SURFACE_SCAN_PRESETS: dict[str, list[str]] = {
    "quick_surface": [
        "stealth_sweep",
        "top_100_ports",
        "timing_normal",
        "open_ports_only",
        "xml_stream_output",
    ],
    "deep_surface": [
        "stealth_sweep",
        "all_65535_ports",
        "service_version_probe",
        "timing_aggressive",
        "open_ports_only",
        "xml_stream_output",
    ],
    "service_fingerprint": [
        "stealth_sweep",
        "service_version_probe",
        "version_intensity_high",
        "default_script_run",
        "timing_normal",
        "xml_stream_output",
    ],
    "os_fingerprint": [
        "stealth_sweep",
        "os_fingerprint",
        "os_scan_guess",
        "timing_normal",
        "xml_stream_output",
    ],
    "full_aggressive": [
        "full_aggressive_probe",
        "all_65535_ports",
        "timing_aggressive",
        "xml_stream_output",
    ],
    "vuln_surface": [
        "stealth_sweep",
        "vuln_script_run",
        "service_version_probe",
        "common_service_ports",
        "timing_normal",
        "xml_stream_output",
    ],
    "stealth_recon": [
        "stealth_sweep",
        "timing_sneaky",
        "open_ports_only",
        "skip_host_discovery",
        "fragment_packets",
        "xml_stream_output",
    ],
    "udp_surface": [
        "udp_sweep",
        "top_100_ports",
        "timing_normal",
        "service_version_probe",
        "xml_stream_output",
    ],
    "http_ssl_surface": [
        "stealth_sweep",
        "http_surface_scripts",
        "ssl_surface_scripts",
        "service_version_probe",
        "common_service_ports",
        "timing_normal",
        "xml_stream_output",
    ],
    "passive_safe": [
        "connect_sweep",
        "host_discovery_only",
        "timing_polite",
        "safe_script_run",
        "xml_stream_output",
    ],
    "banner_sweep": [
        "stealth_sweep",
        "banner_capture",
        "service_version_probe",
        "top_1000_ports",
        "timing_normal",
        "xml_stream_output",
    ],
    "smb_audit": [
        "stealth_sweep",
        "smb_surface_scripts",
        "service_version_probe",
        "timing_normal",
        "xml_stream_output",
    ],
    "dns_audit": [
        "stealth_sweep",
        "dns_surface_scripts",
        "service_version_probe",
        "timing_normal",
        "xml_stream_output",
    ],
    "discovery_sweep": [
        "host_discovery_only",
        "discovery_script_run",
        "timing_normal",
        "xml_stream_output",
    ],
}


def locate_surface_scanner() -> str | None:
    """Locate an installed surface-scanner binary."""

    return shutil.which("nmap") or shutil.which("nmap3")


def surface_scanner_status() -> dict[str, Any]:
    """Return surface scanner capability details."""

    path = locate_surface_scanner()
    if path is None:
        return {
            "available": False,
            "path": None,
            "version": "",
            "scan_profiles": [],
            "scan_presets": [],
        }

    result = subprocess.run(
        [path, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    version_line = ""
    for line in result.stdout.splitlines():
        if line.strip():
            version_line = line.strip()
            break
    return {
        "available": True,
        "path": path,
        "version": version_line,
        "scan_profiles": list(SURFACE_SCAN_PROFILES.keys()),
        "scan_presets": list(SURFACE_SCAN_PRESETS.keys()),
    }


async def surface_scanner_status_async() -> dict[str, Any]:
    """Async wrapper for surface scanner status."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, surface_scanner_status)


def _text_attr(element: ET.Element | None, name: str) -> str:
    if element is None:
        return ""
    return str(element.attrib.get(name, "") or "")


def parse_surface_scan_xml(xml_text: str) -> dict[str, Any]:
    """Parse XML output from a surface scan into structured intelligence."""

    try:
        root = ET.fromstring(xml_text)
        scaninfo = root.find("scaninfo")
        parsed: dict[str, Any] = {
            "scan_info": {
                "type": _text_attr(scaninfo, "type"),
                "protocol": _text_attr(scaninfo, "protocol"),
                "numservices": _text_attr(scaninfo, "numservices"),
                "services": _text_attr(scaninfo, "services"),
            },
            "hosts": [],
            "stats": {
                "elapsed": "",
                "exit": "",
                "summary": "",
            },
            "errors": [],
        }

        for host in root.findall("host"):
            address = ""
            mac_address = ""
            for address_row in host.findall("address"):
                addr = str(address_row.attrib.get("addr", "") or "")
                addr_type = str(address_row.attrib.get("addrtype", "") or "").lower()
                if addr_type == "mac":
                    mac_address = addr
                elif not address:
                    address = addr

            hostnames = [
                str(row.attrib.get("name", "") or "")
                for row in host.findall("./hostnames/hostname")
                if str(row.attrib.get("name", "") or "").strip()
            ]
            status = _text_attr(host.find("status"), "state")
            uptime = host.find("uptime")

            ports: list[dict[str, Any]] = []
            for port in host.findall("./ports/port"):
                service = port.find("service")
                scripts = [
                    {
                        "id": str(script.attrib.get("id", "") or ""),
                        "output": str(script.attrib.get("output", "") or ""),
                    }
                    for script in port.findall("script")
                ]
                ports.append(
                    {
                        "port": int(port.attrib.get("portid", 0) or 0),
                        "protocol": str(port.attrib.get("protocol", "") or ""),
                        "state": _text_attr(port.find("state"), "state"),
                        "reason": _text_attr(port.find("state"), "reason"),
                        "service_name": _text_attr(service, "name"),
                        "product": _text_attr(service, "product"),
                        "version": _text_attr(service, "version"),
                        "extra_info": _text_attr(service, "extrainfo"),
                        "tunnel": _text_attr(service, "tunnel"),
                        "cpe": [str(cpe.text or "") for cpe in port.findall("./service/cpe") if str(cpe.text or "").strip()],
                        "scripts": scripts,
                    }
                )

            os_matches = [
                {
                    "name": str(row.attrib.get("name", "") or ""),
                    "accuracy": str(row.attrib.get("accuracy", "") or ""),
                }
                for row in host.findall("./os/osmatch")
            ]
            host_scripts = [
                {
                    "id": str(script.attrib.get("id", "") or ""),
                    "output": str(script.attrib.get("output", "") or ""),
                }
                for script in host.findall("./hostscript/script")
            ]
            traceroute = [
                {
                    "ttl": str(hop.attrib.get("ttl", "") or ""),
                    "ip": str(hop.attrib.get("ipaddr", "") or ""),
                    "host": str(hop.attrib.get("host", "") or ""),
                }
                for hop in host.findall("./trace/hop")
            ]

            parsed["hosts"].append(
                {
                    "address": address,
                    "mac_address": mac_address,
                    "hostnames": hostnames,
                    "status": status,
                    "ports": ports,
                    "os_matches": os_matches,
                    "scripts": host_scripts,
                    "traceroute": traceroute,
                    "uptime": {
                        "seconds": _text_attr(uptime, "seconds"),
                        "lastboot": _text_attr(uptime, "lastboot"),
                    },
                }
            )

        finished = root.find("./runstats/finished")
        parsed["stats"] = {
            "elapsed": _text_attr(finished, "elapsed"),
            "exit": _text_attr(finished, "exit"),
            "summary": _text_attr(finished, "summary"),
        }

        errors: list[str] = []
        for element in root.findall(".//*"):
            for attr_name in ("error", "errormsg"):
                token = str(element.attrib.get(attr_name, "") or "").strip()
                if token and token not in errors:
                    errors.append(token)
        parsed["errors"] = errors
        return parsed
    except Exception:
        return {}


def _append_profile_flags(command: list[str], flags: list[str]) -> None:
    index = 0
    while index < len(flags):
        token = flags[index]
        if token == "-oX" and index + 1 < len(flags) and flags[index + 1] == "-":
            index += 2
            continue
        command.append(token)
        index += 1


def _unique_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def run_surface_scan(
    target: str,
    profiles: list[str],
    extra_flags: list[str] | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run a surface scan against one target."""

    binary_path = locate_surface_scanner()
    if binary_path is None:
        return {"error": "surface scanner binary not found", "target": target}

    command = [binary_path, "-oX", "-"]
    for profile_name in profiles:
        flags = SURFACE_SCAN_PROFILES.get(profile_name)
        if flags:
            _append_profile_flags(command, flags)
    if extra_flags is not None:
        command.extend(list(extra_flags))
    command.append(target)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"error": "surface scan timed out", "target": target}

    parsed = parse_surface_scan_xml(result.stdout)
    open_ports: list[int] = []
    services: list[dict[str, Any]] = []
    os_guesses: list[str] = []

    for host in parsed.get("hosts", []) if isinstance(parsed, dict) else []:
        if not isinstance(host, dict):
            continue
        for port in host.get("ports", []) or []:
            if not isinstance(port, dict):
                continue
            if str(port.get("state", "")).lower() != "open":
                continue
            port_number = int(port.get("port", 0) or 0)
            open_ports.append(port_number)
            services.append(
                {
                    "port": port_number,
                    "service_name": str(port.get("service_name", "") or ""),
                    "product": str(port.get("product", "") or ""),
                    "version": str(port.get("version", "") or ""),
                }
            )
        for os_match in host.get("os_matches", []) or []:
            if not isinstance(os_match, dict):
                continue
            name = str(os_match.get("name", "") or "").strip()
            if name:
                os_guesses.append(name)

    return {
        "target": target,
        "profiles": list(profiles),
        "preset": None,
        "return_code": int(result.returncode),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command": command,
        "parsed": parsed,
        "open_ports": sorted(set(open_ports)),
        "services": services,
        "os_guesses": _unique_strings(os_guesses),
        "error": None,
    }


async def run_surface_scan_async(
    target: str,
    profiles: list[str],
    extra_flags: list[str] | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Async wrapper for run_surface_scan."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(
            run_surface_scan,
            target,
            profiles,
            extra_flags=extra_flags,
            timeout_seconds=timeout_seconds,
        ),
    )


def run_surface_scan_preset(
    target: str,
    preset_name: str,
    extra_flags: list[str] | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run one named surface-scan preset."""

    preset_profiles = SURFACE_SCAN_PRESETS.get(preset_name)
    if preset_profiles is None:
        return {"error": f"unknown preset: {preset_name}", "target": target}
    result = run_surface_scan(
        target,
        preset_profiles,
        extra_flags=extra_flags,
        timeout_seconds=timeout_seconds,
    )
    result["preset"] = preset_name
    return result


async def run_surface_scan_preset_async(
    target: str,
    preset_name: str,
    extra_flags: list[str] | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Async wrapper for run_surface_scan_preset."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(
            run_surface_scan_preset,
            target,
            preset_name,
            extra_flags=extra_flags,
            timeout_seconds=timeout_seconds,
        ),
    )


def list_surface_scan_profiles() -> list[str]:
    """List all available surface scan profiles."""

    return sorted(SURFACE_SCAN_PROFILES.keys())


def list_surface_scan_presets() -> list[str]:
    """List all available surface scan presets."""

    return sorted(SURFACE_SCAN_PRESETS.keys())

