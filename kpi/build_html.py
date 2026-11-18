"""Render the KPI page (Clyve Design System v1.0). python -m kpi.build_html > out.html"""
from html import escape as e

from . import ALL, LAYERS, OPEN_ITEMS

DATE = "18 Nov 2026"
TAG = {"PUBLIC": "t-mute", "RUNS": "t-ox", "FOUNDER": "t-ink", "CLIENT": "t-ink", "PLATFORM": "t-mute", "CLYVE": "t-mute"}
REV = {"direct": "rev-direct", "indirect": "rev-indirect", "weak": "rev-weak", "none": "rev-none"}
ROLE = {"headline": "role-headline", "supporting": "role-supporting", "internal": "role-internal"}
STAT = {"locked": "stat-locked", "proposed": "stat-proposed"}

CSS = r"""/* Clyve Design System v1.0 tokens. Hex from the spec; oklch equivalents in the spec's tokens/colors.css */
:root{
  --bone-50:#F4EFE7;      /* base surface ~60% */
  --ink-900:#240F0F;      /* text + dark surfaces ~25% */
  --oxblood-600:#751F23;  /* brand + action ~10% */
  --chartreuse-400:#CADC7F; /* "next move" only ~5% */
  --clay-500:#A17D6D;     /* muted: noise, inactive; text only on Ink (4.9:1) */
  --bone-200:#DCD2CB;     /* hairlines only */
  /* Muted text tints on Bone. Derived from the spec's stated contrast (Ink-500 7.5:1, Ink-400 4.9:1); replace with tokens/colors.css values. */
  --ink-500:#5F4645;
  --ink-400:#7C6161;
  --serif:'Source Serif 4',Georgia,serif;
  --sans:'Figtree',sans-serif;
  --mono:'Red Hat Mono',ui-monospace,monospace;
  --ease:cubic-bezier(0.2,0.7,0.2,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:96px}
body{margin:0;background:var(--bone-50);color:var(--ink-900);font-family:var(--sans);font-size:16px;line-height:1.6;font-weight:400;-webkit-font-smoothing:antialiased}
::selection{background:var(--bone-200);color:var(--ink-900)}
a{color:var(--oxblood-600);text-decoration:none;transition:color 180ms var(--ease)}
a:hover{color:var(--ink-900);text-decoration:underline}
.wrap{max-width:1200px;margin:0 auto;padding:0 48px}
.mono{font-family:var(--mono)}

/* type */
h1,h2,h3{margin:0;color:var(--ink-900)}
h1{font-family:var(--serif);font-weight:400;font-size:56px;line-height:1.05;letter-spacing:-0.03em}
h1 em{font-style:italic;font-weight:500}
h2{font-family:var(--serif);font-weight:400;font-size:32px;line-height:1.15;letter-spacing:-0.02em}
h3{font-family:var(--serif);font-weight:600;font-size:22px;line-height:1.25;letter-spacing:-0.01em}
.m-kick{font-family:var(--mono);font-weight:500;font-size:12px;line-height:1.3;letter-spacing:0.1em;color:var(--ink-400);text-transform:uppercase;margin-bottom:4px}
.lead{font-size:19px;line-height:1.55;color:var(--ink-500);max-width:640px;margin:0 0 32px}
.lbl{font-family:var(--mono);font-weight:500;font-size:12px;line-height:1.3;letter-spacing:0.1em;text-transform:uppercase;color:var(--ink-500);margin:24px 0 8px}
.lbl.mt{margin-top:32px}
.lbl .ill{margin-left:12px;color:var(--oxblood-600)}
.eyebrow{display:flex;align-items:center;gap:12px;font-family:var(--mono);font-weight:500;font-size:12px;line-height:1.3;letter-spacing:0.1em;text-transform:uppercase}
.eyebrow::before{content:"";display:block;width:24px;height:4px;background:currentColor}

/* top bar */
.topbar{position:sticky;top:0;z-index:10;background:var(--bone-50);border-bottom:1px solid var(--bone-200)}
.topbar-in{display:flex;align-items:center;gap:32px;height:64px}
.lockup{display:flex;align-items:center;gap:40px;color:var(--ink-900);flex:none}
.lockup .wm{height:16px;width:auto;display:block}
.nav{display:flex;gap:24px;overflow-x:auto;white-space:nowrap;flex:1}
.nav a{font-family:var(--mono);font-weight:500;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:var(--ink-500)}
.nav a:hover{color:var(--oxblood-600);text-decoration:none}
.search{font-family:var(--mono);font-weight:400;font-size:12px;padding:8px 12px;border:1px solid var(--bone-200);border-radius:6px;background:var(--bone-50);color:var(--ink-900);width:264px;transition:border-color 180ms var(--ease)}
.search::placeholder{color:var(--ink-400)}
.search:focus{outline:3px solid rgba(117,31,35,0.15);border-color:var(--oxblood-600)}

/* hero: open dark */
.hero{position:relative;background:var(--ink-900);color:var(--bone-50);overflow:hidden}
.hero .wrap{position:relative;padding-top:96px;padding-bottom:96px}
.hero .eyebrow{color:var(--bone-50);margin-bottom:24px}
.hero h1{color:var(--bone-50);max-width:640px;margin-bottom:24px}
.hero-lead{font-size:19px;line-height:1.55;color:var(--bone-50);max-width:640px;margin:0 0 48px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,160px));gap:32px;margin-bottom:48px;position:relative;z-index:1}
.stat .n{font-family:var(--mono);font-weight:500;font-size:40px;line-height:1;letter-spacing:-0.02em;color:var(--bone-50)}
.stat .l{font-family:var(--mono);font-weight:500;font-size:12px;line-height:1.3;letter-spacing:0.1em;text-transform:uppercase;color:var(--clay-500);margin-top:8px}
.status{display:flex;align-items:center;gap:16px;position:relative;z-index:1}
.status .meta{font-family:var(--mono);font-weight:400;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:var(--clay-500)}
.hero-in{position:relative;z-index:1}
.supergraphic{position:absolute;right:-32px;bottom:-30%;width:720px;height:720px;z-index:0}
.stamp-chip{display:inline-block;font-family:var(--mono);font-weight:500;font-size:12px;line-height:1.4;letter-spacing:0.1em;text-transform:uppercase;border:1px solid var(--bone-50);color:var(--bone-50);border-radius:3px;padding:4px 8px}

/* sections: argue on Bone */
section{margin-top:128px}
.first{margin-top:96px}
.contour{margin-bottom:32px}
.contour i{display:block}
.contour i:nth-child(1){height:1px;background:var(--bone-200);margin-bottom:16px}
.contour i:nth-child(2){height:1px;background:var(--clay-500);margin-bottom:8px}
.contour i:nth-child(3){height:4px;background:var(--ink-900)}
.sec-head{display:flex;align-items:baseline;gap:16px;margin-bottom:16px}
.sec-num{font-family:var(--mono);font-weight:500;font-size:12px;letter-spacing:0.1em;color:var(--oxblood-600)}

.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:16px}
.part{margin-top:128px}
.part .eyebrow{color:var(--oxblood-600);margin-bottom:16px}
.part-h{font-family:var(--serif);font-weight:400;font-size:44px;line-height:1.08;letter-spacing:-0.025em;margin-bottom:16px;max-width:780px}
.part + .layer{margin-top:64px}
.panel{border:1px solid var(--bone-200);border-radius:10px;padding:32px}
.panel .lbl{margin-top:0}
ul.plain{list-style:none;padding:0;margin:0;font-size:14px;line-height:1.5}
ul.plain li{padding:8px 0;border-top:1px solid var(--bone-200)}
ul.plain li:first-child{border-top:0}
.box{margin-top:16px;border:1px solid var(--bone-200);border-radius:6px;padding:24px;font-size:14px;line-height:1.5}
.box .bl{display:block;font-family:var(--mono);font-weight:500;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:var(--oxblood-600);margin-bottom:8px}
.box p{margin:0;max-width:640px}

/* tables */
.scroll{overflow-x:auto;border:1px solid var(--bone-200);border-radius:6px}
table.grid{width:100%;border-collapse:collapse;font-size:14px;line-height:1.5}
table.grid th{font-family:var(--mono);font-weight:500;font-size:12px;line-height:1.3;letter-spacing:0.1em;text-transform:uppercase;color:var(--ink-500);text-align:left;padding:12px 16px;border-bottom:1px solid var(--ink-900);white-space:nowrap}
table.grid td{padding:12px 16px;border-top:1px solid var(--bone-200);vertical-align:top}
table.grid tbody tr:first-child td{border-top:0}
td.in-name{font-weight:600;min-width:160px}
table.cheat td.fcell{font-size:12px;min-width:320px}

/* chips */
.tag,.chip{display:inline-block;font-family:var(--mono);font-weight:500;font-size:12px;line-height:1.4;letter-spacing:0.08em;text-transform:uppercase;border:1px solid;border-radius:3px;padding:2px 8px;white-space:nowrap;margin:2px 4px 2px 0}
.t-ink{color:var(--ink-900);border-color:var(--ink-900)}
.t-mute{color:var(--ink-400);border-color:var(--bone-200)}
.t-ox{color:var(--oxblood-600);border-color:var(--oxblood-600)}
.rev-direct{background:var(--oxblood-600);border-color:var(--oxblood-600);color:var(--bone-50)}
.rev-indirect{color:var(--ink-900);border-color:var(--ink-900)}
.rev-weak,.rev-none,.role-internal,.stat-locked{color:var(--ink-400);border-color:var(--bone-200)}
.role-headline{background:var(--ink-900);border-color:var(--ink-900);color:var(--bone-50)}
.role-supporting{color:var(--ink-500);border-color:var(--ink-500)}
.stat-proposed{color:var(--oxblood-600);border-color:var(--oxblood-600)}

/* metric cards */
.metric{border:1px solid var(--bone-200);border-radius:6px;margin:0 0 32px}
.m-head{display:grid;grid-template-columns:64px minmax(0,1fr) auto;gap:16px;align-items:start;padding:24px 32px;border-bottom:1px solid var(--bone-200)}
.m-id{font-family:var(--mono);font-weight:500;font-size:20px;line-height:1.3;letter-spacing:-0.02em;color:var(--oxblood-600)}
.m-q{margin:8px 0 0;color:var(--ink-500);max-width:640px;font-size:16px;line-height:1.6}
.m-chips{display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end;max-width:304px}
.m-body{padding:8px 32px 32px}
.formula{background:var(--ink-900);color:var(--bone-50);border-radius:6px;padding:24px}
.f-main{font-family:var(--mono);font-weight:500;font-size:14px;line-height:1.6}
.f-sub{font-family:var(--mono);font-weight:400;font-size:12px;line-height:1.6;color:var(--clay-500);margin-top:12px;padding-top:12px;border-top:1px solid var(--ink-500)}
.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:32px}
ol.steps{margin:0;padding-left:24px;font-size:14px;line-height:1.5}
ol.steps li{padding:4px 0}
.ex{margin:0;font-size:14px;line-height:1.5}
.stamp{margin:0;font-size:14px;line-height:1.5}
.stamp .note{font-family:var(--mono);font-weight:400;font-size:12px;color:var(--ink-500);margin-left:4px}
.watch{margin-top:24px;border:1px solid var(--bone-200);border-radius:6px;padding:16px;font-size:14px;line-height:1.5}
.watch .wl{font-family:var(--mono);font-weight:500;font-size:12px;letter-spacing:0.1em;color:var(--oxblood-600);margin-right:12px}

/* close on the next move */
.close{background:var(--ink-900);color:var(--bone-50);margin-top:128px}
.close .wrap{padding-top:96px;padding-bottom:48px}
.close .eyebrow{color:var(--bone-50);margin-bottom:24px}
.close h2{color:var(--bone-50);max-width:780px;font-size:44px;line-height:1.08;letter-spacing:-0.025em;margin-bottom:24px}
.close p{max-width:640px;margin:0 0 96px;color:var(--bone-50)}
.endorsed{display:flex;align-items:center;gap:24px;padding-top:32px;border-top:1px solid var(--ink-500);color:var(--bone-50)}
.endorsed .cos{height:22px;width:auto;display:block}
.endorsed .div{width:1px;height:32px;background:var(--clay-500)}
.endorsed .cl{display:flex;align-items:center;gap:16px}
.endorsed .cl .wm{height:16px;width:auto;display:block}
.endorsed .meta{margin-left:auto;font-family:var(--mono);font-weight:400;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:var(--clay-500)}
.hidden{display:none !important}
#nomatch{display:none;font-family:var(--mono);font-weight:500;font-size:12px;letter-spacing:0.1em;color:var(--ink-500);padding:16px 0}

@media (max-width:900px){
  .wrap{padding:0 24px}
  h1{font-size:44px;line-height:1.08;letter-spacing:-0.025em}
  .hero .wrap{padding-top:64px;padding-bottom:64px}
  .supergraphic{display:none}
  .stats{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cards,.two{grid-template-columns:1fr}
  .part{margin-top:64px}
  .part-h{font-size:32px;line-height:1.15;letter-spacing:-0.02em}
  .m-head{grid-template-columns:1fr;gap:12px;padding:24px}
  .m-chips{justify-content:flex-start;max-width:none}
  .m-body{padding:8px 24px 24px}
  .search{width:144px}
  .lockup{gap:16px}
  section{margin-top:64px}
  .close{margin-top:64px}
  .close h2{font-size:32px;line-height:1.15}
  .endorsed{flex-wrap:wrap}
  .endorsed .meta{margin-left:0;width:100%}
}
@media print{
  .topbar{display:none}
  .metric{break-inside:avoid}
  section{margin-top:48px}
}"""

