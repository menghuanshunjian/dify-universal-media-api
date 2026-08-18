import base64

import pytest

from utils.adapter import build_headers, build_url, decode_base64_media, extract_path, render_template, validate_public_https_url


def test_extract_path_supports_root_dot_and_array() -> None:
    payload = {"data": [{"url": "https://example.com/a.png"}]}
    assert extract_path(payload, "$.data[0].url") == "https://example.com/a.png"


def test_extract_path_raises_for_missing_key() -> None:
    with pytest.raises(KeyError):
        extract_path({"data": {}}, "$.data.url")


def test_render_template_preserves_native_exact_value() -> None:
    context = {"prompt": "draw", "parameters": {"width": 1024, "options": {"n": 2}}}
    template = {
        "prompt": "{{prompt}}",
        "width": "{{parameters.width}}",
        "options": "{{parameters.options}}",
        "label": "size-{{parameters.width}}",
    }
    assert render_template(template, context) == {
        "prompt": "draw",
        "width": 1024,
        "options": {"n": 2},
        "label": "size-1024",
    }


def test_decode_data_uri() -> None:
    raw = b"fake-image"
    value = "data:image/png;base64," + base64.b64encode(raw).decode()
    assert decode_base64_media(value, "application/octet-stream") == (raw, "image/png")


def test_build_url_rejects_absolute_endpoint() -> None:
    with pytest.raises(ValueError, match="relative path"):
        build_url("https://api.example.com", "https://evil.example/path", {})


def test_decode_rejects_invalid_base64() -> None:
    with pytest.raises(ValueError, match="valid Base64"):
        decode_base64_media("not base64!", "image/png")


def test_private_ip_is_rejected() -> None:
    with pytest.raises(ValueError, match="public IP"):
        validate_public_https_url("https://127.0.0.1/resource")


def test_dangerous_fixed_header_is_rejected() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        build_headers({"fixed_headers_json": '{"Host":"internal.example"}'})
