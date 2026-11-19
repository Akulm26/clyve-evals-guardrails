"""AI SEO: the technical checks Clyve can actually promise (ContentOS E1 and E2).

Content can't be cited if AI search can't reach it, read it, or tell who it's about. Each check
takes text you already fetched (this module never touches the network):

    crawler_access(robots_txt, policy, path="/")       AI search and answer crawlers allowed?
    raw_html(html, policy, must_contain=[...])          readable without JavaScript? not noindex?
    schema(html, policy, required=["Organization"])     JSON-LD present, valid, required fields filled?
    entity_consistency(profiles, canonical, policy)     one name and one description everywhere?
    check_page(...)                                     all of the above for one page, combined

Search/answer crawlers (OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot, Bingbot) must be
allowed: blocking them removes the brand from AI answers. User-triggered fetchers (ChatGPT-User,
Claude-User, Perplexity-User, Google-Agent) may ignore robots.txt, so blocking them is a note: test the
firewall. Training crawlers (GPTBot, ClaudeBot, …) are the client's choice: reported, never failed —
except that Google-Extended also controls Gemini grounding, which is noted.
Crawler names change; the lists live in the policy (ai_seo.*) so they can be updated without code.
"""
from __future__ import annotations

import html as _html
import itertools
import json
import re
from html.parser import HTMLParser

from .core import Verdict

# ---------------------------------------------------------------- robots.txt (RFC 9309)

def parse_robots(text: str) -> list[dict]:
    """Groups of {"agents": [lowercased tokens], "rules": [(allow: bool, pattern)]}."""
    groups: list[dict] = []
    cur: dict | None = None
    last_was_agent = False
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, val = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if cur is None or not last_was_agent:
                cur = {"agents": [], "rules": []}
                groups.append(cur)
            cur["agents"].append(val.lower())
            last_was_agent = True
        elif key in ("allow", "disallow") and cur is not None:
            last_was_agent = False
            if val or key == "allow":
                cur["rules"].append((key == "allow", val))
            # an empty Disallow means "allow everything": no rule needed
        else:
            last_was_agent = False   # sitemap, crawl-delay, …: a later user-agent starts a new group
    return groups


def _rule_matches(pattern: str, path: str) -> bool:
    if pattern == "":
        return True
    anchored = pattern.endswith("$")
    body = re.escape(pattern[:-1] if anchored else pattern).replace(r"\*", ".*")
    return re.match(body + ("$" if anchored else ""), path) is not None


def is_allowed(groups: list[dict], agent: str, path: str = "/") -> bool:
    """RFC 9309: the group naming this agent wins (else `*`); longest matching rule wins; Allow wins ties."""
    a = agent.lower()
    named = [g for g in groups if a in g["agents"]]
    chosen = named or [g for g in groups if "*" in g["agents"]]
    rules = [r for g in chosen for r in g["rules"]]
    best: tuple[int, bool] | None = None
    for allow, pat in rules:
        if _rule_matches(pat, path):
            key = (len(pat), allow)
            if best is None or key > best:
                best = key
    return True if best is None else best[1]


def crawler_access(robots_txt: str | None, policy: dict, path: str = "/") -> Verdict:
    cfg = policy["ai_seo"]
    if robots_txt is None:
        return Verdict.from_violations("ai_seo_guard", [])   # no robots.txt = everything allowed (a firewall can still block)
    groups = parse_robots(robots_txt)
    v = [f"{bot} is blocked from {path} — the brand drops out of the answers it powers"
         for bot in cfg["answer_crawlers"] if not is_allowed(groups, bot, path)]
    notes = [f"{bot} is blocked in robots.txt, but it fetches on a user's request and may ignore robots.txt: "
             f"test access through the firewall/CDN instead"
             for bot in cfg.get("user_triggered_fetchers", []) if not is_allowed(groups, bot, path)]
    notes += [f"{bot} is blocked: it is a training token but also affects visibility (Google-Extended: Gemini grounding)"
              for bot in cfg.get("visibility_relevant_training", []) if not is_allowed(groups, bot, path)]
    return Verdict.from_violations("ai_seo_guard", v, notes=notes)


