# 06 · Compliance map (India-first)

> Not legal advice. This maps rules to guards so engineering knows what to build. Verify the current position with a lawyer for each client category, and re-check this page quarterly. Rules here move.

## DPDP Act 2023 + DPDP Rules 2025

MeitY notified the DPDP Rules on 13 November 2025, with a phased rollout: institutional provisions immediately, Consent Manager registration from November 2026, and the core obligations for data fiduciaries fully in force around **May 2027** (18 months from notification).

**What it means for these systems:**

| Obligation (core, phasing in) | Where it bites | Guard / practice |
|---|---|---|
| Lawful basis / consent for processing personal data | Enriched founder emails and phones are personal data, even when "business" contacts | Store `lawful_basis` + `source` per contact; `outreach_guard` blocks contacts without one |
| Notice in clear terms | Lifecycle sign-ups for clients | Template check in intake |
| Withdrawal must be as easy as giving consent | Unsubscribe, WhatsApp STOP | Opt-out recall 1.0 in reply classifier; consent checked at send time |
| Purpose limitation, data minimisation | Enrichment pulling more than needed | `pii_guard` redacts before LLM calls; enrichment schema whitelists fields |
| Security safeguards, breach handling | Leads sheets, CRM exports, n8n creds | Tenant isolation, access logs |
| Grievance handling within a set period | Client brands | Inbound "delete my data" → human route |

**Practical line for Clyve now:** build as if the core obligations already apply. Retrofitting consent tracking into a running pipeline costs far more than storing two extra fields from day one.

## Telecom: SMS and calls (TRAI TCCCPR)

Commercial SMS needs DLT registration (entity, headers, templates) and must respect customer preferences. Promotional messages have time-window restrictions. Set the window in `policies/clyve_policy.yaml` → `automation.quiet_hours_ist` and confirm it against current TRAI rules before go-live.

## WhatsApp Business

Marketing messages need user opt-in and pre-approved templates outside the 24-hour service window. Meta enforces quality ratings, and low ratings throttle or block the number. → `outreach_guard` requires `whatsapp` in the contact's opt-in channels; `automation_guard` requires `template_approved: true`.

## Email deliverability (Gmail / Yahoo bulk-sender rules)

For bulk senders: SPF, DKIM and DMARC authenticated, one-click unsubscribe, and spam complaint rate kept below 0.3%. → policy stop at 0.1%, sender auth flags checked by `outreach_guard`.

## Advertising claims (ASCI; FSSAI for food/supplements)

Comparative claims, health claims and "No. 1" style claims need substantiation. → `claims_gate` (every claim traceable) + `judges/claim_safety.md` for `regulated: true` brands + human sign-off.

## Outside India

If a client sells into the EU/UK (GDPR, PECR) or US (CAN-SPAM, TCPA for SMS), add a jurisdiction flag to the contact record and a policy profile per jurisdiction. The guards are policy-driven, so you won't need new code for this.
