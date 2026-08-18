from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from utils.adapter import (
    build_headers,
    build_url,
    extract_path,
    media_bytes,
    parse_json_object,
    render_template,
    request_json,
)


class GenerateMediaTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        prompt = str(tool_parameters.get("prompt") or "").strip()
        context = {
            "prompt": prompt,
            "model": tool_parameters.get("model") or "",
            "input_url": tool_parameters.get("input_url") or "",
            "parameters": parse_json_object(tool_parameters.get("parameters_json"), "Parameters"),
        }
        template = parse_json_object(tool_parameters.get("request_body_template"), "Request body template")
        body = render_template(template, context)
        headers = build_headers(self.runtime.credentials)
        timeout = int(tool_parameters.get("timeout_seconds") or 120)
        url = build_url(self.runtime.credentials["base_url"], str(tool_parameters["endpoint"]), context)
        _, response_data = request_json(str(tool_parameters.get("method") or "POST"), url, headers, body, timeout)
        value = extract_path(response_data, str(tool_parameters["media_response_path"]))
        blob, mime, source_url = media_bytes(
            value,
            str(tool_parameters.get("response_format") or "auto"),
            str(tool_parameters.get("media_type") or "image"),
            headers,
            timeout,
        )
        yield self.create_json_message({"source_url": source_url, "response": response_data})
        yield self.create_blob_message(blob=blob, meta={"mime_type": mime})

