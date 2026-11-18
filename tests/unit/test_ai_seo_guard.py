"""ai_seo_guard: robots.txt (RFC 9309), raw HTML without JavaScript, JSON-LD schema, entity consistency."""
import json

import pytest

from gtm_evals import ai_seo_guard as seo

ANSWER = ["OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User", "Googlebot", "Bingbot"]


class TestRobotsParsing:
    def test_groups_and_shared_agent_lines(self):
        g = seo.parse_robots("User-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n")
        assert g[0]["agents"] == ["gptbot", "claudebot"] and g[0]["rules"] == [(False, "/")]
        assert g[1]["agents"] == ["*"]

    def test_comments_blank_lines_and_unknown_keys(self):
        g = seo.parse_robots("# hi\nUser-agent: * # everyone\nCrawl-delay: 5\nDisallow: /x # private\nSitemap: https://a/s.xml\n")
        assert g == [{"agents": ["*"], "rules": [(False, "/x")]}]

    def test_sitemap_between_agents_starts_new_group(self):
        g = seo.parse_robots("User-agent: a\nDisallow: /\nSitemap: s\nUser-agent: b\nDisallow: /b\n")
        assert [x["agents"] for x in g] == [["a"], ["b"]]

    def test_empty_disallow_allows_everything(self):
        assert seo.is_allowed(seo.parse_robots("User-agent: *\nDisallow:\n"), "PerplexityBot", "/anything")

    def test_rules_before_any_agent_are_ignored(self):
        assert seo.parse_robots("Disallow: /\n") == []


class TestIsAllowed:
    @pytest.mark.parametrize("robots,agent,path,allowed", [
        ("", "GPTBot", "/", True),
        ("User-agent: *\nDisallow: /\n", "PerplexityBot", "/", False),
        ("User-agent: *\nDisallow: /\n\nUser-agent: PerplexityBot\nAllow: /\n", "PerplexityBot", "/", True),  # named group wins
        ("User-agent: perplexitybot\nDisallow: /\n", "PerplexityBot", "/", False),                            # case-insensitive
        ("User-agent: *\nDisallow: /products\n", "Bingbot", "/products/chai", False),
        ("User-agent: *\nDisallow: /products\n", "Bingbot", "/product", True),
        ("User-agent: *\nDisallow: /\nAllow: /products/\n", "Bingbot", "/products/chai", True),               # longest wins
        ("User-agent: *\nDisallow: /a\nAllow: /a\n", "Bingbot", "/a", True),                                  # tie: allow
        ("User-agent: *\nDisallow: /*.pdf$\n", "Bingbot", "/guide.pdf", False),                              # wildcard + anchor
        ("User-agent: *\nDisallow: /*.pdf$\n", "Bingbot", "/guide.pdf?x=1", True),
        ("User-agent: *\nDisallow: /*?\n", "Bingbot", "/p?sort=1", False),
        ("User-agent: GPTBot\nDisallow: /\n", "Claude-SearchBot", "/", True),                                 # other agents unaffected
        ("User-agent: Claude\nDisallow: /\n", "Claude-SearchBot", "/", True),                                 # exact token, not prefix
    ])
    def test_matching(self, robots, agent, path, allowed):
        assert seo.is_allowed(seo.parse_robots(robots), agent, path) is allowed

    def test_same_agent_in_two_groups_is_merged(self):
        g = seo.parse_robots("User-agent: Bingbot\nDisallow: /a\n\nUser-agent: Bingbot\nDisallow: /b\n")
        assert not seo.is_allowed(g, "Bingbot", "/a") and not seo.is_allowed(g, "Bingbot", "/b")


class TestCrawlerAccess:
    def test_blocking_everything_lists_every_answer_crawler(self, policy):
        v = seo.crawler_access("User-agent: *\nDisallow: /\n", policy)
        assert [x.split()[0] for x in v.violations] == ANSWER

    def test_training_only_block_passes(self, policy):
        r = "User-agent: GPTBot\nUser-agent: ClaudeBot\nUser-agent: Google-Extended\nDisallow: /\n"
        assert seo.crawler_access(r, policy)
        t = seo.training_access(r, policy)
        assert t["GPTBot"] is False and t["ClaudeBot"] is False and t["CCBot"] is True

    def test_no_robots_file(self, policy):
        assert seo.crawler_access(None, policy)
        assert all(seo.training_access(None, policy).values())

    def test_crawler_list_comes_from_policy(self, policy):
        policy["ai_seo"]["answer_crawlers"] = ["NewAnswerBot"]
        assert not seo.crawler_access("User-agent: NewAnswerBot\nDisallow: /\n", policy)
        assert seo.crawler_access("User-agent: PerplexityBot\nDisallow: /\n", policy)


WORDS = " ".join(["Stone-ground winter chai masala from Ludhiana, made in small batches."] * 15)
ORG = {"@context": "https://schema.org", "@type": "Organization", "name": "Example Masala", "url": "https://x.in",
       "logo": "https://x.in/l.png", "sameAs": ["https://instagram.com/x"]}


def page(body=f"<main><h1>Winter chai masala</h1><p>{WORDS}</p></main>", head="", ld=(ORG,),
         canonical='<link rel="canonical" href="https://x.in/chai">', title="<title>Chai</title>"):
    blocks = "".join(f'<script type="application/ld+json">{json.dumps(x) if not isinstance(x, str) else x}</script>' for x in ld)
    return f"<!doctype html><html><head>{title}{canonical}{head}{blocks}</head><body>{body}</body></html>"


