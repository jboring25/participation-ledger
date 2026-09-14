"""The whole graph, in one file, in reading order.

            ┌── extract ──┐   (a model reads prose)
    START ──┤             ├── verify ── commit ── emit ── record
            └── count ────┘   (a parser counts forms)

Five nodes. Each is a function that takes the shared state and returns only the
keys it changed. That is all LangGraph is.

Why a graph and not a script: extract and count are genuinely independent. One
calls a model over the network, the other is local arithmetic. They read the
same document, answer different questions, and only meet at verify, where the
parser's exact count is used to check the model's guess. That convergence is
the reason this is a graph. If it were a straight line, a script would do.

Two sources are supported but not required. Most city clerks publish one
document. When a second exists, agreement across both raises a field's support
from "single" to "both", and disagreement is recorded as a conflict rather
than silently resolved.
"""
import json, re, sys, time
from typing import TypedDict, List, Dict, Optional

from langgraph.graph import StateGraph, START, END

from fields import FIELDS
from llm import ask_json
from tally import tally as count_submissions, count_speakers, derive


# ── the state: one dict, travels through every node ──────────────────────
class S(TypedDict, total=False):
    source_a: str            # the FULL record, including attached comments
    narrative: Optional[str] # just the prose for this item; the model reads
                             # this, not the 400kb of attachments behind it
    source_b: Optional[str]  # corroborating record, or None
    jurisdiction: str
    agenda_posted: str       # ISO date, from the record or the agenda portal
    vote_date: str           # ISO date
    provenance: Dict         # url, retrieved, md5

    a: Dict                  # {field: {value, quote}} from source A
    b: Dict                  # same from source B, empty if absent
    tally: Dict              # deterministic counts
    derived: Dict            # the numbers no source document contains
    assumed: List[str]        # values supplied by hand, not found in the record
    missing: List[str]
    conflicts: List[Dict]
    status: str
    record: Dict
    note_path: str


PROMPT = """Extract these fields from the public record below.

{definitions}

Return JSON. For every field return an object with two keys:
  "value" — the value, or null if the record does not state it
  "quote" — the exact sentence from the record you took it from, copied
            character for character, or null if value is null

Never infer, estimate, or calculate. If the record does not say it, it is null.

RECORD:
{text}"""

# How far the model's comment count may sit from the parser's exact count and
# still be treated as agreement. Declared here, in advance, on purpose: the
# Eviction Lab publishes an 86–114% band for the same reason. Deciding what
# counts as correct before you look is what separates a method from a vibe.
COUNT_TOLERANCE = 0.05

# What a record must contain before it counts as evidence rather than a note.
# The vote is the decision; without it there is nothing to explain. The posting
# date is the denominator of the notice window, which is the whole finding.
REQUIRED = ("vote_yes", "vote_no")


# ── node 1 ───────────────────────────────────────────────────────────────
def extract(s: S) -> dict:
    """Read the prose. Every value must arrive with the sentence it came from."""
    defs = "\n".join(f"- {k}: {v}" for k, v in FIELDS.items())
    return {
        "a": _grounded(s.get("narrative") or s["source_a"], defs),
        "b": _grounded(s["source_b"], defs) if s.get("source_b") else {},
    }


def _grounded(text: str, defs: str) -> dict:
    """Ask for values plus quotes, then throw away anything whose quote is not
    actually in the document. A model can invent a number. It cannot invent a
    sentence that survives a substring check."""
    raw = ask_json(PROMPT.format(definitions=defs, text=text))
    flat = _flatten(text)
    out = {}
    for f in FIELDS:
        got = raw.get(f) or {}
        value, quote = got.get("value"), got.get("quote")
        if value is not None and (not quote or _flatten(quote) not in flat):
            value, quote = None, None          # ungrounded, so discarded
        out[f] = {"value": value, "quote": quote}
    return out


# ── node 2, runs alongside node 1 ────────────────────────────────────────
def count(s: S) -> dict:
    """Count the attached submissions and compute what the record does not say."""
    t = count_submissions(s["source_a"])
    t |= count_speakers(s.get("narrative") or s["source_a"])
    if not t.get("submissions"):
        return {"tally": t, "derived": {}}
    return {"tally": t,
            "derived": derive(t, s["agenda_posted"], s["vote_date"])}


