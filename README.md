# Universal Media API

Universal Media API is a configurable Dify tool plugin for connecting image and
video generation services without writing a separate plugin for every provider.
It supports synchronous JSON APIs and asynchronous submit-and-poll APIs.

Chinese documentation: [readme/README_zh_Hans.md](readme/README_zh_Hans.md)

## Features

- Synchronous image or video generation
- Asynchronous task submission and status polling
- Bearer tokens, raw API keys, and custom fixed headers
- Recursive JSON templates with native value types
- Configurable JSON response paths such as `$.data[0].url`
- URL and Base64 media responses
- Dify file output for downstream workflow nodes
- Public HTTPS-only destinations, redirect validation, and a 100 MiB download limit

## Provider credentials

Open **Tools > Universal Media API > Authorize** and configure:

| Field | Description |
| --- | --- |
| API Base URL | Public HTTPS origin, for example `https://api.example.com` |
| API Key | Optional provider credential |
| Authentication Header | Usually `Authorization` or `X-API-Key` |
| Authentication Prefix | Usually `Bearer`; leave empty for a raw key |
| Fixed Headers (JSON) | Optional string-to-string JSON object |

Endpoints configured in tool nodes must be relative paths on this API host.
Private networks, localhost, embedded URL credentials, plain HTTP, and
cross-origin API redirects are intentionally blocked.

## Synchronous example

Configure **Generate Media (Synchronous)** with values similar to:

```text
Model: provider-model-id
Endpoint: /v1/images/generations
Method: POST
Media Response Path: $.data[0].url
Response Format: URL
Media Type: Image
```

Request body template:

```json
{
  "model": "{{model}}",
  "prompt": "{{prompt}}",
  "size": "{{parameters.size}}",
  "response_format": "url"
}
```

Custom parameters:

```json
{"size": "2048x2048"}
```

Provider field names and response formats vary. Always follow the provider's
current API documentation.

## Asynchronous APIs

Use **Generate Media (Async + Polling)** when an API first returns a task ID.
Configure the submit endpoint and task-ID path, then configure a status endpoint
containing `{{task_id}}`, status path, success/failure values, and media path.

## Template variables

The following placeholders are available:

- `{{prompt}}`
- `{{model}}`
- `{{input_url}}`
- `{{task_id}}` in asynchronous status configuration
- `{{parameters.example}}` for values from Custom Parameters

An exact placeholder preserves its native JSON type. For example,
`"{{parameters.width}}"` becomes a JSON number when `width` is numeric.

## Data and security

Prompts, source URLs, custom parameters, and generated media are transmitted to
the API selected by the workspace administrator. Review that provider's terms
and privacy policy before use. Do not place secrets in prompts, templates, URLs,
or workflow variables. See [PRIVACY.md](PRIVACY.md) for the full disclosure.

## Development

```bash
uv sync --frozen --group dev
uv run pytest
```

Package from the parent directory:

```bash
dify plugin package ./dify-universal-media-plugin
```

## Support and source code

Source repository and issue tracker:
`https://github.com/menghuanshunjian/dify-universal-media-api`

Report bugs and request features through the repository's GitHub Issues page.

## License

MIT License. See [LICENSE](LICENSE).
