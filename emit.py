"""Write a finished record into the Obsidian vault.

One decision is one note. The note is generated, never hand-edited, so
re-running the graph on the same meeting overwrites its own note instead of
creating a second copy. Anything you want to keep goes in a different file.

The structure is flat on purpose:

    Ledger/
      Ledger.md                        index, one row per decision
      Decisions/Chandler 2025-12-11.md one per decision
      Jurisdictions/Chandler.md        one per body, links to its decisions
      Method.md                        how a record is made

Frontmatter carries the numbers so Obsidian treats them as properties and
Dataview can query across every decision without parsing prose. The body is
for a human. The frontmatter is for the ledger.
"""
import json, os
from pathlib import Path

# Override with LEDGER_VAULT to write somewhere else.
VAULT = Path(os.environ.get("LEDGER_VAULT", Path.home() / "Ledger"))
LEDGER = VAULT / "Ledger"


def _fm(record: dict) -> str:
    """YAML frontmatter. Only scalars, because Obsidian properties are typed."""
    f = record["fields"]
    d = record.get("derived", {})
    t = record.get("tally", {})
    rows = {
        "type": "decision",
        "jurisdiction": record.get("jurisdiction"),
        "vote_date": record.get("vote_date"),
        "agenda_posted": record.get("agenda_posted"),
        "item": f.get("item", {}).get("value"),
        "vote_yes": f.get("vote_yes", {}).get("value"),
        "vote_no": f.get("vote_no", {}).get("value"),
        "outcome": record.get("outcome"),
        "submissions": t.get("submissions"),
        "oppose": t.get("oppose"),
        "support": t.get("support"),
        "speakers": f.get("speakers", {}).get("value"),
        "notice_window_days": d.get("notice_window_days"),
        "response_latency_days": d.get("response_latency_days"),
        "same_day_share": d.get("same_day_share"),
        "status": record.get("status"),
    }
    lines = ["---"]
    for k, v in rows.items():
        if v is not None:
            lines.append(f"{k}: {json.dumps(v) if isinstance(v, str) else v}")
    lines.append("---")
    return "\n".join(lines)


def _histogram(by_day: dict, vote_date: str) -> str:
    """A bar per day. The shape is the argument, so it has to be visible
    without opening a spreadsheet."""
    if not by_day:
        return "_No written submissions in the record._"
    peak = max(by_day.values())
    out = ["| Date | | Filed |", "|---|---|--:|"]
    for day, n in by_day.items():
        bar = "█" * max(1, round(n / peak * 24))
        mark = " **(vote)**" if day == vote_date else ""
        out.append(f"| {day}{mark} | `{bar}` | {n} |")
    return "\n".join(out)


