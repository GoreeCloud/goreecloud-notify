# Notify producer integrations

GoreeCloud Notify accepts scoped producer notifications through `POST /api/v1/notifications`. Integration records in this directory define the minimum source, channel, event vocabulary, privacy boundary, authority split, and production-acceptance requirements for specific GoreeCloud producers.

`monitor-producer.json` defines the GoreeCloud Monitor producer contract. Monitor remains authoritative for monitoring state; Notify is authoritative for notification delivery. Successful publication is never health evidence, and Notify must not become the sole outage-alert destination for Notify itself.

These records do not provision producer tokens, create channels, migrate live producers, change routing, or authorize production cutover. Runtime acceptance and rollback evidence remain separate requirements.
