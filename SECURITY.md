# Security Policy

GoreeCloud Notify is in pre-production release-candidate development. Production acceptance and the ntfy cutover remain separate controlled operations.

## Wardveil Security

Security-facing GoreeCloud Notify presentation uses **Wardveil Security by GoreeCloud** as the platform-wide security and protection identity. The approved protection-status phrase is **Protected by Wardveil**.

Wardveil does not replace or supersede the application's technical security controls. GoreeCloud Notify authentication, authorization, session, CSRF, producer-token, input-validation, database-integrity, backup, monitoring, network, and deployment controls remain authoritative for their own technical state.

## Sensitive information

Do not commit or publish passwords, API tokens, session values, CSRF values, private keys, production environment files, recovery material, database contents, or other reusable credentials.

Repository examples and documentation must contain only non-secret placeholders or secret-reference names. Runtime observability intentionally excludes query strings, bodies, cookies, authorization headers, client IP addresses, user-agent strings, environment dumps, and raw unexpected-exception messages.

## Reporting a security issue

Report suspected security issues privately to the GoreeCloud administrator rather than opening a public issue or pull request containing vulnerability details, exploit material, credentials, private topology information, or non-public data.

When available, include the sanitized `X-Request-ID`, the affected GoreeCloud Notify version/build revision, the date/time, the workflow being attempted, and a minimal description of the observed behavior. Do not include passwords, tokens, cookies, private keys, or other reusable secrets merely to make a report more detailed.

The `X-Wardveil-Security` response header is security presentation metadata only; it is not proof that any specific authentication, authorization, TLS, backup, monitoring, or network control succeeded.