def training_access(robots_txt: str | None, policy: dict, path: str = "/") -> dict[str, bool]:
    """Report only: which training crawlers may read `path`. The client decides; nothing fails."""
    groups = parse_robots(robots_txt or "")
    return {bot: is_allowed(groups, bot, path) for bot in policy["ai_seo"]["training_crawlers"]}


# ---------------------------------------------------------------- raw HTML (no JavaScript)

class _Page(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.skip = 0
        self.meta: dict[str, str] = {}
        self.links: list[dict] = []
        self.jsonld: list[str] = []
        self.scripts = 0
        self._ld = False
        self._title = False
        self.title = ""
        self.headings: list[int] = []       # heading levels in document order
        self.images: list[dict] = []
        self.props: dict[str, str] = {}     # <meta property="og:…">

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script":
            self.scripts += 1
            if a.get("type", "").lower() == "application/ld+json":
                self._ld = True
                self.jsonld.append("")
        if tag in self.SKIP:
            self.skip += 1
        if tag == "meta" and a.get("name"):
            self.meta[a["name"].lower()] = a.get("content", "")
        if tag == "meta" and a.get("property"):
            self.props[a["property"].lower()] = a.get("content", "")
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "img":
            self.images.append(a)
        if tag == "link":
            self.links.append(a)
        if tag == "title":
            self._title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "script":
            self._ld = False
        if tag == "title":
            self._title = False

    def handle_data(self, data):
        if self._ld:
            self.jsonld[-1] += data
        elif self._title:
            self.title += data
        elif not self.skip:
            self.text.append(data)


def _page(html: str) -> _Page:
    p = _Page()
    p.feed(html or "")
    p.close()
    return p


def visible_text(html: str) -> str:
    return re.sub(r"\s+", " ", " ".join(_page(html).text)).strip()


def raw_html(html: str, policy: dict, must_contain: list[str] | None = None) -> Verdict:
    """What a crawler that doesn't run JavaScript sees. Key facts must be in the HTML itself."""
    cfg = policy["ai_seo"]
    p = _page(html)
    text = re.sub(r"\s+", " ", " ".join(p.text)).strip()
    low = text.lower()
    v: list[str] = []
    words = len(text.split())
    if words < cfg["min_words_without_js"]:
        hint = " (looks like a JavaScript-only page)" if p.scripts else ""
        v.append(f"only {words} words readable without JavaScript, need ≥ {cfg['min_words_without_js']}{hint}")
    for phrase in must_contain or []:
        if re.sub(r"\s+", " ", phrase).strip().lower() not in low:
            v.append(f"not in the raw HTML (only shows after JavaScript, or missing): '{phrase}'")
    robots = " ".join(p.meta.get(k, "") for k in ("robots", "googlebot")).lower()
    for directive in ("noindex", "nosnippet", "none"):
        if re.search(rf"\b{directive}\b", robots):
            v.append(f"meta robots '{directive}' keeps this page out of search and AI answers")
    canon = [lk.get("href", "") for lk in p.links if "canonical" in lk.get("rel", "").lower().split()]
    if cfg["require_canonical"]:
        if not canon:
            v.append("no canonical link")
        elif not re.match(r"https?://", canon[0]):
            v.append(f"canonical link is not absolute: '{canon[0]}'")
    if not p.title.strip():
        v.append("no <title>")
    return Verdict.from_violations("ai_seo_guard", v)


# ---------------------------------------------------------------- schema.org JSON-LD

def _types(node) -> list[str]:
    t = node.get("@type", [])
    return [x.split("/")[-1] for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)]


