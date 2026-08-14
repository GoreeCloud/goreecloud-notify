# ntfy Migration Boundary

GoreeCloud Notify is being built alongside ntfy, not in place of it yet.

The current migration inventory contains these ntfy topics:

- `goreecloud-beszel`
- `goreecloud-diun`
- `goreecloud-healthchecks`
- `goreecloud-uptime`
- `goreecloud-validation`
- `netbird-alerts`

Milestone 1 changes none of them.

A future compatibility endpoint will be designed in Milestone 2 so producers can move gradually. Final cutover is Milestone 6 and requires parallel operation, producer-by-producer validation, consumer validation, authentication/authorization validation, backup/restore evidence, an independent fallback alert path, and rollback readiness.