WM = '<svg class="wm" viewBox="41 -734 2240 978" role="img" aria-label="Clyve" xmlns="http://www.w3.org/2000/svg"><path d="M384 17C462 17 531 -1 589 -33L593 -182H525L502 -60C467 -44 432 -37 398 -37C276 -37 181 -132 181 -332C181 -531 283 -628 404 -628C433 -628 462 -621 493 -605L516 -482H585L581 -632C517 -668 451 -681 386 -681C195 -681 41 -550 41 -328C41 -112 186 17 384 17Z M628 0H888V-41L819 -54C818 -106 817 -158 817 -210V-583L821 -725L806 -734L625 -689V-650L698 -640V-210C698 -158 697 -106 696 -54L628 -41Z M1200 -439 1276 -427 1224 -280 1167 -120 1054 -428 1133 -439V-479H872V-439L923 -431L1113 32L1111 38C1093 89 1067 135 1031 169L1025 161C998 128 972 120 946 120C911 120 879 137 871 173C873 214 917 244 969 244C1056 244 1107 172 1165 17L1336 -428L1392 -439V-479H1200Z M1654 -437 1727 -424 1627 -135 1518 -425 1594 -437V-479H1333V-437L1384 -428L1565 4H1624L1788 -425L1844 -437V-479H1654Z M2076 -444C2127 -444 2162 -410 2162 -341C2162 -305 2150 -284 2098 -284H1963C1971 -403 2024 -444 2076 -444ZM2081 14C2184 14 2239 -29 2281 -102L2254 -124C2218 -83 2176 -65 2119 -65C2030 -65 1967 -123 1962 -237H2270C2274 -252 2276 -270 2276 -292C2276 -413 2195 -493 2076 -493C1943 -493 1837 -393 1837 -234C1837 -76 1935 14 2081 14Z" fill="currentColor"/></svg>'

