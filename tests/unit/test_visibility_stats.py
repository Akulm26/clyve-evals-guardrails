"""visibility_stats: frozen prompt sets, row validation, noise + chance bands."""
import pytest

from gtm_evals import visibility_stats as vs


def rows(checkpoint, rates, qt="niche", n=25, engine="chatgpt", surface="app"):
    out = []
    for run, rate in enumerate(rates):
        for i in range(n):
            out.append({"checkpoint": checkpoint, "query_type": qt, "engine": engine, "prompt_id": f"{qt}{i}",
                        "run": run, "mentioned": i < round(rate * n), "surface": surface, "screenshot_path": "s.png"})
    return out


class TestFrozen:
    PS = [{"id": "p1", "text": "best masala brand in Punjab", "type": "best_x"}, {"id": "p2", "text": "x", "type": "brand"}]

    def test_hash_is_order_independent_and_stable(self):
        assert vs.prompt_set_hash(self.PS) == vs.prompt_set_hash(list(reversed(self.PS)))

    def test_any_edit_changes_hash(self):
        edited = [dict(self.PS[0], text="best spice brand in Punjab"), self.PS[1]]
        with pytest.raises(ValueError):
            vs.check_frozen(edited, vs.prompt_set_hash(self.PS))

    def test_unchanged_passes(self):
        vs.check_frozen(self.PS, vs.prompt_set_hash(self.PS))


class TestValidateRows:
    def test_clean(self, policy):
        assert vs.validate_rows(rows("d0", [0.2, 0.3]), policy) == []

    def test_blended_and_unknown_query_types(self, policy):
        r = rows("d0", [0.2, 0.3]); r[0]["query_type"] = None; r[1]["query_type"] = "other"
        assert sum("blended" in p for p in vs.validate_rows(r, policy)) == 2

    def test_mixed_surfaces(self, policy):
        r = rows("d0", [0.2, 0.3]) + rows("d0", [0.2, 0.3], surface="api")
        assert any("mixed surfaces" in p for p in vs.validate_rows(r, policy))

    def test_app_rows_need_screenshots(self, policy):
        r = rows("d0", [0.2, 0.3]); r[0]["screenshot_path"] = ""
        assert any("no screenshot" in p for p in vs.validate_rows(r, policy))

    def test_too_few_runs(self, policy):
        assert any("< 2 runs" in p for p in vs.validate_rows(rows("d0", [0.2]), policy))


class TestRealChange:
    def test_noise_is_not_movement(self, policy):
        r = vs.real_change(rows("d0", [0.20, 0.28, 0.24]) + rows("d30", [0.28, 0.24, 0.32]), "d0", "d30", "niche", policy)
        assert not r["real"] and r["before"] == 0.24 and r["after"] == 0.28 and r["noise"] == 0.08

    def test_big_jump_is_real(self, policy):
        r = vs.real_change(rows("d0", [0.20, 0.24, 0.20]) + rows("d30", [0.60, 0.64, 0.56]), "d0", "d30", "niche", policy)
        assert r["real"] and r["verdict"] == "real movement" and r["delta"] > 0

    def test_drops_are_real_too(self, policy):
        assert vs.real_change(rows("d0", [0.6, 0.64]) + rows("d30", [0.2, 0.24]), "d0", "d30", "niche", policy)["delta"] < 0

    def test_must_beat_both_noise_and_chance(self, policy):
        # zero run-to-run noise, small sample: chance band still blocks a small move
        r = vs.real_change(rows("d0", [0.2, 0.2], n=10) + rows("d30", [0.3, 0.3], n=10), "d0", "d30", "niche", policy)
        assert r["noise"] == 0 and not r["real"]

    def test_engine_filter(self, policy):
        data = rows("d0", [0.2, 0.2]) + rows("d30", [0.8, 0.8]) + rows("d0", [0.2, 0.2], engine="gemini") + rows("d30", [0.2, 0.2], engine="gemini")
        assert vs.real_change(data, "d0", "d30", "niche", policy, engine="chatgpt")["real"]
        assert not vs.real_change(data, "d0", "d30", "niche", policy, engine="gemini")["real"]

    def test_missing_checkpoint_raises(self, policy):
        with pytest.raises(ValueError):
            vs.real_change(rows("d0", [0.2, 0.2]), "d0", "d30", "niche", policy)

    def test_run_rates(self):
        assert vs.run_rates(rows("d0", [0.2, 0.4], n=10), "d0", "niche") == [0.2, 0.4]


@pytest.mark.parametrize("n,expected", [(75, 0.16), (300, 0.08), (30, 0.253)])
def test_smallest_provable_move(n, expected):
    assert vs.smallest_provable_move(n) == pytest.approx(expected, abs=0.002)


def test_smallest_move_shrinks_with_more_runs():
    assert vs.smallest_provable_move(100) > vs.smallest_provable_move(400)
