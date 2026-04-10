# ------------------------------------------------------------------------------
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ------------------------------------------------------------------------------

"""Framework-native attack-surface reconnaissance wordlists for read-only research."""

from __future__ import annotations

from pathlib import Path
from typing import Final


_DEFAULT_PRIORITY_SUBDOMAIN_LABELS: Final[tuple[str, ...]] = (
    "www",
    "mail",
    "webmail",
    "api",
    "dev",
    "test",
    "staging",
    "beta",
    "admin",
    "portal",
    "dashboard",
    "internal",
    "corp",
    "vpn",
    "secure",
    "auth",
    "login",
    "app",
    "apps",
    "cdn",
    "static",
    "assets",
    "media",
    "img",
    "images",
    "files",
    "download",
    "uploads",
    "docs",
    "status",
    "support",
    "help",
    "blog",
    "shop",
    "store",
    "payments",
    "billing",
    "m",
    "mobile",
    "old",
    "new",
    "backup",
    "git",
    "jenkins",
    "ci",
    "monitor",
    "monitoring",
    "grafana",
    "kibana",
    "prometheus",
    "sql",
    "db",
    "mysql",
    "redis",
    "search",
    "smtp",
    "imap",
    "pop",
    "ns1",
    "ns2",
    "mx",
    "sso",
    "id",
    "identity",
    "hr",
    "finance",
    "partners",
    "customer",
    "customers",
    "demo",
    "sandbox",
    "preprod",
    "prod",
    "uat",
    "stage",
    "stg",
    "gateway",
    "proxy",
    "lb",
    "vpn-gateway",
    "remote",
    "intranet",
    "extranet",
    "public",
    "private",
    "cloud",
    "storage",
    "s3",
    "cdn2",
    "downloads",
    "wiki",
    "confluence",
    "jira",
    "gitlab",
    "github",
    "nexus",
    "registry",
    "docker",
    "k8s",
    "kubernetes",
    "cluster",
    "node",
    "edge",
    "origin",
    "cache",
    "cms",
    "wordpress",
    "drupal",
    "joomla",
    "phpmyadmin",
    "phpinfo",
    "swagger",
    "api-docs",
    "actuator",
    "health",
    "metrics",
)

_DEFAULT_COMMON_WEB_PATHS: Final[tuple[str, ...]] = (
    "/",
    "robots.txt",
    "sitemap.xml",
    "security.txt",
    ".well-known/security.txt",
    ".git/HEAD",
    ".env",
    ".env.example",
    ".svn/entries",
    ".hg/branch",
    "admin",
    "admin/",
    "admin/login",
    "administrator",
    "dashboard",
    "dashboard/",
    "login",
    "signin",
    "auth",
    "oauth",
    "logout",
    "register",
    "signup",
    "user",
    "users",
    "profile",
    "account",
    "accounts",
    "settings",
    "config",
    "config.php",
    "config.json",
    "backup",
    "backup.zip",
    "backup.tar.gz",
    "backup.sql",
    "db.sql",
    "dump.sql",
    "swagger",
    "swagger-ui",
    "swagger-ui.html",
    "api-docs",
    "openapi.json",
    "graphql",
    "graphiql",
    "actuator",
    "actuator/health",
    "health",
    "metrics",
    "status",
    "server-status",
    "phpinfo.php",
    "info.php",
    "debug",
    "debug/",
    "test",
    "dev",
    "staging",
    "uploads",
    "files",
    "downloads",
    "archive",
    "old",
    "old.zip",
    "logs",
    "log",
    "error.log",
    "access.log",
    "console",
    "shell",
    "jenkins",
    "gitlab",
    "nexus",
    "registry",
    "kibana",
    "grafana",
    "prometheus",
    "elasticsearch",
)