COS = '<svg class="cos" viewBox="41 -681 4477 698" role="img" aria-label="ContentOS" xmlns="http://www.w3.org/2000/svg"><path d="M384 17C462 17 531 -1 589 -33L593 -182H525L502 -60C467 -44 432 -37 398 -37C276 -37 181 -132 181 -332C181 -531 283 -628 404 -628C433 -628 462 -621 493 -605L516 -482H585L581 -632C517 -668 451 -681 386 -681C195 -681 41 -550 41 -328C41 -112 186 17 384 17Z M870 14C1004 14 1111 -78 1111 -239C1111 -400 998 -493 870 -493C741 -493 629 -399 629 -239C629 -79 735 14 870 14ZM870 -34C797 -34 759 -100 759 -238C759 -376 797 -444 870 -444C942 -444 982 -376 982 -238C982 -100 942 -34 870 -34Z M1148 0H1395V-41L1335 -53C1334 -103 1334 -167 1334 -210V-359C1374 -393 1411 -409 1447 -409C1497 -409 1517 -383 1517 -304V-210C1517 -165 1517 -103 1516 -54L1452 -41V0H1699V-41L1637 -53C1636 -103 1636 -165 1636 -210V-314C1636 -438 1587 -493 1501 -493C1441 -493 1382 -464 1331 -406L1324 -483L1308 -493L1141 -429V-392L1212 -383C1214 -343 1215 -318 1215 -263V-210C1215 -167 1215 -103 1214 -54L1148 -41Z M1901 14C1963 14 2006 -10 2032 -52L2008 -77C1986 -60 1967 -52 1947 -52C1915 -52 1894 -74 1894 -123V-419H2016V-479H1895L1899 -617H1819L1782 -480L1700 -470V-419H1774V-204C1774 -165 1773 -141 1773 -112C1773 -24 1822 14 1901 14Z M2272 -444C2323 -444 2358 -410 2358 -341C2358 -305 2346 -284 2294 -284H2159C2167 -403 2220 -444 2272 -444ZM2277 14C2380 14 2435 -29 2477 -102L2450 -124C2414 -83 2372 -65 2315 -65C2226 -65 2163 -123 2158 -237H2466C2470 -252 2472 -270 2472 -292C2472 -413 2391 -493 2272 -493C2139 -493 2033 -393 2033 -234C2033 -76 2131 14 2277 14Z M2510 0H2757V-41L2697 -53C2696 -103 2696 -167 2696 -210V-359C2736 -393 2773 -409 2809 -409C2859 -409 2879 -383 2879 -304V-210C2879 -165 2879 -103 2878 -54L2814 -41V0H3061V-41L2999 -53C2998 -103 2998 -165 2998 -210V-314C2998 -438 2949 -493 2863 -493C2803 -493 2744 -464 2693 -406L2686 -483L2670 -493L2503 -429V-392L2574 -383C2576 -343 2577 -318 2577 -263V-210C2577 -167 2577 -103 2576 -54L2510 -41Z M3263 14C3325 14 3368 -10 3394 -52L3370 -77C3348 -60 3329 -52 3309 -52C3277 -52 3256 -74 3256 -123V-419H3378V-479H3257L3261 -617H3181L3144 -480L3062 -470V-419H3136V-204C3136 -165 3135 -141 3135 -112C3135 -24 3184 14 3263 14Z M3711 17C3870 17 4022 -107 4022 -332C4022 -562 3869 -681 3711 -681C3551 -681 3399 -556 3399 -332C3399 -101 3550 17 3711 17ZM3711 -37C3590 -37 3539 -174 3539 -332C3539 -489 3590 -627 3711 -627C3832 -627 3881 -489 3881 -332C3881 -174 3832 -37 3711 -37Z M4270 17C4424 17 4518 -61 4518 -179C4518 -277 4467 -333 4337 -387L4294 -405C4228 -433 4191 -466 4191 -524C4191 -589 4244 -626 4312 -626C4340 -626 4363 -621 4387 -609L4407 -494H4482L4489 -629C4444 -661 4383 -681 4314 -681C4175 -681 4078 -609 4078 -492C4078 -386 4146 -326 4256 -280L4297 -262C4370 -232 4402 -205 4402 -147C4402 -80 4352 -38 4269 -38C4228 -38 4199 -45 4168 -59L4148 -180H4071L4065 -36C4116 -3 4195 17 4270 17Z" fill="currentColor"/></svg>'


