"""Render ranked results as Markdown and a self-contained HTML page."""

from __future__ import annotations

import html
from datetime import date
from typing import Any, Mapping

from .vocab import AMENITIES

WARN = "⚠️"


def money(n: float | int | None) -> str:
    return "n/a" if n is None else f"₹{int(n):,}"


def label(key: str) -> str:
    return AMENITIES[key][0] if key in AMENITIES else key.replace("_", " ")


def _num(v: Any, suffix: str = "", digits: int = 0) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}{suffix}"


def summary_cells(item: Mapping[str, Any]) -> dict[str, str]:
    enr = item.get("enrichment") or {}
    sc = item["scores"]
    safety = enr.get("safety") or {}
    hospitals = (enr.get("medical") or {}).get("hospitals") or []
    etas = [h["ambulance_est_min"] for h in hospitals if h.get("ambulance_est_min") is not None]
    metro = enr.get("metro") or {}
    malls = enr.get("malls") or []
    commute = enr.get("commute") or {}
    wl = enr.get("waterlogging") or {}
    return {
        "rank": str(item["rank"]),
        "overall": _num(sc["overall"], digits=0),
        "safety": _num(safety.get("score"), digits=0) + (f" ({safety['confidence']})" if safety.get("confidence") else ""),
        "ambulance": _num(min(etas) if etas else None, " min", 0),
        "metro": _num(metro.get("km"), " km", 1),
        "mall": _num(min((m["km"] for m in malls), default=None), " km", 1),
        "commute": (f"{commute['peak_min']:.0f} min, {commute['multiplier']:.1f}x" if commute.get("peak_min") is not None else "n/a"),
        "flood": f"{WARN} {wl.get('status', '')}" if wl.get("warning") else "",
    }


# (table column, key in enrichment.gaps, display name). A cell that reads "n/a"
# must always be explained, so the reader never has to guess whether the data
# was missing, blocked, not requested or simply not looked up.
_GAP_COLUMNS = (
    ("safety", "safety", "Safety"),
    ("ambulance", "medical", "Ambulance"),
    ("metro", "metro", "Metro"),
    ("mall", "malls", "Mall"),
    ("commute", "commute", "Commute"),
)
NO_REASON = "no reason recorded (the enrichment step left a gap without explaining it)"


