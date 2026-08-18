# Privacy Policy

Last updated: August 18, 2026

Universal Media API is a configurable Dify tool plugin. It does not operate an
independent backend, use analytics, create user profiles, or intentionally store
prompts, media, credentials, or API responses outside the Dify runtime.

## Data processed

Depending on a workflow's configuration, the plugin may process and transmit:

- generation prompts and model identifiers;
- source image or video URLs;
- custom request parameters and fixed HTTP headers;
- API credentials configured by a workspace administrator; and
- generated image or video data returned by the configured service.

This content may contain personal or sensitive data if a user includes such data
in a prompt, source URL, source file, header, or custom parameter.

## Purpose and third-party disclosure

The plugin transmits configured request data to the HTTPS API host selected by
the workspace administrator. It may download generated media from a public HTTPS
URL returned by that host. Those services are independent third parties and
process data under their own terms and privacy policies. Because the destination
is user-configurable, this plugin cannot enumerate every possible recipient.

Workspace administrators are responsible for reviewing the selected provider's
privacy policy, obtaining any required consent, and avoiding providers that are
not appropriate for the data being processed.

## Storage and retention

The plugin does not add persistent storage. Dify and the configured third-party
provider may retain workflow inputs, logs, credentials, API responses, or media
according to their respective configuration and policies.

## Security

The plugin requires HTTPS, rejects private and non-public network destinations,
does not place credentials in result messages, and does not forward provider
authorization headers to media download URLs. No Internet transmission method is
guaranteed to be completely secure.

## Contact

For privacy or security questions, use the support channel published in the
plugin's README and source repository.
