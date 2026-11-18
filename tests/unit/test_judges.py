"""judges: templates, rendering, verdict normalisation, labelling sheets, calibration maths, manifest update."""
import pytest

from gtm_evals import judges

ALL = ["claim_safety", "description_accuracy", "on_thesis", "personalisation_factuality", "promise_check", "swap_test"]


def test_bundled_templates():
    assert judges.templates() == ALL


@pytest.mark.parametrize("name", ALL)
def test_every_template_renders_with_its_own_vars(name):
    t = judges.load_template(name)
    values = {v: f"<{v}>" for v in judges.template_vars(t)}
    system, user = judges.render(t, values)
    assert system and user and "{{" not in system + user
    assert judges.missing_vars(t, values) == []
    assert "SYSTEM" not in system[:10]


def test_load_template_from_path(tmp_path):
    p = tmp_path / "mine.md"
    p.write_text("doc\n---\nSYSTEM\nbe strict about {{x}}\nUSER\n{{text}}", encoding="utf-8")
    t = judges.load_template(str(p))
    assert judges.render(t, {"x": "A", "text": "B"}) == ("be strict about A", "B")


def test_unfilled_vars_left_visible_and_listed():
    t = "---\nSYSTEM\n{{a}}\nUSER\n{{b}}"
    assert judges.render(t, {"a": "1"}) == ("1", "{{b}}")
    assert judges.missing_vars(t, {"a": "1"}) == ["b"]


@pytest.mark.parametrize("out,v", [({"verdict": "pass"}, "pass"), ({"verdict": "PASS"}, "pass"), ({"verdict": "on"}, "pass"),
                                   ({"accuracy": "accurate"}, "pass"), ({"verdict": "fail"}, "fail"),
                                   ({"verdict": "unparseable"}, "fail"), ({}, "fail"), ({"verdict": "off"}, "fail")])
def test_normalise(out, v):
    assert judges.normalise(out) == v


class TestLabelSheets:
    def test_columns_put_text_first_and_labels_last(self):
        cols = judges.label_columns(judges.load_template("personalisation_factuality"))
        assert cols[:2] == ["id", "text"] and cols[-2:] == ["human_verdict", "why"]
        assert {"signals", "today", "freshness_days"} <= set(cols)

    def test_template_vars_deduplicated(self):
        assert judges.template_vars("{{a}} {{text}} {{a}}") == ["text", "a"]

    def test_blank_rows(self):
        rows = judges.blank_label_rows("{{text}}", n=3, defaults={"text": ""})
        assert [r["id"] for r in rows] == ["L01", "L02", "L03"] and set(rows[0]) == {"id", "text", "human_verdict", "why"}

    def test_count_labelled(self):
        rows = [{"human_verdict": "pass"}, {"human_verdict": "FAIL "}, {"human_verdict": None}, {"human_verdict": "maybe"}]
        assert judges.count_labelled(rows) == {"labelled": 2, "pass": 1, "fail": 1}


class TestCalibrate:
    def rows(self, n_pass, n_fail, blank=0):
        return ([{"id": f"P{i}", "human_verdict": "pass"} for i in range(n_pass)]
                + [{"id": f"F{i}", "human_verdict": "fail"} for i in range(n_fail)]
                + [{"id": f"B{i}", "human_verdict": None} for i in range(blank)])

    def test_perfect_agreement(self, stub_judge):
        stub_judge()
        res = judges.calibrate("t", self.rows(20, 10))
        assert res == {**res, "labelled_cases": 30, "agreement": 1.0}

    def test_disagreements_counted(self, stub_judge):
        stub_judge(flip={"P0", "F0", "F1"})
        res = judges.calibrate("t", self.rows(20, 10))
        assert res["agreement"] == pytest.approx(27 / 30)
        assert ("F0", "pass", "fail") in res["results"]

    def test_unlabelled_rows_cost_no_calls(self, stub_judge):
        calls = stub_judge()
        res = judges.calibrate("t", self.rows(2, 1, blank=40))
        assert res["labelled_cases"] == 3 and len(calls) == 3

    def test_no_labels(self, stub_judge):
        assert judges.calibrate("t", self.rows(0, 0, blank=3)) == {"labelled_cases": 0, "agreement": 0.0, "results": []}

    def test_today_defaults_to_send_date(self, stub_judge):
        calls = stub_judge()
        judges.calibrate("t", [{"id": "a", "human_verdict": "pass", "date_sent": "2026-11-01", "today": ""}])
        assert calls[0]["today"] == "2026-11-01"


