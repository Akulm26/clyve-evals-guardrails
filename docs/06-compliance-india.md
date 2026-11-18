# 06 · Compliance map (India-first)

> Not legal advice. This page maps rules to guards so engineering knows what to build. Confirm the current position with a lawyer for each client category. **Last checked: 18 Nov 2026.** Re-check quarterly, because these rules keep changing.

## DPDP Act 2023 + DPDP Rules 2025

- MeitY notified the DPDP Rules on 13 Nov 2025. [HSA Advocates via Mondaq]
- Rollout comes in three stages on fixed dates: 14 Nov 2025, 14 Nov 2026 and 14 May 2027. [AMS Shardul]
- Consent Manager registration starts in **Nov 2026**. The core obligations for data fiduciaries (businesses holding personal data) apply in full by **May 2027**. [Legal500; Conventus Law]
- Data fiduciaries and Consent Managers must resolve grievances within **90 days** at most. [AMS Shardul]

| Obligation | Where it bites | Guard / practice |
|---|---|---|
| Lawful basis or consent for processing | Enriched founder emails and phones are personal data, even as "business" contacts | Store `lawful_basis` + `source` per contact. `outreach_guard` blocks contacts without one |
| Clear notice | Lifecycle sign-ups for clients | Template check at intake |
| Withdrawing consent as easy as giving it | Unsubscribe, WhatsApp STOP | Opt-out recall must be 1.0 in the reply classifier; consent checked at send time |
| Purpose limitation, data minimisation | Enrichment pulling more fields than needed | `pii_guard` redacts before LLM calls; enrichment schema whitelists fields |
| Grievance handling (≤ 90 days) | "Delete my data" requests | Inbound deletion requests → human route, logged with a date |

**Practical line:** build as if the May 2027 obligations already apply. Adding two fields now is cheap. Retrofitting consent tracking into a live pipeline isn't.

## SMS and calls: TRAI TCCCPR (2018, amended Feb 2025)

- **Mixed messages count as promotional.** If promotional content is mixed into a service or transactional message, the whole message is treated as promotional and the promotional pre-checks apply. [Khaitan & Co]
- **Number series.** Normal 10-digit numbers can't be used for telemarketing: 140 for promotional calls, 1600 for transactional and service calls. [Mondaq]
- **Header tags.** SMS headers carry a type suffix: -P promotional, -S service, -T transactional, -G government. [Ensure IAS]
- **Delivery window.** From late Oct 2025, Service Explicit SMS can only be delivered **10:00 AM–9:00 PM**, and messages outside that band are auto-rejected. [SMSGatewayHub; Meritto]
- **SE becomes promotional.** Service Explicit templates were scheduled to move to the Promotional category from March 2026. [Fast2SMS]

→ `src/gtm_evals/data/default.yaml` sets `automation.quiet_hours_ist` to **21:00–10:00**, matching that window. `automation_guard` blocks promotional types inside it. Treat any message with an offer in it as promotional, which matches TRAI's mixed-content rule.

## WhatsApp Business Platform

- **24-hour window.** Free-form replies are allowed only within 24 hours of the user's last message. Outside that window, only approved templates. [WhatsApp Business Policy; Rasayel]
- **Opt-in.** Business-initiated messages outside the window need prior opt-in. [CM.com]
- **Opt-out.** Opt-out requests must be honoured. [OnVoard]
- **Escalation.** Automation in the window must offer a clear path to a human: agent transfer, phone or email. [Rasayel]
- **Template categories.** A template that mixes utility content with promotion is classed as marketing. [SleekFlow]

→ `outreach_guard` requires `whatsapp` in the contact's `optin_channels`. `automation_guard` requires `template_approved: true`. The reply agent always has `escalate` as an allowed action. Keep utility templates free of offers.

## Email: Gmail / Yahoo bulk-sender rules