_DEFAULT_TOP_PORTS: Final[tuple[int, ...]] = (
    7, 9, 13, 21, 22, 23, 25, 37, 53, 79, 80, 81, 88, 110, 111, 113, 119, 123,
    135, 137, 138, 139, 143, 161, 179, 199, 389, 427, 443, 445, 465, 512, 513,
    514, 515, 543, 544, 548, 554, 587, 631, 646, 873, 990, 993, 995, 1025, 1026,
    1027, 1080, 1194, 1433, 1521, 1723, 1900, 2049, 2082, 2083, 2086, 2087,
    2181, 2375, 2376, 2483, 2484, 3000, 3128, 3306, 3389, 3690, 4369, 4443,
    4500, 5000, 5001, 5060, 5432, 5601, 5672, 5900, 5984, 5985, 5986, 6000,
    6379, 6443, 7001, 7070, 7443, 7777, 8000, 8008, 8080, 8081, 8088, 8090,
    8181, 8443, 8888, 9000, 9042, 9090, 9200, 9300, 9418, 9443, 9999, 10000,
    11211, 15672, 27017,
)


def _wordlist_root() -> Path:
    return Path(__file__).resolve().parents[2] / "wordlists" / "attack_surface"


def _read_wordlist_text(filename: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    path = _wordlist_root() / filename
    if not path.exists():
        return fallback
    values: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        values.append(line)
    return tuple(values) or fallback


def _read_wordlist_ports(filename: str, fallback: tuple[int, ...]) -> tuple[int, ...]:
    path = _wordlist_root() / filename
    if not path.exists():
        return fallback
    values: list[int] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            values.append(int(line))
        except ValueError:
            continue
    return tuple(values) or fallback


SURFACE_PRIORITY_SUBDOMAIN_LABELS: Final[tuple[str, ...]] = _read_wordlist_text(
    "subdomains_small.txt",
    _DEFAULT_PRIORITY_SUBDOMAIN_LABELS,
)
SURFACE_COMMON_WEB_PATHS: Final[tuple[str, ...]] = _read_wordlist_text(
    "paths_common.txt",
    _DEFAULT_COMMON_WEB_PATHS,
)
SURFACE_TOP_PORTS: Final[tuple[int, ...]] = _read_wordlist_ports(
    "ports_top100.txt",
    _DEFAULT_TOP_PORTS,
)

_PRIORITY_LABEL_INDEX: Final[dict[str, int]] = {
    value.casefold(): index for index, value in enumerate(SURFACE_PRIORITY_SUBDOMAIN_LABELS)
}


def prioritize_surface_subdomains(subdomains: list[str]) -> list[str]:
    """Rank discovered subdomains by curated surface-recon label relevance."""

    normalized = sorted({str(item).strip().lower() for item in subdomains if str(item).strip()})

    def _sort_key(hostname: str) -> tuple[int, int, str]:
        label = hostname.split(".", 1)[0].casefold()
        if label in _PRIORITY_LABEL_INDEX:
            return (0, _PRIORITY_LABEL_INDEX[label], hostname)
        return (1, 10_000, hostname)

    return sorted(normalized, key=_sort_key)


def matched_surface_subdomain_labels(subdomains: list[str]) -> list[str]:
    """Return the curated priority labels that matched discovered subdomains."""

    matched: list[str] = []
    for hostname in prioritize_surface_subdomains(subdomains):
        label = hostname.split(".", 1)[0].casefold()
        if label in _PRIORITY_LABEL_INDEX and label not in matched:
            matched.append(label)
    return matched


def build_surface_wordlist_guidance(
    subdomains: list[str],
    *,
    max_prioritized_hosts: int = 16,
    max_paths: int = 24,
    max_ports: int = 32,
) -> dict[str, object]:
    """Build non-bruteforce surface guidance from framework-owned recon wordlists."""

    prioritized_hosts = prioritize_surface_subdomains(subdomains)
    return {
        "matched_priority_labels": matched_surface_subdomain_labels(subdomains),
        "prioritized_subdomains": prioritized_hosts[:max(1, int(max_prioritized_hosts))],
        "common_paths": list(SURFACE_COMMON_WEB_PATHS[: max(1, int(max_paths))]),
        "top_ports": list(SURFACE_TOP_PORTS[: max(1, int(max_ports))]),
    }