class TestUpdateManifest:
    def test_writes_in_place_keeping_comments(self, tmp_path):
        m = tmp_path / "wf.yaml"
        m.write_text("# keep me\njudges:\n  - template: personalisation_factuality\n    labels: x.csv\n"
                     "    calibration: {labelled_cases: 0, agreement: 0}     # old\nowner: Akul\n", encoding="utf-8")
        assert judges.update_manifest(m, "personalisation_factuality", 34, 0.8824)
        text = m.read_text()
        assert "# keep me" in text and "owner: Akul" in text
        assert "calibration: {labelled_cases: 34, agreement: 0.88}" in text

    def test_only_the_named_judge_changes(self, tmp_path):
        m = tmp_path / "wf.yaml"
        m.write_text("judges:\n  - template: swap_test\n    calibration: {labelled_cases: 5, agreement: 0.5}\n"
                     "  - template: on_thesis\n    calibration: {labelled_cases: 0, agreement: 0}\n", encoding="utf-8")
        judges.update_manifest(m, "on_thesis", 31, 0.9)
        t = m.read_text()
        assert "{labelled_cases: 5, agreement: 0.5}" in t and "{labelled_cases: 31, agreement: 0.90}" in t

    def test_missing_entry_returns_false_and_leaves_file(self, tmp_path):
        m = tmp_path / "wf.yaml"
        m.write_text("judges: []\n", encoding="utf-8")
        assert not judges.update_manifest(m, "swap_test", 1, 1.0) and m.read_text() == "judges: []\n"

    def test_template_name_must_match_whole_word(self, tmp_path):
        m = tmp_path / "wf.yaml"
        m.write_text("judges:\n  - template: swap_test_v2\n    calibration: {labelled_cases: 0, agreement: 0}\n", encoding="utf-8")
        assert not judges.update_manifest(m, "swap_test", 1, 1.0)


class TestRunParsing:
    """judges.run with a fake `anthropic` module: JSON is pulled out of the reply, junk becomes 'unparseable'."""

    @pytest.fixture(autouse=True)
    def _real(self, real_judge_run):
        pass

    def fake_sdk(self, monkeypatch, reply):
        import sys
        import types
        sent = {}

        class Messages:
            def create(self, **kw):
                sent.update(kw)
                return types.SimpleNamespace(content=[types.SimpleNamespace(text=reply)])

        mod = types.SimpleNamespace(Anthropic=lambda: types.SimpleNamespace(messages=Messages()))
        monkeypatch.setitem(sys.modules, "anthropic", mod)
        return sent

    def test_json_inside_prose(self, monkeypatch):
        sent = self.fake_sdk(monkeypatch, 'Sure! {"verdict": "pass", "statements": []} hope that helps')
        out = judges.run("---\nSYSTEM\nbe strict\nUSER\n{{text}}", {"text": "hi"}, model="m1")
        assert out["_verdict"] == "pass" and sent["model"] == "m1" and sent["system"] == "be strict"
        assert sent["messages"] == [{"role": "user", "content": "hi"}]

    def test_unparseable_reply_fails(self, monkeypatch):
        self.fake_sdk(monkeypatch, "I refuse to answer in JSON")
        out = judges.run("---\nSYSTEM\nx\nUSER\ny", {})
        assert out["verdict"] == "unparseable" and out["_verdict"] == "fail"

    def test_model_from_env(self, monkeypatch):
        sent = self.fake_sdk(monkeypatch, '{"verdict": "fail"}')
        monkeypatch.setenv("JUDGE_MODEL", "env-model")
        judges.run("---\nSYSTEM\nx\nUSER\ny", {})
        assert sent["model"] == "env-model"

