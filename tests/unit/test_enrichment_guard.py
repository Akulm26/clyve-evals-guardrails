"""enrichment_guard: what an agent may write to a CRM."""
import pytest

from gtm_evals.enrichment_guard import _names_forbidden, check_write

TODAY = "2026-11-18"


def f(value, date="2026-11-10", source="https://x", **kw):
    return {"value": value, "source": source, "date": date, **kw}


def rec(fields, basis="legitimate_interest", **kw):
    return {"tenant_id": "a", "workflow_tenant_id": "a", "lawful_basis": basis, "fields": fields, **kw}


def test_clean_record(policy):
    assert check_write(rec({"company": f("Example Masala"), "work_email": f("rhea@examplemasala.in"), "ads": f(4)}), policy, TODAY)


class TestProvenance:
    def test_no_source(self, policy):
        assert "no source" in check_write(rec({"x": f("v", source="")}), policy, TODAY).violations[0]

    def test_no_date(self, policy):
        assert "no date" in check_write(rec({"x": {"value": "v", "source": "s"}}), policy, TODAY).violations[0]

    @pytest.mark.parametrize("date,msg", [("2025-01-01", "686 days old"), ("2026-12-01", "in the future"), ("last week", "unreadable date")])
    def test_bad_dates(self, date, msg, policy):
        assert msg in check_write(rec({"x": f("v", date=date)}), policy, TODAY).violations[0]

    def test_datetime_strings_accepted(self, policy):
        assert check_write(rec({"x": f("v", date="2026-11-10T09:30:00Z")}), policy, TODAY)

    def test_low_confidence(self, policy):
        assert "confidence 0.40" in check_write(rec({"x": f("v", confidence=0.4)}), policy, TODAY).violations[0]

    def test_bare_values_need_provenance_too(self, policy):
        v = check_write(rec({"x": "plain"}), policy, TODAY)
        assert any("no source" in x for x in v.violations) and any("no date" in x for x in v.violations)


class TestWhatMayBeStored:
    @pytest.mark.parametrize("field", ["religion", "founder_religion", "Gender", "pan", "bank-account-no", "caste_group", "Age"])
    def test_forbidden_fields(self, field, policy):
        assert "may never be stored" in check_write(rec({field: f("x")}), policy, TODAY).violations[0]

    @pytest.mark.parametrize("field", ["page_views", "company", "ads_running", "panel_size", "storage"])
    def test_similar_names_allowed(self, field, policy):
        assert check_write(rec({field: f("x")}), policy, TODAY)

    def test_names_forbidden_is_whole_word(self):
        assert _names_forbidden("founder_religion", {"religion"}) and _names_forbidden("bank_account_no", {"bank_account"})
        assert not _names_forbidden("page_views", {"age"})

    def test_allowed_fields_list(self, policy):
        policy["enrichment"]["allowed_fields"] = ["company"]
        v = check_write(rec({"company": f("X"), "headcount": f(40)}), policy, TODAY)
        assert v.violations == ["'headcount' is not in enrichment.allowed_fields"]


class TestContactDetails:
    def test_personal_email_needs_consent(self, policy):
        assert "personal email (gmail.com)" in check_write(rec({"email": f("r@gmail.com")}), policy, TODAY).violations[0]
        assert check_write(rec({"email": f("r@gmail.com")}, basis="consent"), policy, TODAY)

    def test_personal_phone_needs_consent(self, policy):
        assert not check_write(rec({"mobile": f("9876543210")}), policy, TODAY)
        assert check_write(rec({"office_phone": f("0172 400 0000")}), policy, TODAY)

    def test_rule_can_be_off(self, policy):
        policy["enrichment"]["work_contact_only"] = False
        assert check_write(rec({"email": f("r@gmail.com")}), policy, TODAY)

    def test_contact_details_need_a_lawful_basis(self, policy):
        v = check_write(rec({"work_email": f("r@brand.in")}, basis=None), policy, TODAY)
        assert "no lawful basis" in v.violations[-1]

    def test_pii_in_free_text(self, policy):
        v = check_write(rec({"notes": f("her number is 9876543210, PAN ABCDE1234F")}), policy, TODAY)
        assert "personal data in a free-text field (PHONE_IN, PAN)" in v.violations[0]


@pytest.mark.parametrize("change", [{"workflow_tenant_id": "b"}, {"tenant_id": None, "workflow_tenant_id": None}])
def test_tenant_isolation(change, policy):
    assert "tenant mismatch" in check_write(dict(rec({"x": f("v")}), **change), policy, TODAY).violations[0]


def test_empty_record(policy):
    assert check_write(rec({}), policy, TODAY)
