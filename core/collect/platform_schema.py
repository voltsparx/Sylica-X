"""Platform manifest loading and validation for Silica-X."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


ALLOWED_METHODS = {"GET", "HEAD", "POST", "PUT"}
ALLOWED_DETECTION_METHODS = {"status_code", "message", "response_url"}


class PlatformValidationError(ValueError):
    """Raised when a platform manifest entry is invalid."""


@dataclass(frozen=True)
class PlatformConfig:
    name: str
    url: str
    url_probe: str
    detection_methods: tuple[str, ...]
    exists_statuses: tuple[int, ...]
    not_found_statuses: tuple[int, ...]
    error_messages: tuple[str, ...]
    error_url: str | None
    regex_check: str | None
    headers: dict[str, str]
    request_method: str
    request_payload: dict[str, Any] | None
    confidence_weight: float


def load_platforms(platform_dir: str = "platforms") -> list[PlatformConfig]:
    if not os.path.isdir(platform_dir):
        raise PlatformValidationError(
            f"Platform directory not found: {os.path.abspath(platform_dir)}"
        )

    configs: list[PlatformConfig] = []
    for filename in sorted(os.listdir(platform_dir)):
        if not filename.endswith(".json"):
            continue
        if filename.lower() == "schema.json":
            continue

        path = os.path.join(platform_dir, filename)
        with open(path, "r", encoding="utf-8") as handle:
            try:
                payload = json.load(handle)
            except json.JSONDecodeError as exc:
                raise PlatformValidationError(
                    f"Invalid JSON in {path}: {exc.msg}"
                ) from exc

        configs.append(_normalize_platform(payload, source=path))

    if not configs:
        raise PlatformValidationError(
            f"No platform json files found in {os.path.abspath(platform_dir)}"
        )
    return configs


def _normalize_platform(raw: dict[str, Any], source: str) -> PlatformConfig:
    if not isinstance(raw, dict):
        raise PlatformValidationError(f"{source}: top-level json must be an object.")

    name = raw.get("name")
    url = raw.get("url")
    if not isinstance(name, str) or not name.strip():
        raise PlatformValidationError(f"{source}: 'name' must be a non-empty string.")
    if not isinstance(url, str) or "{username}" not in url:
        raise PlatformValidationError(
            f"{source}: 'url' must be a string containing '{{username}}'."
        )

    url_probe = raw.get("url_probe", raw.get("urlProbe", url))
    if not isinstance(url_probe, str) or "{username}" not in url_probe:
        raise PlatformValidationError(
            f"{source}: 'url_probe' must contain '{{username}}' when provided."
        )

    detection_methods = _normalize_detection_methods(raw, source)
    exists_statuses = _normalize_int_list(
        raw.get("exists_statuses", raw.get("exists_status")), f"{source}: exists_status"
    )
    not_found_statuses = _normalize_int_list(
        raw.get("not_found_statuses", raw.get("errorCode")), f"{source}: not_found_statuses"
    )

    error_messages = _normalize_string_list(
        raw.get("error_messages", raw.get("errorMsg")), f"{source}: error_messages"
    )
    if "message" in detection_methods and not error_messages:
        raise PlatformValidationError(
            f"{source}: detection method 'message' requires error_messages/errorMsg."
        )

    error_url = raw.get("error_url", raw.get("errorUrl"))
    if error_url is not None:
        if not isinstance(error_url, str) or "{username}" not in error_url:
            raise PlatformValidationError(
                f"{source}: error_url/errorUrl must contain '{{username}}'."
            )

    regex_check = raw.get("regex_check", raw.get("regexCheck"))
    if regex_check is not None and (not isinstance(regex_check, str) or not regex_check):
        raise PlatformValidationError(f"{source}: regex_check/regexCheck must be a string.")

    headers = raw.get("headers", {})
    if not isinstance(headers, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in headers.items()
    ):
        raise PlatformValidationError(
            f"{source}: headers must be an object of string keys and values."
        )

    request_method = raw.get("request_method")
    if request_method is None:
        request_method = "HEAD" if detection_methods == ("status_code",) else "GET"
    if not isinstance(request_method, str) or request_method.upper() not in ALLOWED_METHODS:
        raise PlatformValidationError(
            f"{source}: request_method must be one of {sorted(ALLOWED_METHODS)}."
        )
    request_method = request_method.upper()

    request_payload = raw.get("request_payload")
    if request_payload is not None and not isinstance(request_payload, dict):
        raise PlatformValidationError(f"{source}: request_payload must be an object.")

    confidence_weight = raw.get("confidence_weight", 0.7)
    try:
        confidence_weight = float(confidence_weight)
    except (TypeError, ValueError) as exc:
        raise PlatformValidationError(
            f"{source}: confidence_weight must be numeric."
        ) from exc

    if not 0.0 <= confidence_weight <= 1.0:
        raise PlatformValidationError(
            f"{source}: confidence_weight must be between 0.0 and 1.0."
        )

    return PlatformConfig(
        name=name.strip(),
        url=url,
        url_probe=url_probe,
        detection_methods=detection_methods,
        exists_statuses=tuple(exists_statuses),
        not_found_statuses=tuple(not_found_statuses),
        error_messages=tuple(error_messages),
        error_url=error_url,
        regex_check=regex_check,
        headers=headers,
        request_method=request_method,
        request_payload=request_payload,
        confidence_weight=confidence_weight,
    )


def _normalize_detection_methods(raw: dict[str, Any], source: str) -> tuple[str, ...]:
    manual_methods = raw.get("detection", raw.get("detection_methods"))
    sherlock_style = raw.get("errorType")
    methods_raw = manual_methods if manual_methods is not None else sherlock_style

    if methods_raw is None:
        return ("status_code",)

    if isinstance(methods_raw, str):
        methods = [methods_raw]
    elif isinstance(methods_raw, list) and all(isinstance(item, str) for item in methods_raw):
        methods = list(methods_raw)
    else:
        raise PlatformValidationError(
            f"{source}: detection/errorType must be a string or list of strings."
        )

    normalized: list[str] = []
    for method in methods:
        mapped = method.strip().lower()
        if mapped not in ALLOWED_DETECTION_METHODS:
            raise PlatformValidationError(
                f"{source}: unsupported detection method '{method}'."
            )
        if mapped not in normalized:
            normalized.append(mapped)

    if not normalized:
        raise PlatformValidationError(f"{source}: at least one detection method is required.")
    return tuple(normalized)


def _normalize_int_list(value: Any, label: str) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, list) and all(isinstance(item, int) for item in value):
        return value
    raise PlatformValidationError(f"{label} must be an integer or list of integers.")


def _normalize_string_list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise PlatformValidationError(f"{label} must be a string or list of strings.")
