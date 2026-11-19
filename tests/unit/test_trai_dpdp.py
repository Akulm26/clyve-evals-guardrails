"""TRAI TCCCPR (Feb 2025 amendments) in automation_guard, and dpdp_guard."""
import copy

import pytest

from gtm_evals import dpdp_guard
from gtm_evals.automation_guard import check_send

SMS = {"tenant_id": "a", "workflow_tenant_id": "a", "contact": {"id": "c1", "tenant_id": "a", "consent": {"sms": True}},
       "channel": "sms", "template_id": "t1", "type": "promo", "ts_ist": "2026-11-18T12:30", "header": "AX-BRANDX-P",
       "dlt_template_id": "1107160000000000001", "dlt_template_category": "promotional"}


def send(policy, **over):
    e = copy.deepcopy(SMS)
    for k, v in over.items():
        if k == "contact":
            e["contact"].update(v)
        else:
            e[k] = v
    return check_send(e, [], policy)


class TestTrai:
    def test_clean_promo_sms(self, policy):
        assert send(policy)

    def test_needs_dlt_template(self, policy):
        assert "no DLT template ID" in send(policy, dlt_template_id=None).violations[0]

    def test_template_category_must_match(self, policy):
        assert "registered as 'service'" in send(policy, dlt_template_category="service").violations[0]

    @pytest.mark.parametrize("header,ok", [("AX-BRANDX-P", True), ("AX-BRANDX-S", False), ("ax-brandx-p", True), ("AXBRANDX", False)])
    def test_header_suffix(self, header, ok, policy):
        assert bool(send(policy, header=header)) is ok

    def test_transactional_header(self, policy):
        assert send(policy, type="transactional", header="JD-BANK-T", dlt_template_category="transactional",
                    ts_ist="2026-11-18T23:00")

    @pytest.mark.parametrize("days,ok", [(29, False), (89, False), (91, True)])
    def test_reconsent_lock(self, days, ok, policy):
        from datetime import datetime, timedelta
        out = (datetime(2026, 11, 18, 12, 30) - timedelta(days=days)).isoformat(timespec="minutes")
        v = send(policy, contact={"opt_outs": {"sms": out}}, is_consent_request=True)
        assert bool(v) is ok

    def test_reconsent_lock_only_applies_to_consent_requests(self, policy):
        assert send(policy, contact={"opt_outs": {"sms": "2026-11-10T10:00"}})

    @pytest.mark.parametrize("at,ok", [("2026-11-15T10:00", True), ("2026-11-01T10:00", False)])
    def test_transaction_consent_lasts_7_days(self, at, ok, policy):
        v = send(policy, contact={"consent": {"sms": {"granted": True, "at": at, "source": "transaction"}}})
        assert bool(v) is ok

    def test_explicit_dict_consent(self, policy):
        assert send(policy, contact={"consent": {"sms": {"granted": True, "at": "2025-01-01T10:00", "source": "explicit"}}})
        assert not send(policy, contact={"consent": {"sms": {"granted": False}}})

    def test_whatsapp_is_not_trai_dlt(self, send_event, policy):
        assert check_send(send_event, [], policy)    # no DLT / header fields needed

    def test_voice_gets_consent_rules_but_not_dlt(self, policy):
        assert send(policy, channel="voice", contact={"consent": {"voice": True}}, dlt_template_id=None, header="")


KIDS = {"category": "kids nutrition", "targeting": {"behavioural": False}, "parental_consent_records": True}


class TestDpdpCampaign:
    def test_contextual_kids_campaign_with_consent(self, policy):
        v = dpdp_guard.check_campaign(KIDS, policy)
        assert v and v.notes

    @pytest.mark.parametrize("targeting", [{"behavioural": True}, {"segments": ["abandoned cart"]}, {"segments": ["Lookalike 1%"]}])
    def test_behavioural_blocked(self, targeting, policy):
        v = dpdp_guard.check_campaign(dict(KIDS, targeting=targeting), policy)
        assert not v and "behavioural targeting" in v.violations[0]

    def test_no_parental_consent(self, policy):
        assert "parental consent" in dpdp_guard.check_campaign(dict(KIDS, parental_consent_records=False), policy).violations[0]

    @pytest.mark.parametrize("aud", [{"may_include_minors": True}, {"min_age": 13}])
    def test_audience_flags(self, aud, policy):
        assert not dpdp_guard.check_campaign({"category": "apparel", "audience": aud, "targeting": {"behavioural": True}}, policy)

    def test_adult_audience_untouched(self, policy):
        assert dpdp_guard.check_campaign({"category": "spice", "audience": {"min_age": 21}, "targeting": {"behavioural": True}}, policy)

    def test_no_child_data_processed(self, policy):
        assert dpdp_guard.check_campaign(dict(KIDS, processes_child_data=False, parental_consent_records=False), policy)


NOTICE = ("We collect your name and phone number to send you order updates. To withdraw consent, reply STOP. "
          "Grievances: write to privacy@brand.in. You may complain to the Data Protection Board of India.")


class TestDpdpNotice:
    def test_complete(self, policy):
        assert dpdp_guard.check_notice(NOTICE, policy)

    @pytest.mark.parametrize("cut,missing", [(" To withdraw consent, reply STOP.", "how to withdraw"),
                                             (" You may complain to the Data Protection Board of India.", "Data Protection Board")])
    def test_missing_parts(self, cut, missing, policy):
        v = dpdp_guard.check_notice(NOTICE.replace(cut, ""), policy)
        assert any(missing in x for x in v.violations)

    def test_empty(self, policy):
        assert len(dpdp_guard.check_notice("", policy).violations) == 5


class TestDpdpContact:
    def test_off_by_default(self, policy):
        assert dpdp_guard.check_contact({}, policy)

    def test_on(self, policy):
        policy["dpdp"]["require_consent_record"] = True
        assert not dpdp_guard.check_contact({}, policy)
        assert dpdp_guard.check_contact({"consent_record": {"id": "cr-1"}}, policy)
        assert not dpdp_guard.check_contact({"consent_record": {"id": "cr-1", "via_consent_manager": True}}, policy)
