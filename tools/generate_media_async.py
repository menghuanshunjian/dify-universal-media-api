import time
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


def _status_set(raw: str | None) -> set[str]:
    return {item.strip().lower() for item in str(raw or "").split(",") if item.strip()}


class GenerateMediaAsyncTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        timeout = int(tool_parameters.get("timeout_seconds") or 600)
        interval = int(tool_parameters.get("poll_interval_seconds") or 5)
        request_timeout = min(timeout, 120)
        context = {
            "prompt": str(tool_parameters.get("prompt") or "").strip(),
            "model": tool_parameters.get("model") or "",
            "input_url": tool_parameters.get("input_url") or "",
            "parameters": parse_json_object(tool_parameters.get("parameters_json"), "Parameters"),
        }
        headers = build_headers(self.runtime.credentials)

        submit_body = render_template(
            parse_json_object(tool_parameters.get("submit_body_template"), "Submit body template"), context
        )
        submit_url = build_url(self.runtime.credentials["base_url"], str(tool_parameters["submit_endpoint"]), context)
        _, submit_data = request_json(
            str(tool_parameters.get("submit_method") or "POST"), submit_url, headers, submit_body, request_timeout
        )
        task_id = extract_path(submit_data, str(tool_parameters["task_id_response_path"]))
        if task_id in {None, ""}:
            raise ValueError("The configured task ID response path returned an empty value")
        context["task_id"] = task_id
        yield self.create_json_message({"event": "submitted", "task_id": task_id, "response": submit_data})

        success_values = _status_set(tool_parameters.get("success_status_values"))
        failure_values = _status_set(tool_parameters.get("failure_status_values"))
        deadline = time.monotonic() + timeout
        last_status = None
        while time.monotonic() < deadline:
            status_body = render_template(
                parse_json_object(tool_parameters.get("status_body_template"), "Status body template"), context
            )
            status_url = build_url(self.runtime.credentials["base_url"], str(tool_parameters["status_endpoint"]), context)
            _, status_data = request_json(
                str(tool_parameters.get("status_method") or "GET"), status_url, headers, status_body, request_timeout
            )
            status = str(extract_path(status_data, str(tool_parameters["status_response_path"]))).strip()
            normalized_status = status.lower()
            if status != last_status:
                yield self.create_json_message({"event": "status", "task_id": task_id, "status": status})
                last_status = status

            if normalized_status in success_values:
                value = extract_path(status_data, str(tool_parameters["media_response_path"]))
                blob, mime, source_url = media_bytes(
                    value,
                    str(tool_parameters.get("response_format") or "auto"),
                    str(tool_parameters.get("media_type") or "video"),
                    headers,
                    request_timeout,
                )
                yield self.create_json_message(
                    {"event": "completed", "task_id": task_id, "status": status, "source_url": source_url, "response": status_data}
                )
                yield self.create_blob_message(blob=blob, meta={"mime_type": mime})
                return
            if normalized_status in failure_values:
                error_path = str(tool_parameters.get("error_response_path") or "").strip()
                detail = extract_path(status_data, error_path) if error_path else status_data
                raise RuntimeError(f"Media generation failed with status '{status}': {detail}")
            time.sleep(interval)

        raise TimeoutError(f"Media generation did not finish within {timeout} seconds. Task ID: {task_id}")