def jsonld_nodes(html: str) -> tuple[list[dict], list[str]]:
    """Every JSON-LD object on the page (flattening @graph and lists), plus parse errors."""
    nodes: list[dict] = []
    errors: list[str] = []

    def walk(x):
        if isinstance(x, list):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            if "@type" in x:
                nodes.append(x)
            for k, val in x.items():
                if k != "@context" and isinstance(val, (dict, list)):
                    walk(val)

    for i, block in enumerate(_page(html).jsonld, 1):
        try:
            walk(json.loads(_html.unescape(block)))
        except json.JSONDecodeError as e:
            errors.append(f"JSON-LD block {i} is not valid JSON ({e.msg} at line {e.lineno})")
    return nodes, errors


def schema(html: str, policy: dict, required: list[str] | None = None) -> Verdict:
    cfg = policy["ai_seo"]
    nodes, errors = jsonld_nodes(html)
    v = list(errors)
    need = required if required is not None else cfg["required_schema_types"]
    for t in need:
        found = [n for n in nodes if t in _types(n)]
        if not found:
            v.append(f"no {t} schema (JSON-LD)")
            continue
        for field in cfg["schema_required_fields"].get(t, []):
            alts = field.split("|")
            if not any(any(n.get(a) not in (None, "", [], {}) for a in alts) for n in found):
                shown = "' or '".join(alts)
                v.append(f"{t} schema is missing '{shown}'")
    return Verdict.from_violations("ai_seo_guard", v)


# ---------------------------------------------------------------- entity consistency