def mark(mid, fill, h=32):
    return (f'<svg viewBox="0 0 40 40" width="{h}" height="{h}" role="img" aria-label="Clyve" xmlns="http://www.w3.org/2000/svg">'
            f'<mask id="{mid}"><rect width="40" height="40" fill="#fff"/><path d="M13 20.4 Q22 19.6 30 19 M5 28.4 Q18 27.2 30 26.4" stroke="#000" stroke-width="3.4" fill="none"/></mask>'
            f'<polygon points="2,36 28,10 28,36" fill="{fill}" mask="url(#{mid})"/><rect x="31" y="10" width="7" height="3.4" fill="{"var(--oxblood-600)" if mid == "mtop" else "var(--chartreuse-400)"}"/></svg>')


def tags(src):
    return " ".join(f'<span class="tag {TAG[t]}">{t}</span>' for t in src.split())


def stamp_html(label, note):
    cls = "t-ink" if label in ("OBSERVED", "CAPTURED") else "t-ox" if label.startswith("ASSUMED") else "t-mute"
    n = "" if note is None else f'<span class="note">{e(note)}</span>'
    return f'<p class="stamp"><span class="tag {cls}">{e(label)}</span>{n}</p>'


def card(m):
    rev, role, stat = m.chips.split()
    chips = (f'<span class="chip {REV[rev]}">{rev.upper()}</span><span class="chip {ROLE[role]}">{role.upper()}</span>'
             f'<span class="chip {STAT[stat]}">{stat.upper()}</span>')
    if m.changed:
        chips += f'<span class="chip t-ox">{"NEW" if m.changed == "new" else "UPDATED"} · {DATE.upper()}</span>'
    kick = f'<div class="m-kick">{e(m.kick)}</div>' if m.kick else ""
    subs = "".join(f'<div class="f-sub">{e(s)}</div>' for s in m.subs)
    rows = "".join(f'<tr><td class="in-name">{e(n)}</td><td>{e(w)}</td><td>{tags(s)}</td><td>{e(h)}</td></tr>' for n, w, s, h in m.inputs)
    steps = "".join(f"<li>{e(s)}</li>" for s in m.steps)
    watch = f'<div class="watch"><span class="wl">WATCH OUT</span>{e(m.watch)}</div>' if m.watch else ""
    return f'''
<article class="metric" id="{m.id}" data-layer="{m.layer}" data-src="{m.src}">
  <header class="m-head">
    <div class="m-id">{m.id}</div>
    <div>{kick}<h3>{e(m.title)}</h3><p class="m-q">{e(m.q)}</p></div>
    <div class="m-chips">{chips}</div>
  </header>
  <div class="m-body">
    <div class="lbl">Formula</div>
    <div class="formula"><div class="f-main">{e(m.formula)}</div>{subs}</div>
    <div class="lbl">Inputs and where they come from</div>
    <div class="scroll"><table class="grid"><thead><tr><th>Input</th><th>What it is</th><th>Source</th><th>How to get it</th></tr></thead><tbody>{rows}</tbody></table></div>
    <div class="two">
      <div><div class="lbl">How to collect it</div><ol class="steps">{steps}</ol></div>
      <div><div class="lbl">Worked example<span class="ill">Illustrative numbers</span></div><p class="ex">{e(m.example)}</p>
      <div class="lbl">Stamp</div>{stamp_html(*m.stamp)}</div>
    </div>
    {watch}
  </div>
</article>'''