def missing_reasons(item: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Return (column name, reason) for every summary cell that shows n/a."""
    cells = summary_cells(item)
    gaps = (item.get("enrichment") or {}).get("gaps") or {}
    out = []
    for col, gap_key, name in _GAP_COLUMNS:
        if cells[col].startswith("n/a"):
            reason = gaps.get(gap_key) or gaps.get(col) or NO_REASON
            out.append((name, str(reason)))
    return out


def _facts(item: Mapping[str, Any]) -> list[str]:
    bits = [item.get("unit_type"), (item.get("furnishing") or "").replace("_", "-"), item.get("property_type", "").replace("_", " ")]
    if item.get("area_sqft"):
        bits.append(f"{item['area_sqft']} sqft")
    if item.get("floor") is not None:
        bits.append(f"floor {item['floor']}")
    if item.get("age_years") is not None:
        bits.append(f"{item['age_years']} yrs old")
    return [b for b in bits if b]


def render_markdown(result: Mapping[str, Any], req: Mapping[str, Any], meta: Mapping[str, Any]) -> str:
    ranked = result["ranked"]
    out = [f"# House search: {meta.get('locality', 'results')}", ""]
    out.append(f"_As of {meta.get('as_of', date.today().isoformat())}. Sorted by **{result['sort_by']}**. Prices and availability change; confirm with the owner._")
    out += ["", f"**Looking for:** {meta.get('query', '')}", ""]
    for a in meta.get("assumptions", []):
        out.append(f"- Assumption: {a}")
    if not ranked:
        out += ["", "No listing passed the hard requirements. See *Excluded* below, or relax a requirement."]
    else:
        out += ["", "| # | Listing | Rent | Score | Safety | Ambulance | Metro | Mall | Commute | Waterlogging |", "|---|---|---|---|---|---|---|---|---|---|"]
        for it in ranked:
            c = summary_cells(it)
            title = f"[{it.get('title', it.get('id'))}]({it['url']})" if it.get("url") else str(it.get("title", it.get("id")))
            out.append(f"| {c['rank']} | {title} | {money(it.get('rent'))} | {c['overall']} | {c['safety']} | {c['ambulance']} | {c['metro']} | {c['mall']} | {c['commute']} | {c['flood']} |")
        if any(missing_reasons(it) for it in ranked):
            out += ["", "_n/a means not measured, not zero and not safe. The reason for each is listed under the listing below._"]
        for it in ranked:
            out += ["", f"## {it['rank']}. {it.get('title', it.get('id'))}", "", f"{money(it.get('rent'))}/month · {', '.join(_facts(it))} · {it.get('locality', '')} · via {it.get('source', 'unknown')}"]
            enr = it.get("enrichment") or {}
            wl = enr.get("waterlogging") or {}
            if wl.get("warning"):
                out.append(f"\n{WARN} **Waterlogging {wl['status']}** in this area:")
                out += [f"- {e.get('note', e.get('area'))} ([source]({e['source_url']}), {e.get('date') or 'undated'})" for e in wl["evidence"]]
                if wl.get("reports_by_year"):
                    out.append("- Reports by year: " + ", ".join(f"{y}: {n}" for y, n in wl["reports_by_year"].items()))
            elif wl:
                out.append(f"\nWaterlogging: no reports found. {wl.get('note', '')}")
            for h in ((enr.get("medical") or {}).get("hospitals") or [])[:3]:
                eta = f", ambulance ~{h['ambulance_est_min']:.0f} min (car {h['peak_drive_min']:.0f} min at peak, {h.get('label', '')})" if h.get("ambulance_est_min") is not None else ""
                out.append(f"- Hospital: {h['name']}, {h['km']} km{eta}")
            s = enr.get("safety") or {}
            tr = s.get("trend") or {}
            if tr.get("direction") and tr["direction"] != "insufficient_data":
                years = ", ".join(f"{y['year']}: {y['count']}" for y in tr.get("by_year", []))
                out.append(f"- Safety trend: {tr['direction']} (incidents by year: {years}). {tr.get('caveat', '')}")
            elif tr:
                out.append("- Safety trend: not enough dated incidents to say.")
            for e in (s.get("evidence") or [])[:4]:
                out.append(f"- Safety evidence: {e.get('note', '')} ([source]({e['source_url']}))" if e.get("source_url") else f"- Safety evidence: {e.get('note', '')}")
            prof = (enr.get("commute") or {}).get("profile") or {}
            if prof.get("slots"):
                slots = ", ".join(f"{sl['depart_at'][11:16]} {sl['multiplier']:.1f}x ({sl['traffic_min']:.0f} min)" for sl in prof["slots"])
                out.append(f"- Commute by leaving time: {slots}. Leaving at {prof['best_slot'][11:16]} saves {prof['minutes_saved_by_best_slot']:.0f} min versus the worst slot (typical-traffic forecast).")
            missing = missing_reasons(it)
            if missing:
                out.append("- **Not measured (shown as n/a):**")
                out += [f"  - {name}: {reason}" for name, reason in missing]
            am = it["scores"]["amenity_match"]
            if am["nice_hit"]:
                out.append("- Has: " + ", ".join(label(k) for k in am["nice_hit"]))
            if am["nice_missing"]:
                out.append("- Not listed: " + ", ".join(label(k) for k in am["nice_missing"]))
            if am["must_unverified"]:
                out.append("- **Ask the owner** (must-have not confirmed): " + ", ".join(label(k) for k in am["must_unverified"]))
            for note in it.get("notes") or []:
                out.append(f"- {note}")
            out.append(f"- Data coverage {it['scores']['coverage']:.0%} ({it['scores']['confidence']} confidence)")
    if result["excluded"]:
        out += ["", "## Excluded", ""]
        out += [f"- {e.get('title') or e.get('id')}: {'; '.join(e['reasons'])}" for e in result["excluded"]]
    out += ["", "## Notes", "",
            "- Safety is relative and built from public incident reporting, not a guarantee. It never uses who lives in an area.",
            "- Ambulance times are estimates from peak-hour road traffic with an assumed siren factor; dispatch delay is not included.",
            "- No waterlogging reports found does not mean it never happens."]
    return "\n".join(out) + "\n"


_CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#e3e3e3;--card:#fafafa;--warn:#b45309;--warnbg:#fef3c7}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--mut:#9a9a9a;--line:#2d2d2d;--card:#1c1c1c;--warn:#fbbf24;--warnbg:#3b2a06}}
body{font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg);max-width:1000px;margin:0 auto;padding:16px}
table{border-collapse:collapse;width:100%;display:block;overflow-x:auto}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;white-space:nowrap}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0}
.warn{background:var(--warnbg);color:var(--warn);border-radius:6px;padding:6px 10px;margin:8px 0}
.mut{color:var(--mut)}a{color:inherit}
"""


def render_html(result: Mapping[str, Any], req: Mapping[str, Any], meta: Mapping[str, Any]) -> str:
    e = html.escape
    rows, cards = [], []
    for it in result["ranked"]:
        c = summary_cells(it)
        t = e(str(it.get("title", it.get("id"))))
        link = f'<a href="{e(it["url"], quote=True)}" rel="noopener">{t}</a>' if str(it.get("url", "")).startswith(("http://", "https://")) else t
        rows.append("<tr>" + "".join(f"<td>{x}</td>" for x in (c["rank"], link, e(money(it.get("rent"))), c["overall"], e(c["safety"]), c["ambulance"], c["metro"], c["mall"], e(c["commute"]), e(c["flood"]))) + "</tr>")
        enr = it.get("enrichment") or {}
        wl = enr.get("waterlogging") or {}
        body = [f'<p class="mut">{e(", ".join(_facts(it)))} · {e(str(it.get("locality", "")))} · via {e(str(it.get("source", "")))}</p>']
        if wl.get("warning"):
            notes = "; ".join(e(str(ev.get("note", ev.get("area")))) for ev in wl["evidence"])
            body.append(f'<div class="warn">{WARN} Waterlogging {e(wl["status"])}: {notes}</div>')
        for h in ((enr.get("medical") or {}).get("hospitals") or [])[:3]:
            eta = f", ambulance ~{h['ambulance_est_min']:.0f} min" if h.get("ambulance_est_min") is not None else ""
            body.append(f"<div>🏥 {e(h['name'])}, {h['km']} km{eta}</div>")
        missing = missing_reasons(it)
        if missing:
            items = "".join(f"<li><b>{e(name)}</b>: {e(reason)}</li>" for name, reason in missing)
            body.append(f'<div class="mut">Not measured (shown as n/a):<ul>{items}</ul></div>')
        am = it["scores"]["amenity_match"]
        if am["must_unverified"]:
            body.append('<div class="warn">Ask the owner: ' + e(", ".join(label(k) for k in am["must_unverified"])) + "</div>")
        for note in it.get("notes") or []:
            body.append(f"<div>{e(str(note))}</div>")
        cards.append(f'<div class="card"><h3>{it["rank"]}. {t}</h3>{"".join(body)}</div>')
    head = "<tr>" + "".join(f"<th>{h}</th>" for h in ("#", "Listing", "Rent", "Score", "Safety", "Ambulance", "Metro", "Mall", "Commute", "Waterlogging")) + "</tr>"
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>House search: {e(str(meta.get('locality', 'results')))}</title><style>{_CSS}</style>"
        f"<h1>House search: {e(str(meta.get('locality', '')))}</h1>"
        f'<p class="mut">As of {e(str(meta.get("as_of", date.today().isoformat())))} · sorted by {e(result["sort_by"])} · {e(str(meta.get("query", "")))}</p>'
        f"<table>{head}{''.join(rows)}</table>{''.join(cards)}"
        '<p class="mut">n/a means not measured (not zero, not safe); the reason is given under each listing. '
        "Safety is relative and based on public incident reporting. Ambulance times are estimates. No waterlogging reports is not a guarantee.</p></html>"
    )
