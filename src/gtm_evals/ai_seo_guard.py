"""AI SEO: the technical checks Clyve can actually promise (ContentOS E1 and E2).

Content can't be cited if AI search can't reach it, read it, or tell who it's about. Each check
takes text you already fetched (this module never touches the network):

    crawler_access(robots_txt, policy, path="/")       AI search and answer crawlers allowed?
    raw_html(html, policy, must_contain=[...])          readable without JavaScript? not noindex?
    schema(html, policy, required=["Organization"])     JSON-LD present, valid, required fields filled?
    entity_consistency(profiles, canonical, policy)     one name and one description everywhere?
    check_page(...)                                     all of the above for one page, combined

Search/answer crawlers (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, …)
must be allowed: blocking them removes the brand from AI answers. Training crawlers (GPTBot,
ClaudeBot, Google-Extended, …) are the client's choice: reported, never failed.
Crawler names change; the lists live in the policy (ai_seo.*) so they can be updated without code.
"""
from __future__ import annotations

import html as _html
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
        return Verdict.from_violations("ai_seo_guard", [])   # no robots.txt = everything allowed
    groups = parse_robots(robots_txt)
    v = [f"{bot} is blocked from {path} — the brand drops out of the answers it powers"
         for bot in cfg["answer_crawlers"] if not is_allowed(groups, bot, path)]
    return Verdict.from_violations("ai_seo_guard", v)


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
                v.append(f"{t} schema is missing '{field.replace('|', "' or '")}'")
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
    return Verdict.from_violations("ai_seo_guard", v)
