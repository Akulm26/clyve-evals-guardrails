"""core: Verdict, combine, policy merge and layering."""
import pytest

from gtm_evals import combine, list_profiles, load_policy
from gtm_evals.core import Verdict, _merge


class TestVerdict:
    def test_truthiness_is_passed(self):
        assert Verdict("g", True)
        assert not Verdict("g", False)

    def test_from_violations(self):
        assert Verdict.from_violations("g", []).passed
        v = Verdict.from_violations("g", ["bad"])
        assert not v.passed and v.violations == ["bad"] and not v.escalate

    def test_escalation_alone_fails(self):
        v = Verdict.from_violations("g", [], escalate=True)
        assert not v and v.escalate

    def test_to_dict_roundtrip(self):
        assert Verdict("g", False, ["x"], True).to_dict() == {"guard": "g", "passed": False, "violations": ["x"], "escalate": True}

    def test_violations_default_not_shared(self):
        a, b = Verdict("a", True), Verdict("b", True)
        a.violations.append("x")
        assert b.violations == []


class TestCombine:
    def test_all_pass(self):
        assert combine(Verdict("a", True), Verdict("b", True))

    def test_one_fail_prefixes_guard(self):
        v = combine(Verdict("a", True), Verdict("b", False, ["oops"]))
        assert not v and v.violations == ["[b] oops"] and v.guard == "combined"

    def test_escalate_propagates(self):
        assert combine(Verdict("a", False, [], escalate=True)).escalate

    def test_empty_combine_passes(self):
        assert combine().passed


class TestMerge:
    def test_nested_dicts_merge(self):
        assert _merge({"a": {"x": 1, "y": 2}}, {"a": {"y": 3}}) == {"a": {"x": 1, "y": 3}}

    def test_lists_replace(self):
        assert _merge({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}

    def test_dict_replaces_scalar_and_vice_versa(self):
        assert _merge({"a": 1}, {"a": {"b": 2}}) == {"a": {"b": 2}}
        assert _merge({"a": {"b": 2}}, {"a": 1}) == {"a": 1}

    def test_inputs_not_mutated(self):
        base, over = {"a": {"x": [1]}}, {"a": {"x": [2]}}
        out = _merge(base, over)
        out["a"]["x"].append(9)
        assert base == {"a": {"x": [1]}} and over == {"a": {"x": [2]}}

    def test_none_override(self):
        assert _merge({"a": 1}, None) == {"a": 1}


class TestLoadPolicy:
    def test_defaults_have_every_section(self, policy):
        for k in ("claims", "promise", "outreach", "automation", "action_gate", "visibility", "evals",
                  "manipulation", "deployment_gate"):
            assert k in policy

    def test_profile_layers_on_defaults(self, policy, clyve):
        assert policy["outreach"]["excluded_categories"] == []
        assert "real estate" in clyve["outreach"]["excluded_categories"]
        assert clyve["action_gate"]["kill_switch_env"] == "CLYVE_KILL_SWITCH"
        assert clyve["outreach"]["max_words"] == policy["outreach"]["max_words"]   # untouched keys kept

    def test_user_file_overrides_and_selects_profile(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text("profile: clyve\noutreach:\n  max_words: 90\n", encoding="utf-8")
        p = load_policy(f)
        assert p["outreach"]["max_words"] == 90
        assert "trading" in p["outreach"]["excluded_categories"]      # profile applied
        assert "profile" not in p

    def test_explicit_profile_beats_file_profile(self, tmp_path):
        f = tmp_path / "c.yaml"
        f.write_text("profile: nope\n", encoding="utf-8")
        assert load_policy(f, profile="clyve")["action_gate"]["kill_switch_env"] == "CLYVE_KILL_SWITCH"

    def test_unknown_profile_raises(self):
        with pytest.raises(FileNotFoundError):
            load_policy(profile="does-not-exist")

    def test_empty_user_file_is_fine(self, tmp_path, policy):
        f = tmp_path / "c.yaml"
        f.write_text("# only comments\n", encoding="utf-8")
        assert load_policy(f) == policy

    def test_autodiscovers_cwd_config(self, tmp_path):
        (tmp_path / "gtm-evals.yaml").write_text("outreach: {max_words: 77}\n", encoding="utf-8")
        assert load_policy()["outreach"]["max_words"] == 77   # conftest chdir'd into tmp_path

    def test_list_profiles(self):
        assert "clyve" in list_profiles()