- **Who counts.** Gmail treats senders of about **5,000+ messages a day** to Gmail accounts as bulk senders. [Bird]
- **Requirements.** SPF, DKIM and DMARC alignment, one-click unsubscribe, and a spam rate below **0.3%**. Gmail is actively enforcing this, with rate limiting or rejection for non-compliant mail. [Red Sift]
- **Aim lower.** Target under 0.1%. Above 0.3%, you lose access to Gmail's mitigation support until you've held under 0.3% for seven straight days. [Red Sift]
- **Unsubscribe timing.** One-click unsubscribe must follow RFC 8058, and unsubscribe requests must be processed within 48 hours. [Red Sift]

→ The policy stops sending at a 0.1% complaint rate (`stop_spam_complaint_rate: 0.001`) and checks the SPF/DKIM/DMARC flags. Cold outreach at Clyve's volume sits well below the bulk threshold, but follow the same rules anyway. Once a domain is classified as a bulk sender, that classification is permanent. [OneSignal]

## Advertising claims (ASCI; FSSAI for food and supplements)

Comparative, health and "No. 1" claims need substantiation. → `claims_gate` (every claim traceable) + `judges/claim_safety.md` for `regulated: true` brands + human sign-off. *Not yet verified against the current ASCI code. Check per category before go-live.*

## Outside India

If a client sells into the EU/UK (GDPR, PECR) or the US (CAN-SPAM, TCPA for SMS), add a jurisdiction flag to the contact record and a policy profile per jurisdiction. The guards read from policy, so this needs no new code.

## Sources

- HSA Advocates via Mondaq — DPDP Rules 2025 analysis: https://www.mondaq.com/india/data-protection/1708434/
- AMS Shardul — DPDP enforcement dates: https://www.amsshardul.com/insight/enforcement-of-the-dpdp-act-and-notification-of-the-dpdp-rules/
- Legal500 — DPDP phased implementation: https://www.legal500.com/developments/?p=53484
- Conventus Law — DPDP 18-month timeline: https://conventuslaw.com/?p=131129
- Khaitan & Co — TCCCPR Second Amendment: https://khaitanco.com/thought-leadership/Efforts-to-Curb-Spam-Continue-TRAI-Releases-Second-Amendment-to-the-TCCCPR-2018
- Mondaq — TCCCPR amendments: https://webiis08.mondaq.com/india/telecoms-mobile-cable-communications/1586718/
- Ensure IAS — TCCCPR header tags: https://www.ensureias.com/blog/current-affairs/trai-tightens-rules-to-curb-spam-calls-and-text-messages
- SMSGatewayHub — SE delivery window: https://crm.smsgatewayhub.com/knowledge-base/article/explicit-message-delivery-time-in-india-new-trai-guidelines-2025
- Meritto — SE delivery window: https://help.meritto.com/portal/en/kb/articles/update-change-in-delivery-timings-for-sms-service-explicit-messages
- Fast2SMS — SE to Promotional migration: https://www.fast2sms.com/help/?p=16132
- WhatsApp Business Policy: https://whatsappbusiness.com/policy/?product=marketing
- Rasayel — WhatsApp messaging policy: https://learn.rasayel.io/en/books/whatsapp/whatsapp-business/whatsapp-business-messaging-policy
- CM.com — WhatsApp opt-in: https://www.cm.com/en-za/blog/whatsapp-opt-in/
- OnVoard — WhatsApp 24-hour window: https://onvoard.com/compliance/whatsapp
- SleekFlow — WhatsApp templates: https://sleekflow.io/en-us/blog/whatsapp-business-template
- Bird — Gmail and Yahoo sender requirements: https://bird.com/docs/knowledge-base/deliverability/gmail-yahoo-requirements
- Red Sift — Gmail enforcement: https://redsift.com/blog/gmails-enforcement-ramps-up-what-bulk-senders-need-to-know
- OneSignal — bulk sender classification: https://documentation.onesignal.com/docs/new-google-and-yahoo-email-updates