class TestRawHtml:
    def test_server_rendered_page_passes(self, policy):
        assert seo.raw_html(page(), policy, must_contain=["winter chai masala", "small  batches"])

    def test_js_shell(self, policy):
        v = seo.raw_html(page(body='<div id="root"></div><script>render()</script>'), policy)
        assert "looks like a JavaScript-only page" in v.violations[0]

    def test_text_inside_scripts_and_noscript_does_not_count(self, policy):
        body = f'<div id="root"></div><script>var t="{WORDS}"</script><noscript>{WORDS}</noscript>'
        assert not seo.raw_html(page(body=body), policy, must_contain=["winter chai masala"])

    def test_missing_phrase(self, policy):
        v = seo.raw_html(page(), policy, must_contain=["₹349"])
        assert "not in the raw HTML" in v.violations[0]

    @pytest.mark.parametrize("meta", ['<meta name="robots" content="noindex, follow">', '<meta name="googlebot" content="nosnippet">',
                                      '<meta name="ROBOTS" content="none">'])
    def test_meta_robots(self, meta, policy):
        assert any("meta robots" in x for x in seo.raw_html(page(head=meta), policy).violations)

    def test_index_follow_is_fine(self, policy):
        assert seo.raw_html(page(head='<meta name="robots" content="index, follow">'), policy)

    @pytest.mark.parametrize("canonical,msg", [("", "no canonical link"), ('<link rel="canonical" href="/chai">', "not absolute")])
    def test_canonical(self, canonical, msg, policy):
        assert any(msg in x for x in seo.raw_html(page(canonical=canonical), policy).violations)

    def test_canonical_rule_can_be_off(self, policy):
        policy["ai_seo"]["require_canonical"] = False
        assert seo.raw_html(page(canonical=""), policy)

    def test_title_required(self, policy):
        assert "no <title>" in seo.raw_html(page(title=""), policy).violations

    def test_entities_decoded(self, policy):
        assert seo.raw_html(page(body=f"<p>{WORDS} Chai &amp; masala</p>"), policy, must_contain=["chai & masala"])

    def test_visible_text(self):
        assert seo.visible_text("<p>a <b>b</b></p><script>x</script><style>y</style>") == "a b"


class TestSchema:
    def test_organization_passes(self, policy):
        assert seo.schema(page(), policy)

    def test_missing_type(self, policy):
        assert seo.schema(page(ld=()), policy).violations == ["no Organization schema (JSON-LD)"]

    def test_graph_and_nested_nodes(self, policy):
        graph = {"@context": "https://schema.org", "@graph": [ORG, {"@type": "WebPage", "about": {
            "@type": "Product", "name": "Chai masala", "brand": "Example Masala", "offers": {"@type": "Offer", "price": "349"},
            "image": "https://x.in/c.png"}}]}
        assert seo.schema(page(ld=(graph,)), policy, required=["Organization", "Product"])

    def test_type_lists_and_full_urls(self, policy):
        org = dict(ORG, **{"@type": ["https://schema.org/Organization", "Brand"]})
        assert seo.schema(page(ld=(org,)), policy)

    @pytest.mark.parametrize("drop,msg", [("sameAs", "'sameAs'"), ("logo", "'logo' or 'image'"), ("url", "'url'")])
    def test_required_fields(self, drop, msg, policy):
        org = {k: v for k, v in ORG.items() if k != drop}
        v = seo.schema(page(ld=(org,)), policy)
        assert any(msg in x for x in v.violations), v.violations

    def test_empty_values_count_as_missing(self, policy):
        assert not seo.schema(page(ld=(dict(ORG, sameAs=[]),)), policy)

    def test_alternative_field_satisfies(self, policy):
        org = {k: v for k, v in ORG.items() if k != "logo"} | {"image": "https://x.in/i.png"}
        assert seo.schema(page(ld=(org,)), policy)

    def test_invalid_json_reported(self, policy):
        v = seo.schema(page(ld=('{"@type": "Organization",}',)), policy)
        assert any("not valid JSON" in x for x in v.violations)

    def test_no_requirements(self, policy):
        assert seo.schema(page(ld=()), policy, required=[])

    def test_unknown_type_needs_no_fields(self, policy):
        assert seo.schema(page(ld=({"@type": "Recipe"},)), policy, required=["Recipe"])


class TestEntity:
    CANON = {"name": "Example Masala", "description": "Stone-ground spice blends from Ludhiana, made in small batches",
             "aliases": ["ExampleMasala", "Example Masala Co"]}

    def test_consistent(self, policy):
        profiles = {"website": {"name": "Example Masala", "description": "Stone-ground spice blends from Ludhiana, made in small batches."},
                    "instagram": {"name": "examplemasala", "description": "small batches of stone-ground spice blends from Ludhiana"}}
        assert seo.entity_consistency(profiles, self.CANON, policy)

    def test_alias_and_punctuation(self, policy):
        p = {"x": {"name": "Example Masala Co.", "description": self.CANON["description"]}}
        assert seo.entity_consistency(p, self.CANON, policy)

    def test_wrong_name(self, policy):
        v = seo.entity_consistency({"linkedin": {"name": "Example Foods", "description": self.CANON["description"]}}, self.CANON, policy)
        assert v.violations == ["linkedin: name 'Example Foods' differs from 'Example Masala'"]

    def test_off_message_and_missing_descriptions(self, policy):
        v = seo.entity_consistency({"a": {"name": "Example Masala", "description": "Online grocery for everyone"},
                                    "b": {"name": "Example Masala"}}, self.CANON, policy)
        assert "0% overlap" in v.violations[0] and v.violations[1] == "b: no description"


def test_check_page_combines(policy):
    v = seo.check_page(page(body="<div id=root></div>", ld=()), policy, robots_txt="User-agent: *\nDisallow: /\n")
    joined = " ".join(v.violations)
    assert "OAI-SearchBot" in joined and "JavaScript" in joined and "Organization" in joined
    assert seo.check_page(page(), policy)