# ── node 3 ───────────────────────────────────────────────────────────────
def verify(s: S) -> dict:
    """Compare every reading against every other. Disagreement is a finding,
    never something to smooth over."""
    conflicts = []

    # a vs b, where a second document exists
    for f in FIELDS:
        av = s["a"][f]["value"]
        bv = s["b"].get(f, {}).get("value") if s["b"] else None
        if av is not None and bv is not None and not _same(av, bv):
            conflicts.append({"field": f, "kind": "source", "a": av, "b": bv})

    # the model's comment count vs the parser's exact count
    model = s["a"]["comments_filed"]["value"]
    exact = s["tally"].get("with_position")
    if model is not None and exact:
        if abs(model - exact) / exact > COUNT_TOLERANCE:
            conflicts.append({"field": "comments_filed", "kind": "count",
                              "model": model, "parser": exact,
                              "tolerance": COUNT_TOLERANCE})

    # A record is only citable when the things the study actually claims are
    # present. Absence of conflict is not the same as presence of evidence,
    # and a ledger that calls a half-record "verified" is worse than a ledger
    # with fewer rows, because the overstatement is invisible at a glance.
    missing = [f for f in REQUIRED
               if s["a"].get(f, {}).get("value") is None
               and not s["tally"].get(f)]
    if s.get("assumed"):
        missing += [f"{k} (assumed, not in record)" for k in s["assumed"]]

    status = ("conflicted" if conflicts
              else "partial" if missing
              else "verified")
    return {"conflicts": conflicts, "missing": missing, "status": status}


# ── node 4 ───────────────────────────────────────────────────────────────
def commit(s: S) -> dict:
    """Write the record. Every field carries how well it is supported."""
    bad = {c["field"] for c in s["conflicts"]}
    fields = {}
    for f in FIELDS:
        av = s["a"][f]["value"]
        bv = s["b"].get(f, {}).get("value") if s["b"] else None
        if f in bad:
            fields[f] = {"value": None, "support": "CONFLICT"}
        elif av is not None and bv is not None:
            fields[f] = {"value": av, "support": "both", "quote": s["a"][f]["quote"]}
        elif av is not None or bv is not None:
            side = "a" if av is not None else "b"
            src = s["a"] if side == "a" else s["b"]
            fields[f] = {"value": av if av is not None else bv,
                         "support": "single", "quote": src[f]["quote"]}
        else:
            fields[f] = {"value": None, "support": "missing"}

    # The parser is not a competing opinion. Where it has an exact count, it
    # wins, and it says so.
    if s["tally"].get("with_position"):
        fields["comments_filed"] = {"value": s["tally"]["with_position"],
                                    "support": "counted",
                                    "quote": None}
    if s["tally"].get("speakers"):
        fields["speakers"] = {"value": s["tally"]["speakers"],
                              "support": "counted", "quote": None}

    return {"record": {
        "jurisdiction": s.get("jurisdiction"),
        "vote_date": s.get("vote_date"),
        "agenda_posted": s.get("agenda_posted"),
        "status": s["status"],
        "fields": fields,
        "tally": s["tally"],
        "derived": s["derived"],
        "conflicts": s["conflicts"],
        "missing": s.get("missing", []),
        "assumed": s.get("assumed", []),
        "provenance": s.get("provenance", {}),
    }}


# ── node 5 ───────────────────────────────────────────────────────────────
def emit(s: S) -> dict:
    """Write the record into the vault as a linked note."""
    from emit import write_note
    return {"note_path": write_note(s["record"])}


# ── helpers ──────────────────────────────────────────────────────────────
def _flatten(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _same(x, y) -> bool:
    if isinstance(x, str) and isinstance(y, str):
        return _flatten(x) == _flatten(y)
    return x == y


# ── the wiring ───────────────────────────────────────────────────────────
def build():
    g = StateGraph(S)
    for fn in (extract, count, verify, commit, emit):
        g.add_node(fn.__name__, fn)
    # extract and count fan out from the start and rejoin at verify.
    # LangGraph waits for both before running verify.
    g.add_edge(START, "extract")
    g.add_edge(START, "count")
    g.add_edge("extract", "verify")
    g.add_edge("count", "verify")
    g.add_edge("verify", "commit")
    g.add_edge("commit", "emit")
    g.add_edge("emit", END)
    return g.compile()


def run(**kw):
    t0 = time.time()
    out = build().invoke(kw)
    out["seconds"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 5:
        sys.exit("usage: python graph.py <record.txt> <jurisdiction> "
                 "<agenda_posted> <vote_date> [narrative.txt] [provenance.json]")
    path, juris, posted, voted = sys.argv[1:5]
    narrative = open(sys.argv[5]).read() if len(sys.argv) > 5 else None
    prov = json.load(open(sys.argv[6])) if len(sys.argv) > 6 else {}
    r = run(source_a=open(path).read(), narrative=narrative, source_b=None,
            jurisdiction=juris, agenda_posted=posted, vote_date=voted,
            provenance=prov)
    print(json.dumps({"status": r["status"], "seconds": r["seconds"],
                      "note": r["note_path"], "derived": r["record"]["derived"],
                      "conflicts": r["conflicts"],
                      "missing": r.get("missing", [])}, indent=2))