PARTS = {
    "A": ("parta", "Part A", "ContentOS: what it measures for clients", "Layers 1 to 4. Revenue link means the client's revenue."),
    "B": ("partb", "Part B", "Clyve: the core business", "Layers 5 to 9. Revenue link means Clyve's own revenue. Every metric here is proposed."),
    "C": ("partc", "Part C", "The system: guardrails, evals and send safety", "Layer 10. Whether the numbers, drafts and sends can be trusted at all. Implemented in the open-source clyve-guardrails-evals repo."),
}


def build():
    n_a = sum(1 for m in ALL if m.layer <= 4)
    n_b = sum(1 for m in ALL if 5 <= m.layer <= 9)
    n_c = sum(1 for m in ALL if m.layer == 10)
    n_prop = sum(1 for m in ALL if m.chips.endswith("proposed"))
    nav = "".join(f'<a href="#{a}">{n:02d} {t.split(": ", 1)[1].replace("AI/Search Visibility", "AI visibility").replace("Diagnostic tracks", "Diagnostic").replace("Outcome KPIs", "Outcome").replace("Acquisition engine", "Acquisition").replace("Product line", "Products").replace("Guardrails and evals", "Guardrails")}</a>'
                  for n, a, t, *_ in LAYERS) + '<a href="#open">Open items</a>'
    cheat = "".join(f'<tr data-layer="{m.layer}"><td class="mono"><a href="#{m.id}">{m.id}</a></td><td>{e(m.title)}</td>'
                    f'<td class="mono fcell">{e(m.formula)}</td><td>{tags(m.src)}</td></tr>' for m in ALL)
    body, part_done = [], set()
    for num, anchor, title, lead, ms, part in LAYERS:
        if part not in part_done:
            pid, eb, h, pl = PARTS[part]
            body.append(f'\n<div class="part" id="{pid}"><div class="eyebrow">{eb}</div><h2 class="part-h">{e(h)}</h2><p class="lead">{e(pl)}</p></div>')
            part_done.add(part)
        body.append(f'''
<section class="layer" id="{anchor}">
  <div class="contour" aria-hidden="true"><i></i><i></i><i></i></div>
  <div class="sec-head"><span class="sec-num">{num:02d}</span><h2>{e(title)}</h2></div>
  <p class="lead">{e(lead)}</p>
  {"".join(card(m) for m in ms)}
</section>''')
    opens = "".join(f'<tr><td class="mono">{i}</td><td>{e(a)}</td><td>{e(b)}</td></tr>' for i, (a, b) in enumerate(OPEN_ITEMS, 1))
    runlog = [("run_id", "Unique number for the run", "Assigned by you"), ("date", "Date the run was made", "Automatic"),
              ("platform", "ChatGPT, Perplexity, Gemini (AI Overviews by hand)", "You"), ("prompt_id", "Which frozen prompt", "From the prompt set"),
              ("query_type", "brand, niche, or generic", "From the prompt set"), ("pass_no", "Which repeat pass (1 to K)", "You"),
              ("brand_named", "Y or N: brand name appears in the answer", "Read the answer text"),
              ("brand_cited", "Y or N: brand's domain appears in sources or links", "Read the sources panel"),
              ("rank", "Brand's rank if the answer is a ranked list; else blank", "Read the answer"),
              ("competitors_named", "Every other brand named in the answer", "Read the answer text"),
              ("sources_cited", "Domains shown as sources, one per entry", "Read the sources panel"),
              ("description_correct", "Y or N against the fact list; blank if brand not named", "Compare with the fact list"),
              ("screenshot_id", "Filename of the screenshot", "Capture at collection time")]
    runlog_rows = "".join(f'<tr><td class="mono">{a}</td><td>{e(b)}</td><td>{e(c)}</td></tr>' for a, b, c in runlog)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clyve and ContentOS KPI formulas and data sources | Clyve</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400;1,8..60,500&family=Figtree:wght@400;500;600&family=Red+Hat+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}
