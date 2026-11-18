"""automation_guard: tenant isolation, consent, idempotency, caps, quiet hours, audience sanity, reply allowlist."""
import copy

import pytest

from gtm_evals.automation_guard import check_reply, check_send


def send(ev, policy, history=(), **over):
    e = copy.deepcopy(ev); e.update(over)
    return check_send(e, list(history), policy)


def test_clean_send_passes(send_event, policy):
    assert send(send_event, policy)


class TestTenants:
    @pytest.mark.parametrize("field", ["tenant_id", "workflow_tenant_id"])
    def test_mismatch(self, field, send_event, policy):
        assert "tenant mismatch" in send(send_event, policy, **{field: "b"}).violations[0]

    def test_contact_from_other_tenant(self, send_event, policy):
        c = dict(send_event["contact"], tenant_id="b")
        assert not send(send_event, policy, contact=c)

    def test_missing_tenant(self, send_event, policy):
        assert not send(send_event, policy, tenant_id=None, workflow_tenant_id=None,
                        contact=dict(send_event["contact"], tenant_id=None))


class TestConsent:
    def test_no_consent(self, send_event, policy):
        c = dict(send_event["contact"], consent={"whatsapp": False})
        assert "no current whatsapp consent" in send(send_event, policy, contact=c).violations

    def test_unapproved_whatsapp_template(self, send_event, policy):
        assert "WhatsApp template not approved" in send(send_event, policy, template_approved=False).violations

    def test_email_needs_no_template_approval(self, send_event, policy):
        assert send(send_event, policy, channel="email", template_approved=False)


class TestFrequency:
    def h(self, ts, template="t0", channel="whatsapp"):
        return {"contact_id": "c1", "template_id": template, "channel": channel, "ts_ist": ts}

    def test_duplicate_inside_window(self, send_event, policy):
        v = send(send_event, policy, [self.h("2026-11-18T09:00", template="t1")])
        assert any("duplicate" in x for x in v.violations)

    def test_same_template_outside_window_ok(self, send_event, policy):
        assert send(send_event, policy, [self.h("2026-11-16T09:00", template="t1")])

    def test_frequency_cap(self, send_event, policy):
        hist = [self.h("2026-11-15T12:00"), self.h("2026-11-16T12:00")]
        assert any("frequency cap: 2 whatsapp" in x for x in send(send_event, policy, hist).violations)

    def test_cap_ignores_other_channels_and_old_sends(self, send_event, policy):
        hist = [self.h("2026-11-15T12:00", channel="email"), self.h("2026-11-01T12:00")]
        assert send(send_event, policy, hist)


class TestQuietHours:
    @pytest.mark.parametrize("ts,ok", [("2026-11-18T21:00", False), ("2026-11-18T23:59", False),
                                       ("2026-11-18T09:59", False), ("2026-11-18T10:00", True),
                                       ("2026-11-18T20:59", True)])
    def test_boundaries(self, ts, ok, send_event, policy):
        assert bool(send(send_event, policy, ts_ist=ts)) is ok

    def test_transactional_allowed_at_night(self, send_event, policy):
        assert send(send_event, policy, ts_ist="2026-11-18T23:00", type="transactional")

    @pytest.mark.parametrize("extra", [{"has_offer": True}, {"body": "Your order shipped! Use code SAVE10 for 10% off."}])
    def test_offer_inside_service_message_is_promotional(self, extra, send_event, policy):
        assert not send(send_event, policy, ts_ist="2026-11-18T23:00", type="transactional", **extra)

    def test_type_is_case_insensitive(self, send_event, policy):
        assert not send(send_event, policy, ts_ist="2026-11-18T23:00", type="PROMO")


class TestAudience:
    def test_jump(self, send_event, policy):
        assert any("audience jumped" in x for x in send(send_event, policy, audience_size=42000).violations)

    def test_no_history_no_check(self, send_event, policy):
        assert send(send_event, policy, audience_size=42000, last_audience_size=None)


class TestReply:
    @pytest.mark.parametrize("inbound", ["Where is my order?", "What are your store hours?", "How much is the 200g pack?"])
    def test_allowlisted_questions_auto_reply(self, inbound, policy):
        assert check_reply({"action": "answer_faq", "text": "Here you go."}, inbound, policy)

    @pytest.mark.parametrize("inbound", ["I want a refund", "This gave me an allergy", "I'll take you to consumer court",
                                         "paise wapas karo"])
    def test_sensitive_topics_escalate(self, inbound, policy):
        v = check_reply({"action": "answer_faq", "text": "ok"}, inbound, policy)
        assert not v and v.escalate and "sensitive topic" in v.violations[0]

    def test_unknown_question_goes_to_human(self, policy):
        v = check_reply({"action": "answer_faq", "text": "sure"}, "Can you sponsor my podcast?", policy)
        assert not v and "not a known-safe question" in v.violations[0]

    def test_bot_offering_discount_escalates(self, policy):
        assert not check_reply({"action": "answer_faq", "text": "Here's 50% off!"}, "Where is my order?", policy)

    def test_escalating_is_always_allowed(self, policy):
        assert check_reply({"action": "escalate", "text": "Passing you to a person."}, "I want a refund", policy)

    def test_disallowed_action(self, policy):
        v = check_reply({"action": "issue_refund", "text": "done"}, "Where is my order?", policy)
        assert any("not in allowed list" in x for x in v.violations)
