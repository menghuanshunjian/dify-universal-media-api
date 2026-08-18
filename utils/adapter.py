from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


TOKEN_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
MAX_REDIRECTS = 5
HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
FORBIDDEN_HEADERS = {
    "connection", "content-length", "host", "proxy-authenticate",
    "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade",
}


def validate_public_https_url(url: str, field_name: str = "URL") -> str:
    """Reject non-HTTPS and hosts resolving to non-public address space."""
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{field_name} must be a valid HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not contain embedded credentials")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"{field_name} host could not be resolved") from exc
    if not addresses:
        raise ValueError(f"{field_name} host could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError(f"{field_name} must resolve only to public IP addresses")
    return value


def _request_with_safe_redirects(
    method: str, url: str, *, preserve_origin: bool = False, **kwargs: Any
) -> requests.Response:
    current_url = validate_public_https_url(url)
    initial = urlparse(current_url)
    initial_origin = (initial.hostname, initial.port or 443)
    current_method = method.upper()
    for _ in range(MAX_REDIRECTS + 1):
        response = requests.request(method=current_method, url=current_url, allow_redirects=False, **kwargs)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response
        location = response.headers.get("Location")
        response.close()
        if not location:
            raise RuntimeError("Upstream returned a redirect without a Location header")
        current_url = validate_public_https_url(urljoin(current_url, location), "Redirect URL")
        redirected = urlparse(current_url)
        if preserve_origin and (redirected.hostname, redirected.port or 443) != initial_origin:
            raise RuntimeError("API redirect to a different host was blocked")
        if response.status_code == 303:
            current_method = "GET"
            kwargs["json"] = None
            kwargs["params"] = None
    raise RuntimeError(f"Upstream exceeded the {MAX_REDIRECTS}-redirect limit")


def extract_path(data: Any, path: str) -> Any:
    """Read a dot/bracket path such as $.data[0].url from JSON-compatible data."""
    normalized = path.strip()
    if normalized in {"", "$"}:
        return data
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized.startswith("$"):
        normalized = normalized[1:]

    tokens = re.findall(r"([^.\[\]]+)|\[(\d+)\]", normalized)
    current = data
    for object_key, array_index in tokens:
        if object_key:
            if not isinstance(current, dict) or object_key not in current:
                raise KeyError(f"Response path '{path}' was not found at '{object_key}'")
            current = current[object_key]
        else:
            if not isinstance(current, list):
                raise KeyError(f"Response path '{path}' expected an array")
            index = int(array_index)
            if index >= len(current):
                raise KeyError(f"Response path '{path}' array index {index} is out of range")
            current = current[index]
    return current


def _lookup(context: dict[str, Any], path: str) -> Any:
    return extract_path(context, path)


def render_template(value: Any, context: dict[str, Any]) -> Any:
    """Render placeholders recursively; an exact placeholder preserves its native type."""
    if isinstance(value, dict):
        return {key: render_template(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [render_template(item, context) for item in value]
    if not isinstance(value, str):
        return value

    exact = TOKEN_PATTERN.fullmatch(value)
    if exact:
        return _lookup(context, exact.group(1))

    def replace(match: re.Match[str]) -> str:
        resolved = _lookup(context, match.group(1))
        if isinstance(resolved, (dict, list)):
            return json.dumps(resolved, ensure_ascii=False)
        return str(resolved)

    return TOKEN_PATTERN.sub(replace, value)


def parse_json_object(raw: str | None, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def build_url(base_url: str, endpoint: str, context: dict[str, Any]) -> str:
    rendered = str(render_template(endpoint, context)).strip()
    parsed = urlparse(rendered)
    if parsed.scheme or parsed.netloc or rendered.startswith("//"):
        raise ValueError("Endpoint must be a relative path on the configured API host")
    url = urljoin(base_url.rstrip("/") + "/", rendered.lstrip("/"))
    base = urlparse(validate_public_https_url(base_url, "API Base URL"))
    target = urlparse(validate_public_https_url(url, "API endpoint"))
    if (base.hostname, base.port or 443) != (target.hostname, target.port or 443):
        raise ValueError("Endpoint must use the configured API host")
    return url


def build_headers(credentials: dict[str, str]) -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    fixed_headers = parse_json_object(credentials.get("fixed_headers_json"), "Fixed headers")
    for raw_name, raw_value in fixed_headers.items():
        name = str(raw_name).strip()
        if not HEADER_NAME_PATTERN.fullmatch(name) or name.lower() in FORBIDDEN_HEADERS:
            raise ValueError(f"Fixed header '{name}' is not allowed")
        if "\r" in str(raw_value) or "\n" in str(raw_value):
            raise ValueError(f"Fixed header '{name}' contains an invalid value")
        headers[name] = str(raw_value)
    api_key = str(credentials.get("api_key", "")).strip()
    if api_key:
        name = str(credentials.get("auth_header") or "Authorization").strip()
        if not HEADER_NAME_PATTERN.fullmatch(name) or name.lower() in FORBIDDEN_HEADERS:
            raise ValueError("Authentication Header is not allowed")
        prefix = str(credentials.get("auth_prefix") or "").strip()
        if "\r" in prefix or "\n" in prefix or "\r" in api_key or "\n" in api_key:
            raise ValueError("Authentication value contains invalid characters")
        headers[name] = f"{prefix} {api_key}".strip()
    return headers


def request_json(method: str, url: str, headers: dict[str, str], body: dict[str, Any], timeout: int) -> tuple[requests.Response, Any]:
    response = _request_with_safe_redirects(
        method.upper(),
        url,
        preserve_origin=True,
        headers=headers,
        json=body if method.upper() != "GET" else None,
        params=body if method.upper() == "GET" else None,
        timeout=(10, timeout),
    )
    if not response.ok:
        raise RuntimeError(f"API request failed with HTTP {response.status_code}")
    try:
        return response, response.json()
    except ValueError as exc:
        raise RuntimeError("API returned a non-JSON response") from exc


def decode_base64_media(value: str, default_mime: str) -> tuple[bytes, str]:
    if value.startswith("data:"):
        header, encoded = value.split(",", 1)
        mime = header[5:].split(";", 1)[0] or default_mime
    else:
        encoded = value
        mime = default_mime
    try:
        return base64.b64decode(encoded, validate=True), mime
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Media response is not valid Base64 data") from exc


def download_media(url: str, headers: dict[str, str], timeout: int) -> tuple[bytes, str]:
    # Never forward provider credentials to an arbitrary result/CDN URL.
    download_headers = {"Accept": "image/*,video/*,application/octet-stream"}
    with _request_with_safe_redirects("GET", url, headers=download_headers, timeout=(10, timeout), stream=True) as response:
        if not response.ok:
            raise RuntimeError(f"Media download failed with HTTP {response.status_code}")
        content_length = int(response.headers.get("Content-Length") or 0)
        if content_length > MAX_DOWNLOAD_BYTES:
            raise RuntimeError("Media file exceeds the 100 MiB download limit")
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise RuntimeError("Media file exceeds the 100 MiB download limit")
            chunks.append(chunk)
        mime = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0]
        return b"".join(chunks), mime


def media_bytes(value: Any, response_format: str, media_type: str, headers: dict[str, str], timeout: int) -> tuple[bytes, str, str | None]:
    if isinstance(value, list):
        if not value:
            raise ValueError("Media response array is empty")
        value = value[0]
    if not isinstance(value, str) or not value:
        raise ValueError("The configured media response path did not return a URL or Base64 string")

    default_mime = "image/png" if media_type == "image" else "video/mp4"
    detected = response_format
    if detected == "auto":
        detected = "url" if value.startswith(("http://", "https://")) else "base64"
    if detected == "url":
        blob, mime = download_media(value, headers, timeout)
        return blob, mime, value
    if detected == "base64":
        blob, mime = decode_base64_media(value, default_mime)
        return blob, mime, None
    raise ValueError(f"Unsupported response format: {response_format}")