def _tok(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def entity_consistency(profiles: dict[str, dict], canonical: dict, policy: dict) -> Verdict:
    """profiles = {"website": {"name": ..., "description": ...}, "linkedin": {...}, "instagram": {...}, ...}
    canonical = {"name": "Brand", "description": "the canonical one-liner", "aliases": [...]}

    Every channel must use the canonical name (or a listed alias) and a description that
    says what the canonical one-liner says, so AI assistants meet one consistent entity.
    """
    cfg = policy["ai_seo"]
    names = {_norm_name(canonical.get("name", ""))} | {_norm_name(a) for a in canonical.get("aliases", [])}
    want = _tok(canonical.get("description", ""))
    v: list[str] = []
    for channel, prof in profiles.items():
        if _norm_name(prof.get("name", "")) not in names:
            v.append(f"{channel}: name '{prof.get('name', '')}' differs from '{canonical.get('name')}'")
        desc = prof.get("description", "")
        if not desc:
            v.append(f"{channel}: no description")
            continue
        overlap = len(want & _tok(desc)) / len(want) if want else 1.0
        if overlap < cfg["description_min_overlap"]:
            v.append(f"{channel}: description doesn't match the canonical one-liner "
                     f"({overlap:.0%} overlap, need ≥ {cfg['description_min_overlap']:.0%})")
    return Verdict.from_violations("ai_seo_guard", v)


# ---------------------------------------------------------------- one page, all checks

def check_page(html: str, policy: dict, robots_txt: str | None = None, path: str = "/",
               must_contain: list[str] | None = None, required_schema: list[str] | None = None) -> Verdict:
    parts = [raw_html(html, policy, must_contain), schema(html, policy, required_schema)]
    if robots_txt is not None:
        parts.insert(0, crawler_access(robots_txt, policy, path))
    v = [x for p in parts for x in p.violations]
    return Verdict.from_violations("ai_seo_guard", v, notes=[x for p in parts for x in p.notes])


# ---------------------------------------------------------------- the reality test: fetched as each crawler

def fetch_results(results: list[dict], policy: dict) -> Verdict:
    """results: what each answer crawler got when it fetched a key page (saved by `gtm-evals seo --fetch-plan`,
    or from the CDN's bot logs): [{"agent": "PerplexityBot", "status": 200, "body": "…"}].

    A clean robots.txt means nothing if the firewall answers 403 or a challenge page."""
    cfg = policy["ai_seo"]
    by = {r.get("agent"): r for r in results or []}
    v, notes = [], []
    for bot in cfg["answer_crawlers"]:
        r = by.get(bot)
        if r is None:
            notes.append(f"no fetch result for {bot}")
            continue
        status, body = int(r.get("status") or 0), (r.get("body") or "")[:20000].lower()
        if status != 200:
            v.append(f"{bot} got HTTP {status}" + (" (blocked by the firewall or CDN)" if status in (401, 403, 429, 503) else ""))
        elif any(m in body for m in cfg["challenge_markers"]):
            v.append(f"{bot} got a challenge page, not the content")
    notes.append("a user-agent test from your machine doesn't come from the crawler's IP: CDNs verify bots by IP, "
                 "so confirm in the CDN's bot logs too")
    return Verdict.from_violations("ai_seo_guard", v, notes=notes)


def fetch_plan(url: str, policy: dict) -> str:
    """curl commands that save one result per answer crawler, ready for fetch_results()."""
    lines = ["# Run from a server, not your laptop if you can. Then: gtm-evals seo --fetch-results fetch.json",
             "echo '[' > fetch.json"]
    bots = policy["ai_seo"]["answer_crawlers"]
    for i, bot in enumerate(bots):
        ua = policy["ai_seo"]["crawler_user_agents"].get(bot, bot)
        sep = "," if i < len(bots) - 1 else ""
        lines.append(f"curl -s -o /tmp/body.html -w '%{{http_code}}' -A '{ua}' '{url}' | "
                     f"python3 -c \"import json,sys;print(json.dumps({{'agent':'{bot}','status':int(sys.stdin.read()),"
                     f"'body':open('/tmp/body.html',errors='ignore').read()[:20000]}})+'{sep}')\" >> fetch.json")
    lines.append("echo ']' >> fetch.json")
    return "\n".join(lines)


# ---------------------------------------------------------------- site-wide checks (the 80% rule)

def page_checks(html: str, policy: dict) -> dict[str, bool]:
    """Per-page hygiene that answer engines lean on. True = passes."""
    p = _page(html)
    h = p.headings
    return {
        "readable_without_js": bool(raw_html(html, policy)),
        "meta_description": bool(p.meta.get("description", "").strip()),
        "single_h1": h.count(1) == 1,
        "open_graph": bool(p.props.get("og:title") and p.props.get("og:description")),
        "image_alt": all("alt" in img for img in p.images),
        "heading_order": all(b - a <= 1 for a, b in itertools.pairwise(h)),
    }


def check_site(pages: dict[str, str], policy: dict, site_files: dict[str, str] | None = None) -> Verdict:
    """pages: {path: saved HTML}. A per-page check passes when ≥ site_pass_share of pages pass it.
    site_files: {"llms.txt": text, "feed.xml": text, ...} for the site-level checks."""
    cfg = policy["ai_seo"]
    need = cfg["site_pass_share"]
    req = cfg["require"]
    v, notes = [], []
    results = {path: page_checks(html, policy) for path, html in (pages or {}).items()}
    if not results:
        return Verdict.from_violations("ai_seo_guard", ["no pages given"])
    for check in [c for c in req if c in next(iter(results.values()))]:
        bad = sorted(p for p, r in results.items() if not r[check])
        share = 1 - len(bad) / len(results)
        if share < need:
            v.append(f"{check.replace('_', ' ')}: {share:.0%} of pages pass, need {need:.0%} "
                     f"(e.g. {', '.join(bad[:3])})")
        elif bad:
            notes.append(f"{check.replace('_', ' ')}: {len(bad)} page(s) fail ({', '.join(bad[:3])})")
    files = {k.lower().lstrip("/"): t for k, t in (site_files or {}).items()}
    if "llms_txt" in req and not files.get("llms.txt", "").strip():
        v.append("no /llms.txt")
    if "feed" in req:
        has_link = any(re.search(r'type=["\']application/(rss|atom)\+xml', h, re.IGNORECASE) for h in pages.values())
        if not has_link and not any(k.endswith((".xml", ".rss", ".atom")) and "<" in t for k, t in files.items()):
            v.append("no RSS or Atom feed (linked from pages or saved as a site file)")
    return Verdict.from_violations("ai_seo_guard", v, notes=notes)
