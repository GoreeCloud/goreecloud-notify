# GoreeCloud Notify Manual Browser and Operating-System Acceptance

## Purpose

I use this procedure to collect, sanitize, validate, and retain the real human/browser/operating-system evidence required by GitHub issue #55 before I treat GoreeCloud Notify's Milestone 3 and 4 web experience as manually accepted.

This procedure does not automate the manual checks. It only makes the evidence contract deterministic and fail-closed after I perform the checks myself. Playwright, Axe, CI, Production Readiness, and Monitoring Alert Readiness remain complementary automated evidence and do not substitute for this procedure.

Passing this manual gate also does not authorize production deployment or ntfy cutover. Backup/restore, independent monitoring/out-of-band alerting, target runtime/private publication, controlled migration, and rollback remain separate gates.

## Source authority

The machine-readable contract is:

`deploy/acceptance/manual_browser_os_acceptance.json`

The validator is:

`deploy/acceptance/validate_manual_browser_evidence.py`

The contract is bound to GitHub issue #55 and requires the candidate to remain a release candidate with production acceptance pending while this evidence is collected. A production-mode runtime is not the same thing as an accepted production release.

## Historical evidence boundary

The permanent GoreeCloud Notify records already document a real Firefox 153.0.4 / Zorin OS 17.3 Pro candidate session against the frozen `v0.2.0` source. That session covered substantial keyboard, focus, 200% zoom/reflow, Orca screen-reader, two-tab realtime, browser-permission, and redacted desktop-alert behavior.

I do not reconstruct a passing evidence bundle from that narrative record. The same permanent record states that enabled-alert backlog/replay no-alert-storm behavior was not conclusively proven and that exact viewport evidence, explicit Auto/Light/Dark confirmation, logout/login round-trip evidence, and separate sidebar Unread/Read filter confirmation were not captured. Later source hardening also changed the current `main` revision and application identity after the frozen `v0.2.0` candidate session.

For issue #55 closure, I therefore collect a fresh, explicit evidence bundle against the exact candidate revision I intentionally want to accept. Historical observations may guide the session, but missing evidence is not backfilled from memory.

## Evidence file handling

I create the evidence JSON outside source control or under an ignored filename matching:

`goreecloud-notify-manual-browser-acceptance*.json`

The file is Internal acceptance evidence. Before permanent storage or documentation, I sanitize it and verify that it contains no reusable credentials, cookies, CSRF values, session material, private keys, recovery information, producer tokens, raw private notification content, or other unnecessary personal data.

I use synthetic notification data for the acceptance session. Screenshots are either sanitized before retention or not retained.

## Required session metadata

Every recorded acceptance session must include:

- a unique session identifier;
- an ISO-8601 date/time with timezone;
- browser name and exact browser version;
- operating-system name and version;
- device/viewport class;
- exact CSS viewport width and height;
- screen-reader name/version when that session supplies screen-reader evidence;
- the exact HTTPS candidate URL;
- the exact 40-character Git build revision under acceptance.

All sessions in one evidence bundle must target the same candidate URL and exact build revision.

## Required manual checks

The machine-readable contract is authoritative for the exact check identifiers. It covers:

- keyboard traversal of sign-in, inbox, filters/search/pagination, notification detail/actions, subscription controls, appearance settings, system-alert settings, and logout/login;
- logical focus order, absence of keyboard traps, and visible focus;
- screen-reader names/roles/landmarks, reading order, status/error/realtime/mutation feedback;
- 200% zoom/reflow without lost functionality or unintended horizontal document overflow;
- practical Glaze UI contrast, readability, spacing, and hierarchy review;
- explicit Auto, Light, and Dark appearance confirmation;
- separate sidebar Unread and Read filter confirmation;
- two-tab realtime delivery with independent selection and understandable cross-tab read/unread/acknowledgement reconciliation;
- connection/reconnection clarity and absence of confusing duplicate system alerts;
- no automatic browser permission prompt;
- explicit permission grant and deny behavior;
- app-level alert disablement after grant;
- external browser-permission revocation reconciliation;
- generic/redacted operating-system alert presentation;
- foreground suppression with understandable hidden-page behavior;
- reconnect/replay/backlog behavior with system alerts enabled and no alert storm.

Every required check must have exactly one final result in the evidence bundle. A `fail` result must link to a dedicated `GoreeCloud/goreecloud-notify` issue and prevents the validator from passing. I do not use `not_applicable` to bypass a required issue #55 check.

## Evidence shape

The evidence JSON uses this top-level structure:

```json
{
  "schema_version": 1,
  "evidence_kind": "goreecloud-notify-manual-browser-os-acceptance",
  "sanitized": true,
  "captured_at": "2026-08-18T21:45:00-05:00",
  "candidate": {
    "service_url": "https://notify-rc.goreecloud.com",
    "build_revision": "<exact-40-character-git-sha>",
    "release_stage": "release_candidate",
    "production_accepted": false,
    "acceptance_status": "pending"
  },
  "sessions": [],
  "checks": [],
  "privacy": {
    "synthetic_test_data_only": true,
    "raw_notification_content_recorded": false,
    "reusable_secrets_recorded": false,
    "screenshots_sanitized_or_not_retained": true
  }
}
```

I populate `sessions` and `checks` from what I actually observed. I do not commit a completed acceptance evidence file merely to make CI green; the evidence represents a real manual session and is reviewed before permanent storage.

## Validation

After completing and sanitizing the evidence, I run:

```bash
python deploy/acceptance/validate_manual_browser_evidence.py \
  goreecloud-notify-manual-browser-acceptance.json \
  --expected-revision <exact-deployed-git-sha>
```

The validator fails closed when:

- the evidence is incomplete;
- a required check is missing or duplicated;
- a check is marked failed;
- a failed check lacks a dedicated defect issue;
- a screen-reader check references a session without a real screen reader/version;
- browser, OS, viewport, time, URL, or revision metadata is missing or placeholder text;
- a session targets a different URL or revision from the candidate;
- the candidate revision differs from the explicitly expected revision;
- the candidate is incorrectly represented as production accepted;
- the candidate URL is not HTTPS or contains credentials/query material;
- required privacy assertions are not satisfied;
- prohibited sensitive-data fields appear in the evidence structure.

A validator PASS means the evidence bundle is complete and internally consistent with the source issue #55 contract. It does not prove the observations were performed correctly by itself; the observations remain human evidence.

## Closure procedure for issue #55

I close issue #55 only after all of the following are true:

1. I performed the required checks against the exact candidate revision I intend to accept.
2. The evidence records browser, OS, viewport, date/time, candidate URL, and exact Git revision for every session.
3. Every required check has a final `pass` result.
4. Any defect found during testing has a dedicated issue and is resolved/retested before the final passing bundle is produced.
5. The evidence contains only sanitized synthetic acceptance data and no reusable secrets or raw private notification content.
6. `validate_manual_browser_evidence.py` passes with the candidate's exact revision supplied through `--expected-revision`.
7. I update `docs/milestone-4-acceptance.md`, issue #55, and the permanent GoreeCloud Notify records with the actual outcome.

Issue #55 closure remains necessary but not sufficient for production acceptance. I keep ntfy active until the complete production and migration gates are intentionally satisfied.
