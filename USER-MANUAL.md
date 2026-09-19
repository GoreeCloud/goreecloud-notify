# GoreeCloud Notify — User Manual

**Document Internal Version Number:** 2026.09.18.1  
**Document External Version Number:** 1.0.0  
**Status:** Repository user manual for the current release-candidate source  
**As of:** September 18, 2026  
**Central manual:** `GoreeCloud/User Manuals/User Manual — GoreeCloud Notify.docx`

## Before using Notify

GoreeCloud Notify is not yet production-accepted. Use only an approved deployment and account.

Do not treat the retired ntfy service as the current Notify application.

## Sign in

1. Open the approved GoreeCloud Notify URL.
2. Sign in with the account provisioned for that deployment.
3. Keep your session private and sign out on shared devices.

If authentication is rejected, do not bypass the application or private-network controls. Contact the deployment administrator.

## Inbox

The inbox shows notifications delivered to your account.

Depending on the current UI, you can:

- review delivered notifications;
- open notification details;
- mark delivery state/read state where available;
- use subscription and preference controls exposed to your account;
- receive realtime inbox updates through the authenticated stream.

If the realtime connection is interrupted, keep the application open or reconnect normally. The client is designed to reconcile against authoritative delivery state.

## Browser system alerts

Browser system alerts require an explicit user permission action.

Notify must not request browser notification permission silently.

If permission is:

- **granted:** alerts may be shown according to your Notify settings and browser/OS rules;
- **not yet decided:** use the visible enable action if you want system alerts;
- **denied:** change the browser/OS permission manually before retrying;
- **unsupported:** continue using the in-application inbox.

System alerts are a convenience layer; the inbox remains the authoritative user-facing delivery record.

## Linux client

The Flutter Linux client uses the same Notify service and account model.

Use the approved application build for the deployment. Do not enter production credentials into development or untrusted builds.

## Android client

The Flutter Android client can present persistent/system alerts when platform permission is granted.

Android permission is requested only from a user-initiated enable flow.

If Android does not grant notification permission, continue using the app inbox and change the platform permission manually if desired.

Production Android signing, installation, background-delivery, and physical-device acceptance remain separate release gates.

## Subscriptions and preferences

Use the application UI to manage the subscriptions/preferences exposed to your account.

Do not share producer credentials or administrator credentials as a substitute for user subscription access.

## Producers and integrations

Producer configuration is an administrator/integration task.

Applications that send notifications should use a dedicated least-privilege GoreeCloud Notify producer identity/token and the native API whenever practical.

The ntfy-compatible publishing path exists only for bounded migration compatibility.

## Privacy and sensitive content

Treat notification content as potentially sensitive.

Avoid placing passwords, private keys, recovery codes, session tokens, or other reusable secrets inside notifications.

Browser/OS notifications may appear outside the application window. Use minimized notification content appropriate to that risk.

## Troubleshooting

If Notify is unreachable:

1. confirm you are on the approved private network;
2. confirm the approved Notify hostname resolves;
3. retry the application normally;
4. do not disable TLS or authentication to force access;
5. report persistent outages through the approved independent outage path.

If the application behaves unexpectedly after reconnecting, refresh/reopen the client and verify the authoritative inbox state before assuming a notification was lost or duplicated.

## Recovery and support boundary

Backup/restore, Gateway/DNS/NetBird configuration, producer credentials, and production activation are administrator responsibilities.

A passing source test or successful login does not by itself prove the deployment is production-accepted.