def write_note(record: dict) -> str:
    (LEDGER / "Decisions").mkdir(parents=True, exist_ok=True)
    (LEDGER / "Jurisdictions").mkdir(parents=True, exist_ok=True)

    juris = record.get("jurisdiction", "Unknown")
    slug = f"{juris} {record.get('vote_date', 'undated')}"
    f, d, t = record["fields"], record.get("derived", {}), record.get("tally", {})
    prov = record.get("provenance", {})

    body = [_fm(record), "", f"# {juris} · {record.get('vote_date')}", ""]

    # A partial record says so at the top, in the first thing a reader sees.
    # Burying it under the numbers is how a ledger starts lying by omission.
    if record.get("status") != "verified":
        body += [f"> [!warning] {record['status'].upper()} — not citable yet",
                 "> Missing or unverified: "
                 + ", ".join(record.get("missing") or ["—"]) + ".",
                 "> Numbers below are real and grounded, but this record does "
                 "not yet meet the bar in [[Method]] and must not be quoted.",
                 ""]

    # The derived numbers first. They are the finding; everything below is
    # the evidence for them.
    if d:
        body += [
            "## The two numbers",
            "",
            f"**Notice window: {d.get('notice_window_days')} days.** The agenda was "
            f"posted {record.get('agenda_posted')} and the vote was "
            f"{record.get('vote_date')}. That is how long this decision was "
            "formally findable by a resident.",
            "",
            f"**Response latency: {d.get('response_latency_days')} day(s).** The first "
            "written comment arrived that long after the agenda posted. This is the "
            "number that answers the apathy explanation.",
            "",
        ]
        if d.get("same_day_share") is not None:
            body += [
                f"{d['same_day_count']} of {t.get('submissions')} submissions "
                f"({int(d['same_day_share'] * 100)}%) were filed on the day of the "
                "vote itself.", "",
            ]

    body += ["## Participation", "", _histogram(t.get("by_day", {}),
                                                record.get("vote_date")), ""]

    if t.get("submissions"):
        body += [
            f"- **{t['submissions']}** written submissions attached to the minutes",
            f"- **{t.get('with_position')}** stated a position: "
            f"**{t.get('oppose')} oppose / {t.get('support')} support**"
            + (f" ({d.get('oppose_ratio')}:1)" if d.get("oppose_ratio") else ""),
            f"- **{t.get('unique_names')}** unique names "
            f"({t.get('repeat_submitters')} people submitted more than once)",
            "",
        ]

    # Extracted fields, each with the sentence it came from.
    body += ["## Extracted fields", "", "| Field | Value | Support |", "|---|---|---|"]
    for k, v in f.items():
        val = v.get("value")
        body.append(f"| {k} | {'—' if val is None else val} | `{v.get('support')}` |")
    body.append("")

    quotes = [(k, v["quote"]) for k, v in f.items() if v.get("quote")]
    if quotes:
        body += ["## Grounding", ""]
        body += [f"**{k}**\n> {q.strip()}\n" for k, q in quotes]

    if record.get("conflicts"):
        body += ["## Conflicts", "",
                 "Recorded, not resolved. A disagreement between sources is a "
                 "finding about the record.", "",
                 "```json", json.dumps(record["conflicts"], indent=2), "```", ""]

    body += ["## Provenance", ""]
    if prov:
        for k, v in prov.items():
            body.append(f"- **{k}**: {v}")
    else:
        body.append("- _Not recorded. Every record needs a source URL, a "
                    "retrieval date and a checksum before it is citable._")

    body += ["", "---", "",
             f"Jurisdiction: [[{juris}]] · Method: [[Method]] · Index: [[Ledger]]",
             "", "_Generated by the extraction graph. Do not hand-edit; "
             "re-running overwrites this file._", ""]

    path = LEDGER / "Decisions" / f"{slug}.md"
    path.write_text("\n".join(body))

    _write_jurisdiction(juris)
    _write_index()
    return str(path)


def _write_jurisdiction(juris: str):
    """One note per body. Dataview fills the table if the plugin is on; the
    plain link list below works whether it is or not."""
    p = LEDGER / "Jurisdictions" / f"{juris}.md"
    decisions = sorted((LEDGER / "Decisions").glob(f"{juris} *.md"))
    links = "\n".join(f"- [[{d.stem}]]" for d in decisions) or "_No decisions yet._"
    p.write_text(f"""---
type: jurisdiction
name: {juris}
decisions: {len(decisions)}
---

# {juris}

## Decisions on record

{links}

---
Index: [[Ledger]]
""")


def _write_index():
    """The ledger itself. Every decision, newest first."""
    decisions = sorted((LEDGER / "Decisions").glob("*.md"), reverse=True)
    rows = ["| Decision | Notice window | Response latency | Submissions | Outcome | Status |",
            "|---|--:|--:|--:|---|---|"]
    for d in decisions:
        fm = {}
        for line in d.read_text().split("---")[1].strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip('"')
        vote = f"{fm.get('vote_yes','?')}-{fm.get('vote_no','?')}"
        rows.append(
            f"| [[{d.stem}]] | {fm.get('notice_window_days','—')} d "
            f"| {fm.get('response_latency_days','—')} d "
            f"| {fm.get('submissions','—')} | {vote} "
            f"| {fm.get('status','?')} |")

    fdir = LEDGER / "Findings"
    findings = "\n".join(f"- [[{x.stem}]]" for x in sorted(fdir.glob("*.md"))) \
        if fdir.exists() else "_None yet._"

    (LEDGER / "Ledger.md").write_text(f"""---
type: index
decisions: {len(decisions)}
---

# The participation ledger

One row per decision that committed power, water, or a tax benefit to a data
center in Arizona.

**Notice window** is how long the decision was formally findable before the
vote. **Response latency** is how long it took the first resident to react
once it was. The claim this ledger tests is that the second number is small
and the first one is too, which means non-participation is a property of the
process rather than of the public.

{chr(10).join(rows)}

## Findings

{findings}

---
Method: [[Method]]
""")


if __name__ == "__main__":
    import sys
    write_note(json.load(open(sys.argv[1])))