</style>
</head>
<body id="top">
<div class="topbar"><div class="wrap topbar-in">
  <a class="lockup" href="#top" aria-label="Clyve">{mark("mtop", "currentColor")}{WM}</a>
  <nav class="nav" aria-label="Sections">{nav}</nav>
  <input id="q" class="search" type="search" placeholder="Filter: mention, GA4, D7, Q1" aria-label="Filter metrics">
</div></div>

<header class="hero">
  <div class="wrap">
    <svg class="supergraphic" viewBox="0 0 40 40" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><mask id="sg"><rect width="40" height="40" fill="#fff"/><path d="M13 20.4 Q22 19.6 30 19 M5 28.4 Q18 27.2 30 26.4 M9 24.4 Q20 23.4 30 22.6 M0 32.4 Q16 30.8 30 29.8 M17 16.6 Q24 16.1 30 15.7 M2 35 Q16 34 30 33.2" stroke="#000" stroke-width="1.4" fill="none"/></mask><polygon points="2,36 28,10 28,36" fill="var(--oxblood-600)" mask="url(#sg)"/><rect x="31" y="10" width="7" height="2.5" fill="var(--chartreuse-400)"/></svg>
    <div class="hero-in">
      <div class="eyebrow">Clyve · KPI reference</div>
      <h1>Every KPI across Clyve and ContentOS, and the <em>source</em> of every number</h1>
      <p class="hero-lead">Part A covers what ContentOS measures for clients. Part B covers Clyve itself: sales funnel, own content, lead gen, products and revenue. Part C covers the system: guardrails, evals and every automated send. Each metric shows the formula, the counts that feed it, and where every count comes from.</p>
      <div class="stats">
        <div class="stat"><div class="n">{len(ALL)}</div><div class="l">Metrics</div></div>
        <div class="stat"><div class="n">{n_a}</div><div class="l">ContentOS</div></div>
        <div class="stat"><div class="n">{n_b}</div><div class="l">Clyve core</div></div>
        <div class="stat"><div class="n">{n_c}</div><div class="l">Guardrails</div></div>
      </div>
      <div class="status"><span class="stamp-chip">Status: provisional</span><span class="meta">KPI formulas / {DATE} / {n_prop} proposed</span></div>
    </div>
  </div>
