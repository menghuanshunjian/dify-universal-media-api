import json

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from utils.adapter import validate_public_https_url


class UniversalMediaProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, str]) -> None:
        base_url = str(credentials.get("base_url", "")).strip()
        try:
            validate_public_https_url(base_url, "API Base URL")
        except ValueError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc

        try:
            headers = json.loads(credentials.get("fixed_headers_json") or "{}")
        except json.JSONDecodeError as exc:
            raise ToolProviderCredentialValidationError(f"Fixed headers is not valid JSON: {exc}") from exc
        if not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
            raise ToolProviderCredentialValidationError("Fixed headers must be a JSON object containing string values")