</header>

<main class="wrap">
<section id="read" class="first">
  <div class="sec-head"><span class="sec-num">00</span><h2>How to read this</h2></div>
  <div class="cards">
    <div class="panel"><div class="lbl">Every metric has</div><ul class="plain"><li>A formula built from named counts</li><li>A table saying where each count comes from</li><li>Steps to collect it</li><li>A worked example with illustrative numbers</li><li>A stamp saying how sure the number is</li></ul></div>
    <div class="panel"><div class="lbl">Source tags</div><ul class="plain">
      <li><span class="tag t-mute">PUBLIC</span> counted from public pages, no client access</li>
      <li><span class="tag t-ox">RUNS</span> counted from the AI prompt run log</li>
      <li><span class="tag t-ink">FOUNDER</span> comes from the founder call</li>
      <li><span class="tag t-ink">CLIENT</span> needs data the client shares</li>
      <li><span class="tag t-mute">PLATFORM</span> a platform's own analytics (LinkedIn, Instagram, Gumroad, sending tools)</li>
      <li><span class="tag t-mute">CLYVE</span> Clyve's own logs and records</li></ul></div>
    <div class="panel"><div class="lbl">Revenue link</div><ul class="plain"><li><span class="chip rev-direct">Direct</span> the number is money, or the step before it</li><li><span class="chip rev-indirect">Indirect</span> a plausible cause of a direct number</li><li><span class="chip rev-weak">Weak</span> a thin link; not for headlines</li><li><span class="chip rev-none">None</span> a prerequisite or a gate</li></ul></div>
    <div class="panel"><div class="lbl">Stamps (framework)</div><ul class="plain"><li><b>Observed</b> counted from a public source</li><li><b>Assumed ±1</b> public-only, before the founder call</li><li><b>Captured</b> after the founder call</li><li><b>Our read</b> Akul's interpretation only</li></ul></div>
  </div>
  <div class="box"><span class="bl">Provisional</span><p>Formulas are working definitions drafted from the ContentOS framework rules. The framework fixes what each track measures and how it is sampled; the exact arithmetic here is proposed wording. Freeze the definitions at Day 0 of each engagement. Worked examples use made-up numbers for a hypothetical D2C brand and are not results.</p></div>
  <div class="box"><span class="bl">Updated {DATE}</span><p>O2 now needs a move to beat a chance band as well as the noise band. New: C5 (prompt-set power), G6 to G8 (personalisation accuracy, bounce, spam complaints), and Part C, Layer 10 (Q1 to Q9: guardrails, evals and send safety). Open item 3 updated; items 15 to 19 added. Metrics marked NEW or UPDATED. Generated from kpi/ in clyve-guardrails-evals.</p></div>
</section>

<section id="vars">
  <div class="contour" aria-hidden="true"><i></i><i></i><i></i></div>
  <div class="sec-head"><span class="sec-num">00</span><h2>Variables and the run log</h2></div>
  <p class="lead">All Layer 2 formulas come from one table: the run log. One row per run.</p>
  <div class="scroll"><table class="grid"><thead><tr><th>Symbol</th><th>Meaning</th><th>Typical value</th></tr></thead><tbody>
    <tr><td class="mono">N</td><td>Prompts in the frozen prompt set</td><td>20 to 30, split across brand, niche and generic</td></tr>
    <tr><td class="mono">K</td><td>Runs per prompt per platform per checkpoint</td><td>2 to 3</td></tr>
    <tr><td class="mono">P</td><td>Platforms</td><td>3: ChatGPT, Perplexity, Gemini</td></tr>
    <tr><td class="mono">Runs in a segment</td><td>N in the segment × K × P</td><td>8 prompts × 3 × 3 = 72</td></tr>
    <tr><td class="mono">Pass</td><td>The full prompt set run once on each platform</td><td>K passes per checkpoint</td></tr>
    <tr><td class="mono">Smallest provable move</td><td>1.96 × √(0.25 × 2 ÷ runs in segment) × 100 (see C5)</td><td>~28 points per platform, ~16 pooled, for 8 prompts × 3 runs</td></tr>
  </tbody></table></div>
  <div class="lbl mt">The run log (one row per run)</div>
  <div class="scroll"><table class="grid"><thead><tr><th>Column</th><th>What it holds</th><th>Where it comes from</th></tr></thead><tbody>{runlog_rows}</tbody></table></div>
  <div class="box"><span class="bl">Rules that protect the numbers</span><p>Freeze the prompt set and definitions at Day 0. Split every figure by query type. Run client baselines in the real app interfaces and screenshot every run; an API trend track may run alongside but is labelled separately and never mixed in. A change counts only if it beats both the noise band and the chance band (see O2), and is reported as a figure only if it clears the smallest provable move (see C5).</p></div>
</section>

<section id="cheat">
  <div class="contour" aria-hidden="true"><i></i><i></i><i></i></div>
  <div class="sec-head"><span class="sec-num">00</span><h2>All formulas at a glance</h2></div>
  <p class="lead">Select an ID to jump to its full card.</p>
  <div class="scroll"><table class="grid cheat"><thead><tr><th>ID</th><th>Metric</th><th>Formula</th><th>Data from</th></tr></thead><tbody>{cheat}</tbody></table></div>
</section>
{"".join(body)}

<section id="open">
  <div class="contour" aria-hidden="true"><i></i><i></i><i></i></div>
  <div class="sec-head"><span class="sec-num">11</span><h2>Open items</h2></div>
  <p class="lead">What is undecided or unverified. None blocks a first audit, but each limits how far the numbers can be trusted.</p>
  <div class="scroll"><table class="grid"><thead><tr><th>#</th><th>Open item</th><th>What to do</th></tr></thead><tbody>{opens}</tbody></table></div>
</section>
</main>

<footer class="close">
  <div class="wrap">
    <div class="eyebrow">Next move</div>
    <h2>Confirm the working definitions, then freeze them before the first audit and the first tracked month.</h2>
    <p>Until then, every formula here is a proposal. Settle D1 and D2 scoring, the noise threshold, the adoption rule and the inquiry definition first; they decide how far the numbers can be trusted. Then add the consent fields (Q7) and calibrate one judge (Q3) before any automated send or model-marked column.</p>
    <div class="endorsed">{COS}<span class="div" aria-hidden="true"></span><span class="cl">{mark("mfoot", "var(--bone-50)", 24)}{WM}</span><span class="meta">Clyve and ContentOS KPI formulas / provisional</span></div>
  </div>
</footer>
<script>(function(){{
  var q = document.getElementById('q');
  if(!q) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll('.metric'));
  var rows = Array.prototype.slice.call(document.querySelectorAll('table.cheat tbody tr'));
  var msg = document.createElement('div'); msg.id = 'nomatch'; msg.textContent = 'No metric matches this filter';
  var first = document.getElementById('layer1'); if(first) first.parentNode.insertBefore(msg, first);
  function apply(){{
    var v = q.value.trim().toLowerCase(), shown = 0;
    cards.forEach(function(c){{
      var hit = !v || c.textContent.toLowerCase().indexOf(v) !== -1 || (c.getAttribute('data-src')||'').toLowerCase().indexOf(v) !== -1;
      c.classList.toggle('hidden', !hit); if(hit) shown++;
    }});
    rows.forEach(function(r){{ r.classList.toggle('hidden', !!v && r.textContent.toLowerCase().indexOf(v) === -1); }});
    document.querySelectorAll('.layer').forEach(function(s){{
      s.classList.toggle('hidden', !s.querySelector('.metric:not(.hidden)'));
    }});
    msg.style.display = (shown === 0) ? 'block' : 'none';
  }}
  q.addEventListener('input', apply);
}})();
</script>
</body>
</html>
'''


if __name__ == "__main__":
    print(build(), end="")
